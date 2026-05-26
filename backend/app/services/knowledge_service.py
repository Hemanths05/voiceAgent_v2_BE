"""
Knowledge Service with RAG
Handles knowledge base management and semantic search
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
import math
import asyncio
import uuid

from app.core.exceptions import (
    KnowledgeNotFoundError,
    DocumentParsingError,
    ValidationError,
    AuthorizationError,
    EmbeddingsError
)
from app.core.logging_config import get_logger
from app.database.mongodb import get_database
from app.database.qdrant import get_qdrant_client, upsert_vectors, search_vectors, delete_vectors_by_filter
from app.schemas.knowledge import (
    KnowledgeUploadRequest,
    KnowledgeUpdateRequest,
    KnowledgeResponse,
    KnowledgeListResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResult,
    KnowledgeSearchResponse,
    KnowledgeChunkResponse,
    KnowledgeUploadResponse
)
from app.utils.document_parser import DocumentParser
from app.utils.text_chunker import SmartTextChunker
from app.utils.validators import Validators
from app.providers.factories.embeddings_factory import EmbeddingsFactory

logger = get_logger(__name__)


class KnowledgeService:
    """
    Service for handling knowledge base operations and RAG

    RAG Flow:
    1. Upload document → parse → chunk → embed → store in Qdrant + MongoDB
    2. Query → embed query → search Qdrant → retrieve top chunks
    3. Format chunks as context for LLM
    """

    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        """
        Initialize knowledge service

        Args:
            db: MongoDB database instance (if None, will use get_database())
        """
        self.db = db or get_database()
        self.knowledge_collection = self.db.knowledge_bases
        self.users_collection = self.db.users
        self.qdrant_client = get_qdrant_client()

        # Initialize text chunker
        self.text_chunker = SmartTextChunker(
            chunk_size_tokens=512,
            overlap_tokens=50,
            min_chunk_size_tokens=50
        )

    async def upload_knowledge(
        self,
        file_data: bytes,
        filename: str,
        data: KnowledgeUploadRequest,
        company_id: str,
        uploaded_by_user_id: Optional[str] = None
    ) -> KnowledgeUploadResponse:
        """
        Upload and process knowledge base document

        Full Pipeline:
        1. Validate document size
        2. Parse document → extract text
        3. Chunk text with overlap
        4. Generate embeddings for each chunk
        5. Store vectors in Qdrant
        6. Store metadata in MongoDB

        Args:
            file_data: Document file bytes
            filename: Original filename
            data: Upload metadata
            company_id: Company ID
            uploaded_by_user_id: ID of user uploading (for authorization)

        Returns:
            Knowledge upload response

        Raises:
            DocumentParsingError: If document parsing fails
            EmbeddingsError: If embedding generation fails
            AuthorizationError: If user doesn't have permission
        """
        try:
            # Check authorization
            if uploaded_by_user_id:
                await self._check_company_authorization(uploaded_by_user_id, company_id)

            logger.info(f"Starting knowledge upload: {filename} for company {company_id}")

            # Step 1: Validate document size (max 10MB)
            DocumentParser.validate_document_size(file_data, max_size_mb=10)

            # Step 2: Parse document
            logger.info(f"Parsing document: {filename}")
            parsed_doc = DocumentParser.parse(file_data, filename)
            text = parsed_doc["text"]
            file_metadata = parsed_doc["metadata"]

            # Validate text length
            DocumentParser.validate_text_length(text, min_length=50, max_length=1_000_000)

            # Step 3: Chunk text
            logger.info(f"Chunking text: {len(text)} characters")
            chunks = self.text_chunker.chunk_text(
                text,
                metadata={
                    "filename": filename,
                    "title": data.title,
                    "file_format": file_metadata["format"]
                }
            )

            if not chunks:
                raise DocumentParsingError(
                    "No chunks generated from document",
                    {"filename": filename}
                )

            logger.info(f"Generated {len(chunks)} chunks")

            # Step 4: Generate embeddings
            logger.info("Generating embeddings")
            embeddings_provider = EmbeddingsFactory.create("gemini")  # Use configured provider

            # Extract chunk texts
            chunk_texts = [chunk["text"] for chunk in chunks]

            # Generate embeddings in batches (max 100 per batch)
            batch_size = 100
            all_embeddings = []

            for i in range(0, len(chunk_texts), batch_size):
                batch = chunk_texts[i:i + batch_size]
                embeddings_response = await embeddings_provider.embed(batch)
                all_embeddings.extend(embeddings_response.embeddings)
                logger.debug(f"Generated embeddings for batch {i//batch_size + 1}")

            # Step 5: Create MongoDB document
            knowledge_doc = {
                "company_id": company_id,
                "title": data.title,
                "description": data.description,
                "tags": data.tags or [],
                "filename": filename,
                "file_format": file_metadata["format"],
                "file_size": len(file_data),
                "num_chunks": len(chunks),
                "total_chars": len(text),
                "file_metadata": file_metadata,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            result = await self.knowledge_collection.insert_one(knowledge_doc)
            knowledge_id = str(result.inserted_id)

            logger.info(f"Created knowledge entry: {knowledge_id}")

            # Step 6: Store vectors in Qdrant
            logger.info("Storing vectors in Qdrant")

            # Prepare vector points
            vector_points = []
            for idx, (chunk, embedding) in enumerate(zip(chunks, all_embeddings)):
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{knowledge_id}_{idx}"))

                vector_points.append({
                    "id": point_id,
                    "vector": embedding,
                    "payload": {
                        "knowledge_id": knowledge_id,
                        "company_id": company_id,
                        "chunk_index": chunk["chunk_index"],
                        "text": chunk["text"],
                        "title": data.title,
                        "filename": filename,
                        "tags": data.tags or [],
                        "char_count": chunk["char_count"],
                        "token_count_estimate": chunk["token_count_estimate"]
                    }
                })

            # Upsert to Qdrant
            point_ids = [vp["id"] for vp in vector_points]
            point_vectors = [vp["vector"] for vp in vector_points]
            point_payloads = [vp["payload"] for vp in vector_points]
            await upsert_vectors(point_vectors, point_payloads, ids=point_ids)

            logger.info(f"Knowledge upload complete: {knowledge_id} ({len(chunks)} chunks)")

            # Build response
            knowledge_response = KnowledgeResponse(
                id=knowledge_id,
                company_id=company_id,
                title=data.title,
                description=data.description,
                tags=data.tags or [],
                filename=filename,
                file_format=file_metadata["format"],
                file_size=len(file_data),
                num_chunks=len(chunks),
                total_chars=len(text),
                created_at=knowledge_doc["created_at"],
                updated_at=knowledge_doc["updated_at"]
            )

            return KnowledgeUploadResponse(
                knowledge=knowledge_response,
                message=f"Document uploaded and processed successfully ({len(chunks)} chunks created)"
            )

        except (DocumentParsingError, EmbeddingsError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error uploading knowledge: {str(e)}", exc_info=True)
            raise

    async def search_knowledge(
        self,
        query: str,
        company_id: str,
        top_k: int = 5,
        score_threshold: float = 0.5,
        tags: Optional[List[str]] = None,
        requesting_user_id: Optional[str] = None
    ) -> KnowledgeSearchResponse:
        """
        Semantic search in knowledge base

        Args:
            query: Search query
            company_id: Company ID to search within
            top_k: Number of results to return
            score_threshold: Minimum similarity score (0-1)
            tags: Filter by tags
            requesting_user_id: ID of user making request (for authorization)

        Returns:
            Search results

        Raises:
            EmbeddingsError: If embedding generation fails
            AuthorizationError: If user doesn't have permission
        """
        try:
            # Check authorization
            if requesting_user_id:
                await self._check_company_authorization(requesting_user_id, company_id)

            logger.info(f"Searching knowledge: query='{query}' company={company_id} top_k={top_k}")

            # Generate query embedding
            embeddings_provider = EmbeddingsFactory.create("gemini")
            embeddings_response = await embeddings_provider.embed([query])
            query_embedding = embeddings_response.embeddings[0]

            # Build search filter
            search_filter = {}
            if tags:
                search_filter["tags"] = {"$in": tags}

            # Search Qdrant
            search_results = await search_vectors(
                query_vector=query_embedding,
                company_id=company_id,
                top_k=top_k,
                score_threshold=score_threshold
            )

            logger.info(f"Found {len(search_results)} results")

            # Build response
            results = []
            for result in search_results:
                payload = result["payload"]
                chunk = KnowledgeChunkResponse(
                    chunk_index=payload["chunk_index"],
                    text=payload["text"],
                    score=result["score"],
                    metadata={
                        "char_count": payload.get("char_count"),
                        "token_count_estimate": payload.get("token_count_estimate")
                    }
                )

                results.append(
                    KnowledgeSearchResult(
                        knowledge_id=payload["knowledge_id"],
                        title=payload["title"],
                        chunk=chunk
                    )
                )

            return KnowledgeSearchResponse(
                query=query,
                results=results,
                total_results=len(results)
            )

        except (EmbeddingsError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error searching knowledge: {str(e)}", exc_info=True)
            raise

    async def build_rag_context(
        self,
        query: str,
        company_id: str,
        top_k: int = 5
    ) -> str:
        """
        Build RAG context for LLM from knowledge base

        This is used by the voice pipeline to inject relevant knowledge
        into the LLM prompt

        Args:
            query: User query
            company_id: Company ID
            top_k: Number of knowledge chunks to retrieve

        Returns:
            Formatted context string for LLM
        """
        try:
            # Search knowledge base
            search_response = await self.search_knowledge(
                query=query,
                company_id=company_id,
                top_k=top_k,
                score_threshold=0.5
            )

            if not search_response.results:
                return ""

            # Format results as context
            context_parts = ["Relevant information from knowledge base:\n"]

            for idx, result in enumerate(search_response.results, 1):
                context_parts.append(
                    f"\n[Source {idx}: {result.title}]\n{result.chunk.text}"
                )

            context = "\n".join(context_parts)

            logger.debug(
                f"Built RAG context: {len(search_response.results)} chunks, "
                f"{len(context)} characters"
            )

            return context

        except Exception as e:
            logger.error(f"Error building RAG context: {str(e)}", exc_info=True)
            # Return empty context on error (graceful degradation)
            return ""

    async def get_knowledge(
        self,
        knowledge_id: str,
        company_id: str,
        include_chunks: bool = False,
        requesting_user_id: Optional[str] = None
    ) -> KnowledgeResponse:
        """
        Get knowledge entry by ID

        Args:
            knowledge_id: Knowledge entry ID
            company_id: Company ID
            include_chunks: Whether to include chunks in response
            requesting_user_id: ID of user making request (for authorization)

        Returns:
            Knowledge entry

        Raises:
            KnowledgeNotFoundError: If knowledge not found
            AuthorizationError: If user doesn't have permission
        """
        try:
            Validators.validate_mongodb_id(knowledge_id, "knowledge_id")

            # Check authorization
            if requesting_user_id:
                await self._check_company_authorization(requesting_user_id, company_id)

            # Get knowledge entry
            knowledge = await self.knowledge_collection.find_one({
                "_id": ObjectId(knowledge_id),
                "company_id": company_id
            })

            if not knowledge:
                raise KnowledgeNotFoundError(f"Knowledge not found: {knowledge_id}")

            # Get chunks if requested
            chunks = None
            if include_chunks:
                # Get chunks from Qdrant
                search_results = await search_vectors(
                    query_vector=None,  # Get all chunks
                    company_id=company_id,
                    top_k=1000,  # Get all chunks
                    filter_payload={"knowledge_id": knowledge_id}
                )

                chunks = [
                    KnowledgeChunkResponse(
                        chunk_index=result["payload"]["chunk_index"],
                        text=result["payload"]["text"],
                        metadata={
                            "char_count": result["payload"].get("char_count"),
                            "token_count_estimate": result["payload"].get("token_count_estimate")
                        }
                    )
                    for result in sorted(search_results, key=lambda x: x["payload"]["chunk_index"])
                ]

            return KnowledgeResponse(
                id=str(knowledge["_id"]),
                company_id=knowledge["company_id"],
                title=knowledge["title"],
                description=knowledge.get("description"),
                tags=knowledge.get("tags", []),
                filename=knowledge["filename"],
                file_format=knowledge["file_format"],
                file_size=knowledge["file_size"],
                num_chunks=knowledge["num_chunks"],
                total_chars=knowledge["total_chars"],
                created_at=knowledge["created_at"],
                updated_at=knowledge["updated_at"],
                chunks=chunks
            )

        except (KnowledgeNotFoundError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error getting knowledge: {str(e)}", exc_info=True)
            raise

    async def list_knowledge(
        self,
        company_id: str,
        page: int = 1,
        page_size: int = 20,
        tags: Optional[List[str]] = None,
        requesting_user_id: Optional[str] = None
    ) -> KnowledgeListResponse:
        """
        List knowledge entries with pagination

        Args:
            company_id: Company ID
            page: Page number (1-indexed)
            page_size: Number of items per page
            tags: Filter by tags
            requesting_user_id: ID of user making request (for authorization)

        Returns:
            Paginated knowledge list

        Raises:
            AuthorizationError: If user doesn't have permission
        """
        try:
            # Check authorization
            if requesting_user_id:
                await self._check_company_authorization(requesting_user_id, company_id)

            # Build filter
            filter_doc: Dict[str, Any] = {"company_id": company_id}

            if tags:
                filter_doc["tags"] = {"$in": tags}

            # Get total count
            total = await self.knowledge_collection.count_documents(filter_doc)

            # Calculate pagination
            skip = (page - 1) * page_size
            total_pages = math.ceil(total / page_size) if total > 0 else 1

            # Get knowledge entries
            cursor = self.knowledge_collection.find(filter_doc).sort("created_at", -1).skip(skip).limit(page_size)
            entries = await cursor.to_list(length=page_size)

            # Build response
            knowledge_responses = [
                KnowledgeResponse(
                    id=str(entry["_id"]),
                    company_id=entry["company_id"],
                    title=entry["title"],
                    description=entry.get("description"),
                    tags=entry.get("tags", []),
                    filename=entry["filename"],
                    file_format=entry["file_format"],
                    file_size=entry["file_size"],
                    num_chunks=entry["num_chunks"],
                    total_chars=entry["total_chars"],
                    created_at=entry["created_at"],
                    updated_at=entry["updated_at"]
                )
                for entry in entries
            ]

            return KnowledgeListResponse(
                items=knowledge_responses,
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages
            )

        except AuthorizationError:
            raise
        except Exception as e:
            logger.error(f"Error listing knowledge: {str(e)}", exc_info=True)
            raise

    async def update_knowledge(
        self,
        knowledge_id: str,
        company_id: str,
        data: KnowledgeUpdateRequest,
        updating_user_id: Optional[str] = None
    ) -> KnowledgeResponse:
        """
        Update knowledge entry metadata

        Args:
            knowledge_id: Knowledge entry ID
            company_id: Company ID
            data: Update data
            updating_user_id: ID of user making update (for authorization)

        Returns:
            Updated knowledge entry

        Raises:
            KnowledgeNotFoundError: If knowledge not found
            AuthorizationError: If user doesn't have permission
        """
        try:
            Validators.validate_mongodb_id(knowledge_id, "knowledge_id")

            # Check authorization
            if updating_user_id:
                await self._check_company_authorization(updating_user_id, company_id)

            # Get knowledge entry
            knowledge = await self.knowledge_collection.find_one({
                "_id": ObjectId(knowledge_id),
                "company_id": company_id
            })

            if not knowledge:
                raise KnowledgeNotFoundError(f"Knowledge not found: {knowledge_id}")

            # Build update document
            update_doc = {"updated_at": datetime.utcnow()}

            if data.title is not None:
                update_doc["title"] = data.title

            if data.description is not None:
                update_doc["description"] = data.description

            if data.tags is not None:
                update_doc["tags"] = data.tags

            # Update MongoDB
            await self.knowledge_collection.update_one(
                {"_id": ObjectId(knowledge_id)},
                {"$set": update_doc}
            )

            # Update Qdrant payloads
            if data.title is not None or data.tags is not None:
                # Get all vector IDs for this knowledge entry
                # Update their payloads with new title/tags
                # Note: This is a simplified version, full implementation would batch update Qdrant
                pass

            logger.info(f"Knowledge updated: {knowledge_id}")

            return await self.get_knowledge(knowledge_id, company_id)

        except (KnowledgeNotFoundError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error updating knowledge: {str(e)}", exc_info=True)
            raise

    async def delete_knowledge(
        self,
        knowledge_id: str,
        company_id: str,
        deleting_user_id: Optional[str] = None
    ) -> None:
        """
        Delete knowledge entry and associated vectors

        Args:
            knowledge_id: Knowledge entry ID
            company_id: Company ID
            deleting_user_id: ID of user performing deletion (for authorization)

        Raises:
            KnowledgeNotFoundError: If knowledge not found
            AuthorizationError: If user doesn't have permission
        """
        try:
            Validators.validate_mongodb_id(knowledge_id, "knowledge_id")

            # Check authorization
            if deleting_user_id:
                await self._check_company_authorization(deleting_user_id, company_id)

            # Get knowledge entry
            knowledge = await self.knowledge_collection.find_one({
                "_id": ObjectId(knowledge_id),
                "company_id": company_id
            })

            if not knowledge:
                raise KnowledgeNotFoundError(f"Knowledge not found: {knowledge_id}")

            # Delete from MongoDB and Qdrant in parallel
            await asyncio.gather(
                self.knowledge_collection.delete_one({"_id": ObjectId(knowledge_id)}),
                delete_vectors_by_filter(
                    company_id=company_id,
                    filter_payload={"knowledge_id": knowledge_id}
                )
            )

            logger.info(f"Knowledge deleted: {knowledge_id}")

        except (KnowledgeNotFoundError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error deleting knowledge: {str(e)}", exc_info=True)
            raise

    async def _check_company_authorization(
        self,
        user_id: str,
        company_id: str
    ) -> None:
        """
        Check if user can access company's knowledge base

        Args:
            user_id: User ID
            company_id: Company ID

        Raises:
            AuthorizationError: If not authorized
        """
        user = await self.users_collection.find_one({"_id": int(user_id)})
        if not user:
            raise AuthorizationError("User not found")

        # Superadmin can access all companies
        if user["role"] == "superadmin":
            return

        # Admin can only access their own company
        if user["role"] == "admin":
            if user.get("company_id") != company_id:
                raise AuthorizationError("Cannot access other companies' knowledge base")
            return

        raise AuthorizationError("Insufficient permissions")


# Export service
__all__ = ["KnowledgeService"]
