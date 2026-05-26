"""
Call Service
Handles call management and tracking
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
import math

from app.core.exceptions import (
    CallNotFoundError,
    ValidationError,
    AuthorizationError
)
from app.core.logging_config import get_logger
from app.database.mongodb import get_database
from app.schemas.call import (
    CallCreate,
    CallUpdate,
    CallResponse,
    CallListResponse,
    CallStatsResponse,
    CallFilterParams,
    CallTranscriptMessage
)
from app.utils.validators import Validators

logger = get_logger(__name__)


class CallService:
    """
    Service for handling call management operations
    """

    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        """
        Initialize call service

        Args:
            db: MongoDB database instance (if None, will use get_database())
        """
        self.db = db or get_database()
        self.calls_collection = self.db.calls
        self.users_collection = self.db.users

    async def create_call(self, data: CallCreate) -> CallResponse:
        """
        Create a new call record

        Args:
            data: Call creation data

        Returns:
            Created call information
        """
        try:
            # Validate inputs
            Validators.validate_twilio_sid(data.call_sid, "Call SID", "call_sid")
            if not data.company_id:
                raise ValidationError("company_id is required", {"field": "company_id"})
            Validators.validate_phone(data.from_number, allow_twilio_format=True)
            Validators.validate_phone(data.to_number, allow_twilio_format=True)

            # Create call document
            call_doc = {
                "call_sid": data.call_sid,
                "company_id": data.company_id,
                "from_number": data.from_number,
                "to_number": data.to_number,
                "direction": data.direction,
                "status": "initiated",
                "duration": None,
                "transcript": [],
                "error_message": None,
                "metadata": {},
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            # Insert call
            result = await self.calls_collection.insert_one(call_doc)
            call_id = str(result.inserted_id)

            logger.info(f"Call created: {data.call_sid} (id={call_id})")

            return CallResponse(
                id=call_id,
                call_sid=data.call_sid,
                company_id=data.company_id,
                from_number=data.from_number,
                to_number=data.to_number,
                direction=data.direction,
                status="initiated",
                duration=None,
                transcript=[],
                error_message=None,
                metadata={},
                created_at=call_doc["created_at"],
                updated_at=call_doc["updated_at"]
            )

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error creating call: {str(e)}", exc_info=True)
            raise

    async def get_call(
        self,
        call_id: str,
        requesting_user_id: Optional[str] = None
    ) -> CallResponse:
        """
        Get call by ID

        Args:
            call_id: Call ID
            requesting_user_id: ID of user making request (for authorization)

        Returns:
            Call information

        Raises:
            CallNotFoundError: If call not found
            AuthorizationError: If user doesn't have permission
        """
        try:
            Validators.validate_mongodb_id(call_id, "call_id")

            # Get call
            call = await self.calls_collection.find_one({"_id": ObjectId(call_id)})

            if not call:
                raise CallNotFoundError(f"Call not found: {call_id}")

            # Check authorization
            if requesting_user_id:
                await self._check_call_authorization(requesting_user_id, call["company_id"])

            return self._build_call_response(call)

        except (CallNotFoundError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error getting call: {str(e)}", exc_info=True)
            raise

    async def get_call_by_sid(
        self,
        call_sid: str,
        requesting_user_id: Optional[str] = None
    ) -> CallResponse:
        """
        Get call by Twilio Call SID

        Args:
            call_sid: Twilio Call SID
            requesting_user_id: ID of user making request (for authorization)

        Returns:
            Call information

        Raises:
            CallNotFoundError: If call not found
            AuthorizationError: If user doesn't have permission
        """
        try:
            Validators.validate_twilio_sid(call_sid, "Call SID", "call_sid")

            # Get call
            call = await self.calls_collection.find_one({"call_sid": call_sid})

            if not call:
                raise CallNotFoundError(f"Call not found: {call_sid}")

            # Check authorization
            if requesting_user_id:
                await self._check_call_authorization(requesting_user_id, call["company_id"])

            return self._build_call_response(call)

        except (CallNotFoundError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error getting call by SID: {str(e)}", exc_info=True)
            raise

    async def update_call(
        self,
        call_id: str,
        data: CallUpdate,
        updating_user_id: Optional[str] = None
    ) -> CallResponse:
        """
        Update call information

        Args:
            call_id: Call ID
            data: Update data
            updating_user_id: ID of user making update (for authorization)

        Returns:
            Updated call information

        Raises:
            CallNotFoundError: If call not found
            ValidationError: If validation fails
            AuthorizationError: If user doesn't have permission
        """
        try:
            Validators.validate_mongodb_id(call_id, "call_id")

            # Get call
            call = await self.calls_collection.find_one({"_id": ObjectId(call_id)})

            if not call:
                raise CallNotFoundError(f"Call not found: {call_id}")

            # Check authorization (optional for system updates)
            if updating_user_id:
                await self._check_call_authorization(updating_user_id, call["company_id"])

            # Build update document
            update_doc = {"updated_at": datetime.utcnow()}

            if data.status is not None:
                update_doc["status"] = data.status

            if data.duration is not None:
                update_doc["duration"] = data.duration

            if data.transcript is not None:
                # Convert Pydantic models to dicts
                update_doc["transcript"] = [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp
                    }
                    for msg in data.transcript
                ]

            if data.error_message is not None:
                update_doc["error_message"] = data.error_message

            if data.metadata is not None:
                update_doc["metadata"] = data.metadata

            # Update call
            await self.calls_collection.update_one(
                {"_id": ObjectId(call_id)},
                {"$set": update_doc}
            )

            logger.debug(f"Call updated: {call_id}")

            # Return updated call
            return await self.get_call(call_id)

        except (CallNotFoundError, ValidationError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error updating call: {str(e)}", exc_info=True)
            raise

    async def update_call_by_sid(
        self,
        call_sid: str,
        data: CallUpdate
    ) -> CallResponse:
        """
        Update call by Twilio Call SID (for system updates during call)

        Args:
            call_sid: Twilio Call SID
            data: Update data

        Returns:
            Updated call information

        Raises:
            CallNotFoundError: If call not found
        """
        try:
            Validators.validate_twilio_sid(call_sid, "Call SID", "call_sid")

            # Get call
            call = await self.calls_collection.find_one({"call_sid": call_sid})

            if not call:
                raise CallNotFoundError(f"Call not found: {call_sid}")

            # Build update document
            update_doc = {"updated_at": datetime.utcnow()}

            if data.status is not None:
                update_doc["status"] = data.status

            if data.duration is not None:
                update_doc["duration"] = data.duration

            if data.transcript is not None:
                update_doc["transcript"] = [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp
                    }
                    for msg in data.transcript
                ]

            if data.error_message is not None:
                update_doc["error_message"] = data.error_message

            if data.metadata is not None:
                update_doc["metadata"] = data.metadata

            # Update call
            await self.calls_collection.update_one(
                {"call_sid": call_sid},
                {"$set": update_doc}
            )

            logger.debug(f"Call updated by SID: {call_sid}")

            # Return updated call
            return await self.get_call_by_sid(call_sid)

        except (CallNotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error updating call by SID: {str(e)}", exc_info=True)
            raise

    async def list_calls(
        self,
        company_id: str,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[CallFilterParams] = None,
        requesting_user_id: Optional[str] = None
    ) -> CallListResponse:
        """
        List calls with pagination and filtering

        Args:
            company_id: Company ID
            page: Page number (1-indexed)
            page_size: Number of items per page
            filters: Filter parameters
            requesting_user_id: ID of user making request (for authorization)

        Returns:
            Paginated call list

        Raises:
            AuthorizationError: If user doesn't have permission
        """
        try:
            if not company_id:
                raise ValidationError("company_id is required", {"field": "company_id"})

            # Check authorization
            if requesting_user_id:
                await self._check_call_authorization(requesting_user_id, company_id)

            # Build filter
            filter_doc: Dict[str, Any] = {"company_id": company_id}

            if filters:
                if filters.status:
                    filter_doc["status"] = filters.status

                if filters.from_number:
                    filter_doc["from_number"] = filters.from_number

                if filters.direction:
                    filter_doc["direction"] = filters.direction

                if filters.start_date or filters.end_date:
                    date_filter = {}
                    if filters.start_date:
                        date_filter["$gte"] = filters.start_date
                    if filters.end_date:
                        date_filter["$lte"] = filters.end_date
                    filter_doc["created_at"] = date_filter

                if filters.min_duration or filters.max_duration:
                    duration_filter = {}
                    if filters.min_duration:
                        duration_filter["$gte"] = filters.min_duration
                    if filters.max_duration:
                        duration_filter["$lte"] = filters.max_duration
                    filter_doc["duration"] = duration_filter

            # Get total count
            total = await self.calls_collection.count_documents(filter_doc)

            # Calculate pagination
            skip = (page - 1) * page_size
            total_pages = math.ceil(total / page_size) if total > 0 else 1

            # Get calls
            cursor = self.calls_collection.find(filter_doc).sort("created_at", -1).skip(skip).limit(page_size)
            calls = await cursor.to_list(length=page_size)

            # Build response
            call_responses = [self._build_call_response(call) for call in calls]

            return CallListResponse(
                items=call_responses,
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages
            )

        except AuthorizationError:
            raise
        except Exception as e:
            logger.error(f"Error listing calls: {str(e)}", exc_info=True)
            raise

    async def get_call_stats(
        self,
        company_id: str,
        requesting_user_id: Optional[str] = None
    ) -> CallStatsResponse:
        """
        Get call statistics for a company

        Args:
            company_id: Company ID
            requesting_user_id: ID of user making request (for authorization)

        Returns:
            Call statistics

        Raises:
            AuthorizationError: If user doesn't have permission
        """
        try:
            if not company_id:
                raise ValidationError("company_id is required", {"field": "company_id"})

            # Check authorization
            if requesting_user_id:
                await self._check_call_authorization(requesting_user_id, company_id)

            # Get total calls
            total_calls = await self.calls_collection.count_documents({"company_id": company_id})

            # Get calls by status
            completed_calls = await self.calls_collection.count_documents({
                "company_id": company_id,
                "status": "completed"
            })

            failed_calls = await self.calls_collection.count_documents({
                "company_id": company_id,
                "status": "failed"
            })

            in_progress_calls = await self.calls_collection.count_documents({
                "company_id": company_id,
                "status": "in_progress"
            })

            # Calculate average and total duration
            pipeline = [
                {"$match": {"company_id": company_id, "duration": {"$exists": True, "$ne": None}}},
                {"$group": {
                    "_id": None,
                    "avg_duration": {"$avg": "$duration"},
                    "total_duration": {"$sum": "$duration"}
                }}
            ]
            duration_result = await self.calls_collection.aggregate(pipeline).to_list(1)
            avg_duration = duration_result[0]["avg_duration"] if duration_result else 0.0
            total_duration = duration_result[0]["total_duration"] if duration_result else 0.0

            # Get time-based stats
            now = datetime.utcnow()
            today_start = datetime(now.year, now.month, now.day)
            week_start = today_start - timedelta(days=today_start.weekday())
            month_start = datetime(now.year, now.month, 1)

            calls_today = await self.calls_collection.count_documents({
                "company_id": company_id,
                "created_at": {"$gte": today_start}
            })

            calls_this_week = await self.calls_collection.count_documents({
                "company_id": company_id,
                "created_at": {"$gte": week_start}
            })

            calls_this_month = await self.calls_collection.count_documents({
                "company_id": company_id,
                "created_at": {"$gte": month_start}
            })

            return CallStatsResponse(
                company_id=company_id,
                total_calls=total_calls,
                completed_calls=completed_calls,
                failed_calls=failed_calls,
                in_progress_calls=in_progress_calls,
                avg_duration=avg_duration,
                total_duration=total_duration,
                calls_today=calls_today,
                calls_this_week=calls_this_week,
                calls_this_month=calls_this_month
            )

        except AuthorizationError:
            raise
        except Exception as e:
            logger.error(f"Error getting call stats: {str(e)}", exc_info=True)
            raise

    def _build_call_response(self, call: dict) -> CallResponse:
        """
        Build call response from MongoDB document

        Args:
            call: MongoDB document

        Returns:
            Call response
        """
        # Convert transcript dicts to Pydantic models
        transcript = None
        if call.get("transcript"):
            transcript = [
                CallTranscriptMessage(
                    role=msg["role"],
                    content=msg["content"],
                    timestamp=msg["timestamp"]
                )
                for msg in call["transcript"]
            ]

        return CallResponse(
            id=str(call["_id"]),
            call_sid=call["call_sid"],
            company_id=call["company_id"],
            from_number=call["from_number"],
            to_number=call["to_number"],
            direction=call["direction"],
            status=call["status"],
            duration=call.get("duration"),
            transcript=transcript,
            error_message=call.get("error_message"),
            metadata=call.get("metadata", {}),
            created_at=call["created_at"],
            updated_at=call["updated_at"]
        )

    async def _check_call_authorization(
        self,
        user_id: str,
        company_id: str
    ) -> None:
        """
        Check if user can access calls for company

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
                raise AuthorizationError("Cannot access other companies' calls")
            return

        raise AuthorizationError("Insufficient permissions")


# Export service
__all__ = ["CallService"]
