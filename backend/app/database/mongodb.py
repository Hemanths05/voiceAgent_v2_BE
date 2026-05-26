"""
MongoDB Database Connection
Manages connection to MongoDB using Motor (async driver)
"""
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure

from app.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Global database client and database instance
_client: Optional[AsyncIOMotorClient] = None
_database: Optional[AsyncIOMotorDatabase] = None


# ==================== Connection Management ====================

async def connect_to_mongo() -> None:
    """
    Connect to MongoDB and create indexes
    """
    global _client, _database

    try:
        logger.info(f"Connecting to MongoDB: {settings.mongodb_url.split('@')[-1]}")

        # Create client
        _client = AsyncIOMotorClient(
            settings.mongodb_url,
            maxPoolSize=settings.mongodb_max_pool_size,
            minPoolSize=settings.mongodb_min_pool_size,
            serverSelectionTimeoutMS=5000,
        )

        # Get database
        _database = _client[settings.mongodb_db_name]

        # Test connection
        await _client.admin.command("ping")

        logger.info(f"✓ Connected to MongoDB database: {settings.mongodb_db_name}")

        # Create indexes
        await create_indexes()

    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error connecting to MongoDB: {str(e)}", exc_info=True)
        raise


async def close_mongo_connection() -> None:
    """
    Close MongoDB connection
    """
    global _client

    if _client:
        _client.close()
        logger.info("MongoDB connection closed")


def get_database() -> AsyncIOMotorDatabase:
    """
    Get MongoDB database instance

    Returns:
        AsyncIOMotorDatabase instance

    Raises:
        RuntimeError: If database is not connected
    """
    if _database is None:
        raise RuntimeError("Database not connected. Call connect_to_mongo() first.")
    return _database


# ==================== Index Creation ====================

async def create_indexes() -> None:
    """
    Create database indexes for optimal query performance
    """
    db = get_database()

    logger.info("Creating database indexes...")

    # Users collection indexes
    await db.users.create_index([("email", ASCENDING)], unique=True)
    await db.users.create_index([("company_id", ASCENDING)])
    await db.users.create_index([("role", ASCENDING)])
    await db.users.create_index([("created_at", DESCENDING)])
    logger.info("✓ Created indexes for 'users' collection")

    # Companies collection indexes
    await db.companies.create_index([("phone_number", ASCENDING)], unique=True)
    await db.companies.create_index([("status", ASCENDING)])
    await db.companies.create_index([("created_at", DESCENDING)])
    logger.info("✓ Created indexes for 'companies' collection")

    # Knowledge bases collection indexes
    await db.knowledge_bases.create_index([("company_id", ASCENDING)])
    await db.knowledge_bases.create_index([("vector_id", ASCENDING)])
    await db.knowledge_bases.create_index(
        [("company_id", ASCENDING), ("created_at", DESCENDING)]
    )
    logger.info("✓ Created indexes for 'knowledge_bases' collection")

    # Calls collection indexes
    await db.calls.create_index([("call_sid", ASCENDING)], unique=True)
    await db.calls.create_index([("company_id", ASCENDING)])
    await db.calls.create_index([("status", ASCENDING)])
    await db.calls.create_index([("created_at", DESCENDING)])
    await db.calls.create_index(
        [("company_id", ASCENDING), ("created_at", DESCENDING)]
    )
    logger.info("✓ Created indexes for 'calls' collection")

    # Agent configs collection indexes
    await db.agent_configs.create_index([("company_id", ASCENDING)], unique=True)
    logger.info("✓ Created indexes for 'agent_configs' collection")

    logger.info("✓ All database indexes created successfully")


# ==================== Collection Helpers ====================

def get_collection(collection_name: str):
    """
    Get a MongoDB collection

    Args:
        collection_name: Name of the collection

    Returns:
        AsyncIOMotorCollection instance
    """
    db = get_database()
    return db[collection_name]


# Collection shortcuts
def get_users_collection():
    """Get users collection"""
    return get_collection("users")


def get_companies_collection():
    """Get companies collection"""
    return get_collection("companies")


def get_knowledge_bases_collection():
    """Get knowledge_bases collection"""
    return get_collection("knowledge_bases")


def get_calls_collection():
    """Get calls collection"""
    return get_collection("calls")


def get_agent_configs_collection():
    """Get agent_configs collection"""
    return get_collection("agent_configs")


# Export functions
__all__ = [
    "connect_to_mongo",
    "close_mongo_connection",
    "get_database",
    "create_indexes",
    "get_collection",
    "get_users_collection",
    "get_companies_collection",
    "get_knowledge_bases_collection",
    "get_calls_collection",
    "get_agent_configs_collection",
]
