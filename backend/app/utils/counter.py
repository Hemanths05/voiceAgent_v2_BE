"""
Auto-increment Counter Utility
Provides sequential numeric IDs for collections
"""
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Counter:
    """
    Auto-increment counter for generating sequential numeric IDs
    Uses MongoDB's findAndModify for atomic increments
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize counter with database instance

        Args:
            db: Motor database instance
        """
        self.db = db
        self.collection = db.counters

    async def get_next_sequence(self, sequence_name: str) -> int:
        """
        Get next sequence number for a given sequence

        Args:
            sequence_name: Name of the sequence (e.g., 'company', 'user', 'call')

        Returns:
            Next sequence number (starts from 1)

        Example:
            counter = Counter(db)
            company_number = await counter.get_next_sequence('company')
            # Returns: 1, 2, 3, ...
        """
        try:
            result = await self.collection.find_one_and_update(
                {"_id": sequence_name},
                {"$inc": {"sequence_value": 1}},
                upsert=True,
                return_document=True
            )

            if result:
                sequence_value = result.get("sequence_value", 1)
                logger.debug(f"Generated sequence {sequence_name}: {sequence_value}")
                return sequence_value
            else:
                # Fallback if something goes wrong
                logger.warning(f"Counter result was None for {sequence_name}, returning 1")
                return 1

        except Exception as e:
            logger.error(f"Error getting next sequence for {sequence_name}: {str(e)}", exc_info=True)
            # Return 1 as fallback to avoid breaking the flow
            return 1

    async def get_current_sequence(self, sequence_name: str) -> int:
        """
        Get current sequence value without incrementing

        Args:
            sequence_name: Name of the sequence

        Returns:
            Current sequence value (0 if not exists)
        """
        try:
            result = await self.collection.find_one({"_id": sequence_name})
            if result:
                return result.get("sequence_value", 0)
            return 0
        except Exception as e:
            logger.error(f"Error getting current sequence for {sequence_name}: {str(e)}", exc_info=True)
            return 0

    async def reset_sequence(self, sequence_name: str, value: int = 0) -> bool:
        """
        Reset sequence to a specific value (admin operation)

        Args:
            sequence_name: Name of the sequence
            value: Value to reset to (default 0)

        Returns:
            True if successful, False otherwise
        """
        try:
            await self.collection.update_one(
                {"_id": sequence_name},
                {"$set": {"sequence_value": value}},
                upsert=True
            )
            logger.info(f"Reset sequence {sequence_name} to {value}")
            return True
        except Exception as e:
            logger.error(f"Error resetting sequence {sequence_name}: {str(e)}", exc_info=True)
            return False


# Export
__all__ = ["Counter"]
