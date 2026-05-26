"""
Qdrant Vector Database Connection
Manages connection to Qdrant for knowledge base embeddings
"""
from typing import List, Dict, Any, Optional
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchParams,
)

from app.config import settings
from app.core.logging_config import get_logger
from app.core.exceptions import VectorDatabaseError

logger = get_logger(__name__)

# Global Qdrant client instance
_qdrant_client: Optional[AsyncQdrantClient] = None


# ==================== Connection Management ====================

async def connect_to_qdrant() -> None:
    """
    Connect to Qdrant and create collection if it doesn't exist
    """
    global _qdrant_client

    try:
        logger.info(f"Connecting to Qdrant: {settings.qdrant_url}")

        # Create client
        if settings.qdrant_api_key:
            _qdrant_client = AsyncQdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key,
                timeout=30.0,
            )
        else:
            _qdrant_client = AsyncQdrantClient(
                url=settings.qdrant_url,
                timeout=30.0,
            )

        logger.info(f"✓ Connected to Qdrant")

        # Create collection if it doesn't exist
        await create_collection_if_not_exists()

    except Exception as e:
        logger.error(f"Failed to connect to Qdrant: {str(e)}", exc_info=True)
        raise VectorDatabaseError(f"Failed to connect to Qdrant: {str(e)}")


async def close_qdrant_connection() -> None:
    """
    Close Qdrant connection
    """
    global _qdrant_client

    if _qdrant_client:
        await _qdrant_client.close()
        logger.info("Qdrant connection closed")


def get_qdrant_client() -> AsyncQdrantClient:
    """
    Get Qdrant client instance

    Returns:
        AsyncQdrantClient instance

    Raises:
        RuntimeError: If client is not connected
    """
    if _qdrant_client is None:
        raise RuntimeError("Qdrant client not connected. Call connect_to_qdrant() first.")
    return _qdrant_client


# ==================== Collection Management ====================

async def create_collection_if_not_exists() -> None:
    """
    Create Qdrant collection if it doesn't exist and ensure indexes are created
    """
    client = get_qdrant_client()
    collection_name = settings.qdrant_collection_name

    try:
        # Check if collection exists
        collections = await client.get_collections()
        collection_exists = any(
            col.name == collection_name for col in collections.collections
        )

        if not collection_exists:
            # Create collection
            await client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=settings.qdrant_vector_size,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"✓ Created Qdrant collection: {collection_name}")

        # Always ensure payload indexes exist (idempotent operation)
        # These will be created if they don't exist, or skipped if they do
        await _ensure_payload_indexes(client, collection_name)

    except Exception as e:
        logger.error(f"Failed to create collection: {str(e)}", exc_info=True)
        raise VectorDatabaseError(f"Failed to create collection: {str(e)}")


async def _ensure_payload_indexes(client: AsyncQdrantClient, collection_name: str) -> None:
    """
    Ensure payload indexes exist for the collection
    This is idempotent and won't fail if indexes already exist
    """
    try:
        # Create payload indexes for filtering (will skip if already exist)
        try:
            await client.create_payload_index(
                collection_name=collection_name,
                field_name="company_id",
                field_schema="integer",
            )
            logger.info(f"✓ Created or verified payload index for company_id")
        except Exception as e:
            # Index might already exist, log and continue
            if "already exists" not in str(e).lower():
                logger.warning(f"Could not create company_id index: {str(e)}")

        try:
            await client.create_payload_index(
                collection_name=collection_name,
                field_name="knowledge_id",
                field_schema="keyword",
            )
            logger.info(f"✓ Created or verified payload index for knowledge_id")
        except Exception as e:
            # Index might already exist, log and continue
            if "already exists" not in str(e).lower():
                logger.warning(f"Could not create knowledge_id index: {str(e)}")

    except Exception as e:
        logger.error(f"Failed to ensure payload indexes: {str(e)}", exc_info=True)


# ==================== Vector Operations ====================

async def upsert_vectors(
    vectors: List[List[float]],
    payloads: List[Dict[str, Any]],
    ids: Optional[List[str]] = None,
) -> List[str]:
    """
    Upsert vectors into Qdrant

    Args:
        vectors: List of embedding vectors
        payloads: List of metadata payloads (must include company_id)
        ids: Optional list of point IDs (auto-generated if not provided)

    Returns:
        List of point IDs

    Raises:
        VectorDatabaseError: If upsert fails
    """
    client = get_qdrant_client()
    collection_name = settings.qdrant_collection_name

    try:
        # Generate IDs if not provided
        if ids is None:
            import uuid
            ids = [str(uuid.uuid4()) for _ in range(len(vectors))]

        # Validate inputs
        if len(vectors) != len(payloads):
            raise ValueError("Number of vectors must match number of payloads")

        if ids and len(ids) != len(vectors):
            raise ValueError("Number of IDs must match number of vectors")

        # Validate all payloads have company_id
        for i, payload in enumerate(payloads):
            if "company_id" not in payload:
                raise ValueError(f"Payload at index {i} missing required field: company_id")

        # Create points
        points = [
            PointStruct(
                id=point_id,
                vector=vector,
                payload=payload,
            )
            for point_id, vector, payload in zip(ids, vectors, payloads)
        ]

        # Upsert points
        await client.upsert(
            collection_name=collection_name,
            points=points,
        )

        logger.info(f"✓ Upserted {len(points)} vectors to Qdrant")

        return ids

    except Exception as e:
        logger.error(f"Failed to upsert vectors: {str(e)}", exc_info=True)
        raise VectorDatabaseError(f"Failed to upsert vectors: {str(e)}")


async def search_vectors(
    query_vector: List[float],
    company_id: str,
    top_k: int = 5,
    score_threshold: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Search for similar vectors in Qdrant with company_id filtering

    Args:
        query_vector: Query embedding vector
        company_id: Company ID to filter by (for multi-tenancy)
        top_k: Number of results to return
        score_threshold: Minimum similarity score (0.0 to 1.0)

    Returns:
        List of search results with id, score, and payload

    Raises:
        VectorDatabaseError: If search fails
    """
    client = get_qdrant_client()
    collection_name = settings.qdrant_collection_name

    try:
        # Create filter for company_id
        search_filter = Filter(
            must=[
                FieldCondition(
                    key="company_id",
                    match=MatchValue(value=company_id),
                )
            ]
        )

        # Search
        search_result = await client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=search_filter,
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,
        )

        # Format results
        results = [
            {
                "id": str(hit.id),
                "score": hit.score,
                "payload": hit.payload,
            }
            for hit in search_result
        ]

        logger.info(
            f"✓ Found {len(results)} results for company {company_id} "
            f"(top_k={top_k}, threshold={score_threshold})"
        )

        return results

    except Exception as e:
        logger.error(f"Failed to search vectors: {str(e)}", exc_info=True)
        raise VectorDatabaseError(f"Failed to search vectors: {str(e)}")


async def delete_vectors(
    ids: List[str],
    company_id: Optional[str] = None,
) -> None:
    """
    Delete vectors from Qdrant

    Args:
        ids: List of point IDs to delete
        company_id: Optional company ID for additional safety check

    Raises:
        VectorDatabaseError: If deletion fails
    """
    client = get_qdrant_client()
    collection_name = settings.qdrant_collection_name

    try:
        # If company_id provided, verify ownership before deleting
        if company_id:
            # Retrieve points to verify company_id
            points = await client.retrieve(
                collection_name=collection_name,
                ids=ids,
                with_payload=True,
            )

            # Check if all points belong to the company
            for point in points:
                if point.payload.get("company_id") != company_id:
                    raise VectorDatabaseError(
                        f"Cannot delete point {point.id}: belongs to different company"
                    )

        # Delete points
        await client.delete(
            collection_name=collection_name,
            points_selector=ids,
        )

        logger.info(f"✓ Deleted {len(ids)} vectors from Qdrant")

    except Exception as e:
        logger.error(f"Failed to delete vectors: {str(e)}", exc_info=True)
        raise VectorDatabaseError(f"Failed to delete vectors: {str(e)}")


async def delete_vectors_by_filter(
    company_id: str,
    filter_payload: Dict[str, Any],
) -> None:
    """
    Delete vectors matching company_id and additional payload filters

    Args:
        company_id: Company ID (required for multi-tenancy)
        filter_payload: Additional payload fields to filter by (e.g., {"knowledge_id": "xyz"})

    Raises:
        VectorDatabaseError: If deletion fails
    """
    client = get_qdrant_client()
    collection_name = settings.qdrant_collection_name

    try:
        # Build filter conditions
        must_conditions = [
            FieldCondition(
                key="company_id",
                match=MatchValue(value=company_id),
            )
        ]

        # Add additional filters from filter_payload
        for key, value in filter_payload.items():
            must_conditions.append(
                FieldCondition(
                    key=key,
                    match=MatchValue(value=value),
                )
            )

        # Create combined filter
        delete_filter = Filter(must=must_conditions)

        # Delete points
        await client.delete(
            collection_name=collection_name,
            points_selector=delete_filter,
        )

        logger.info(
            f"✓ Deleted vectors for company {company_id} "
            f"with filters: {filter_payload}"
        )

    except Exception as e:
        logger.error(f"Failed to delete vectors by filter: {str(e)}", exc_info=True)
        raise VectorDatabaseError(f"Failed to delete vectors by filter: {str(e)}")


async def delete_vectors_by_company(company_id: str) -> None:
    """
    Delete all vectors for a company

    Args:
        company_id: Company ID

    Raises:
        VectorDatabaseError: If deletion fails
    """
    client = get_qdrant_client()
    collection_name = settings.qdrant_collection_name

    try:
        # Create filter for company_id
        delete_filter = Filter(
            must=[
                FieldCondition(
                    key="company_id",
                    match=MatchValue(value=company_id),
                )
            ]
        )

        # Delete points
        await client.delete(
            collection_name=collection_name,
            points_selector=delete_filter,
        )

        logger.info(f"✓ Deleted all vectors for company {company_id}")

    except Exception as e:
        logger.error(f"Failed to delete vectors for company: {str(e)}", exc_info=True)
        raise VectorDatabaseError(f"Failed to delete vectors for company: {str(e)}")


async def count_vectors_by_company(company_id: str) -> int:
    """
    Count vectors for a company

    Args:
        company_id: Company ID

    Returns:
        Number of vectors

    Raises:
        VectorDatabaseError: If count fails
    """
    client = get_qdrant_client()
    collection_name = settings.qdrant_collection_name

    try:
        # Create filter for company_id
        count_filter = Filter(
            must=[
                FieldCondition(
                    key="company_id",
                    match=MatchValue(value=company_id),
                )
            ]
        )

        # Count points
        result = await client.count(
            collection_name=collection_name,
            count_filter=count_filter,
            exact=True,
        )

        return result.count

    except Exception as e:
        logger.error(f"Failed to count vectors: {str(e)}", exc_info=True)
        raise VectorDatabaseError(f"Failed to count vectors: {str(e)}")


# Export functions
__all__ = [
    "connect_to_qdrant",
    "close_qdrant_connection",
    "get_qdrant_client",
    "create_collection_if_not_exists",
    "upsert_vectors",
    "search_vectors",
    "delete_vectors",
    "delete_vectors_by_filter",
    "delete_vectors_by_company",
    "count_vectors_by_company",
]
