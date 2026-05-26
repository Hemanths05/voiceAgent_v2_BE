"""
Company Service
Handles company CRUD operations and management
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
import math

from app.core.exceptions import (
    CompanyNotFoundError,
    ValidationError,
    AuthorizationError
)
from app.core.logging_config import get_logger
from app.database.mongodb import get_database
from app.schemas.company import (
    CompanyCreate,
    CompanyUpdate,
    CompanyStatusUpdate,
    CompanyResponse,
    CompanyListResponse,
    CompanyStatsResponse,
    DashboardMetricsResponse
)
from app.utils.validators import Validators
from app.utils.counter import Counter

logger = get_logger(__name__)


class CompanyService:
    """
    Service for handling company management operations
    """

    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        """
        Initialize company service

        Args:
            db: MongoDB database instance (if None, will use get_database())
        """
        self.db = db or get_database()
        self.companies_collection = self.db.companies
        self.users_collection = self.db.users
        self.calls_collection = self.db.calls
        self.agent_configs_collection = self.db.agent_configs
        self.counter = Counter(self.db)

    async def create_company(
        self,
        data: CompanyCreate,
        created_by_user_id: Optional[str] = None
    ) -> CompanyResponse:
        """
        Create a new company

        Args:
            data: Company creation data
            created_by_user_id: ID of user creating this company (for authorization)

        Returns:
            Created company information

        Raises:
            ValidationError: If validation fails
            AuthorizationError: If user doesn't have permission
        """
        try:
            # Check authorization - only superadmin can create companies
            if created_by_user_id:
                creator = await self.users_collection.find_one({"_id": int(created_by_user_id)})
                if not creator or creator["role"] != "superadmin":
                    raise AuthorizationError("Only superadmin can create companies")

            # Validate phone number
            phone_number = Validators.validate_phone(data.phone_number, allow_twilio_format=True)

            # Check if phone number already exists
            existing_company = await self.companies_collection.find_one({"phone_number": phone_number})
            if existing_company:
                raise ValidationError(
                    f"Company with phone number {phone_number} already exists",
                    {"phone_number": phone_number}
                )

            # Get next company ID from counter
            company_id = await self.counter.get_next_sequence("company")

            # Create company document with sequential _id
            company_doc = {
                "_id": company_id,
                "name": data.name,
                "phone_number": phone_number,
                "description": data.description,
                "industry": data.industry,
                "status": data.status or "active",
                "subscription_tier": data.subscription_tier or "free",
                "ai_provider": data.ai_provider,
                "stt_provider": data.stt_provider,
                "tts_provider": data.tts_provider,
                "max_users": data.max_users,
                "max_monthly_calls": data.max_monthly_calls,
                "current_call_count": 0,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            # Insert company
            await self.companies_collection.insert_one(company_doc)

            # Create default agent configuration for company
            await self._create_default_agent_config(str(company_id))

            logger.info(f"Company created: {data.name} (id={company_id}, phone={phone_number})")

            return CompanyResponse(
                id=company_id,
                name=data.name,
                phone_number=phone_number,
                description=data.description,
                industry=data.industry,
                status=company_doc["status"],
                subscription_tier=company_doc["subscription_tier"],
                ai_provider=data.ai_provider,
                stt_provider=data.stt_provider,
                tts_provider=data.tts_provider,
                max_users=data.max_users,
                max_monthly_calls=data.max_monthly_calls,
                current_call_count=0,
                created_at=company_doc["created_at"],
                updated_at=company_doc["updated_at"],
                total_calls=0,
                total_admins=0
            )

        except (ValidationError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error creating company: {str(e)}", exc_info=True)
            raise

    async def get_company(
        self,
        company_id: str,
        requesting_user_id: Optional[str] = None,
        include_stats: bool = False
    ) -> CompanyResponse:
        """
        Get company by ID

        Args:
            company_id: Company ID to retrieve
            requesting_user_id: ID of user making the request (for authorization)
            include_stats: Whether to include statistics

        Returns:
            Company information

        Raises:
            CompanyNotFoundError: If company not found
            AuthorizationError: If user doesn't have permission
        """
        try:
            # Validate company_id is provided
            if not company_id:
                raise ValidationError("company_id is required", {"field": "company_id"})

            # Get company
            company = await self.companies_collection.find_one({"_id": int(company_id)})
            if not company:
                raise CompanyNotFoundError(f"Company not found: {company_id}")

            # Check authorization
            if requesting_user_id:
                await self._check_company_access_authorization(requesting_user_id, company_id)

            # Get stats if requested
            total_calls = None
            total_admins = None
            if include_stats:
                total_calls = await self.calls_collection.count_documents({"company_id": company_id})
                total_admins = await self.users_collection.count_documents({
                    "company_id": company_id,
                    "role": "admin"
                })

            return CompanyResponse(
                id=company["_id"],
                company_number=company["_id"],
                name=company["name"],
                phone_number=company["phone_number"],
                description=company.get("description"),
                industry=company.get("industry"),
                status=company["status"],
                subscription_tier=company.get("subscription_tier", "free"),
                ai_provider=company.get("ai_provider"),
                stt_provider=company.get("stt_provider"),
                tts_provider=company.get("tts_provider"),
                max_users=company.get("max_users"),
                max_monthly_calls=company.get("max_monthly_calls"),
                current_call_count=company.get("current_call_count", 0),
                created_at=company["created_at"],
                updated_at=company["updated_at"],
                total_calls=total_calls,
                total_admins=total_admins
            )

        except (CompanyNotFoundError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error getting company: {str(e)}", exc_info=True)
            raise

    async def get_company_by_phone(
        self,
        phone_number: str
    ) -> CompanyResponse:
        """
        Get company by phone number

        Args:
            phone_number: Company's Twilio phone number

        Returns:
            Company information

        Raises:
            CompanyNotFoundError: If company not found for this phone number
        """
        try:
            # Validate phone number format
            validated_phone = Validators.validate_phone(phone_number, allow_twilio_format=True)

            # Get company by phone number
            company = await self.companies_collection.find_one({"phone_number": validated_phone})
            if not company:
                raise CompanyNotFoundError(f"Company not found for phone number: {phone_number}")

            # Get basic stats
            total_calls = await self.calls_collection.count_documents({"company_id": company["_id"]})
            total_admins = await self.users_collection.count_documents({
                "company_id": company["_id"],
                "role": "admin"
            })

            return CompanyResponse(
                id=company["_id"],
                company_number=company["_id"],
                name=company["name"],
                phone_number=company["phone_number"],
                description=company.get("description"),
                industry=company.get("industry"),
                status=company["status"],
                subscription_tier=company.get("subscription_tier", "free"),
                ai_provider=company.get("ai_provider"),
                stt_provider=company.get("stt_provider"),
                tts_provider=company.get("tts_provider"),
                max_users=company.get("max_users"),
                max_monthly_calls=company.get("max_monthly_calls"),
                current_call_count=company.get("current_call_count", 0),
                created_at=company["created_at"],
                updated_at=company["updated_at"],
                total_calls=total_calls,
                total_admins=total_admins
            )

        except CompanyNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting company by phone: {str(e)}", exc_info=True)
            raise

    async def update_company(
        self,
        company_id: str,
        data: CompanyUpdate,
        updating_user_id: Optional[str] = None
    ) -> CompanyResponse:
        """
        Update company information

        Args:
            company_id: Company ID to update
            data: Update data
            updating_user_id: ID of user making the update (for authorization)

        Returns:
            Updated company information

        Raises:
            CompanyNotFoundError: If company not found
            ValidationError: If validation fails
            AuthorizationError: If user doesn't have permission
        """
        try:
            # Validate company_id is provided
            if not company_id:
                raise ValidationError("company_id is required", {"field": "company_id"})

            # Get company
            company = await self.companies_collection.find_one({"_id": int(company_id)})
            if not company:
                raise CompanyNotFoundError(f"Company not found: {company_id}")

            # Check authorization - only superadmin can update companies
            if updating_user_id:
                updater = await self.users_collection.find_one({"_id": int(updating_user_id)})
                if not updater or updater["role"] != "superadmin":
                    raise AuthorizationError("Only superadmin can update companies")

            # Build update document
            update_doc = {"updated_at": datetime.utcnow()}

            if data.name is not None:
                update_doc["name"] = data.name

            if data.phone_number is not None:
                phone_number = Validators.validate_phone(data.phone_number, allow_twilio_format=True)
                # Check if new phone number already exists (excluding current company)
                existing = await self.companies_collection.find_one({
                    "phone_number": phone_number,
                    "_id": {"$ne": int(company_id)}
                })
                if existing:
                    raise ValidationError(
                        f"Phone number {phone_number} already in use",
                        {"phone_number": phone_number}
                    )
                update_doc["phone_number"] = phone_number

            if data.description is not None:
                update_doc["description"] = data.description

            if data.industry is not None:
                update_doc["industry"] = data.industry

            if data.status is not None:
                update_doc["status"] = data.status

            if data.subscription_tier is not None:
                update_doc["subscription_tier"] = data.subscription_tier

            if data.ai_provider is not None:
                update_doc["ai_provider"] = data.ai_provider

            if data.stt_provider is not None:
                update_doc["stt_provider"] = data.stt_provider

            if data.tts_provider is not None:
                update_doc["tts_provider"] = data.tts_provider

            if data.max_users is not None:
                update_doc["max_users"] = data.max_users

            if data.max_monthly_calls is not None:
                update_doc["max_monthly_calls"] = data.max_monthly_calls

            # Update company
            await self.companies_collection.update_one(
                {"_id": int(company_id)},
                {"$set": update_doc}
            )

            logger.info(f"Company updated: {company_id}")

            # Return updated company
            return await self.get_company(company_id)

        except (CompanyNotFoundError, ValidationError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error updating company: {str(e)}", exc_info=True)
            raise

    async def update_company_status(
        self,
        company_id: str,
        data: CompanyStatusUpdate,
        updating_user_id: Optional[str] = None
    ) -> CompanyResponse:
        """
        Update company status

        Args:
            company_id: Company ID to update
            data: Status update data
            updating_user_id: ID of user making the update (for authorization)

        Returns:
            Updated company information

        Raises:
            CompanyNotFoundError: If company not found
            AuthorizationError: If user doesn't have permission
        """
        try:
            # Validate company_id is provided
            if not company_id:
                raise ValidationError("company_id is required", {"field": "company_id"})

            # Get company
            company = await self.companies_collection.find_one({"_id": int(company_id)})
            if not company:
                raise CompanyNotFoundError(f"Company not found: {company_id}")

            # Check authorization - only superadmin can update status
            if updating_user_id:
                updater = await self.users_collection.find_one({"_id": int(updating_user_id)})
                if not updater or updater["role"] != "superadmin":
                    raise AuthorizationError("Only superadmin can update company status")

            # Update status
            await self.companies_collection.update_one(
                {"_id": int(company_id)},
                {
                    "$set": {
                        "status": data.status,
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            logger.info(f"Company status updated: {company_id} -> {data.status}")

            # Return updated company
            return await self.get_company(company_id)

        except (CompanyNotFoundError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error updating company status: {str(e)}", exc_info=True)
            raise

    async def list_companies(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        industry: Optional[str] = None,
        requesting_user_id: Optional[str] = None
    ) -> CompanyListResponse:
        """
        List companies with pagination and filtering

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            status: Filter by status
            industry: Filter by industry
            requesting_user_id: ID of user making the request (for authorization)

        Returns:
            Paginated company list

        Raises:
            AuthorizationError: If user doesn't have permission
        """
        try:
            # Check authorization - only superadmin can list all companies
            if requesting_user_id:
                requester = await self.users_collection.find_one({"_id": int(requesting_user_id)})
                if not requester or requester["role"] != "superadmin":
                    raise AuthorizationError("Only superadmin can list companies")

            # Build filter
            filter_doc: Dict[str, Any] = {}

            if status:
                filter_doc["status"] = status

            if industry:
                filter_doc["industry"] = industry

            # Get total count
            total = await self.companies_collection.count_documents(filter_doc)

            # Calculate pagination
            skip = (page - 1) * page_size
            total_pages = math.ceil(total / page_size) if total > 0 else 1

            # Get companies
            cursor = self.companies_collection.find(filter_doc).sort("created_at", -1).skip(skip).limit(page_size)
            companies = await cursor.to_list(length=page_size)

            # Build response with stats
            company_responses = []
            for company in companies:
                company_id = company["_id"]
                total_calls = await self.calls_collection.count_documents({"company_id": company_id})
                total_admins = await self.users_collection.count_documents({
                    "company_id": company_id,
                    "role": "admin"
                })

                company_responses.append(
                    CompanyResponse(
                        id=company_id,
                        company_number=company["_id"],
                        name=company["name"],
                        phone_number=company["phone_number"],
                        description=company.get("description"),
                        industry=company.get("industry"),
                        status=company["status"],
                        subscription_tier=company.get("subscription_tier", "free"),
                        ai_provider=company.get("ai_provider"),
                        stt_provider=company.get("stt_provider"),
                        tts_provider=company.get("tts_provider"),
                        max_users=company.get("max_users"),
                        max_monthly_calls=company.get("max_monthly_calls"),
                        current_call_count=company.get("current_call_count", 0),
                        created_at=company["created_at"],
                        updated_at=company["updated_at"],
                        total_calls=total_calls,
                        total_admins=total_admins
                    )
                )

            return CompanyListResponse(
                companies=company_responses,
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages
            )

        except AuthorizationError:
            raise
        except Exception as e:
            logger.error(f"Error listing companies: {str(e)}", exc_info=True)
            raise

    async def get_company_stats(
        self,
        company_id: str,
        requesting_user_id: Optional[str] = None
    ) -> CompanyStatsResponse:
        """
        Get detailed statistics for a company

        Args:
            company_id: Company ID
            requesting_user_id: ID of user making the request (for authorization)

        Returns:
            Company statistics

        Raises:
            CompanyNotFoundError: If company not found
            AuthorizationError: If user doesn't have permission
        """
        try:
            # Validate company_id is provided
            if not company_id:
                raise ValidationError("company_id is required", {"field": "company_id"})

            # Get company
            company = await self.companies_collection.find_one({"_id": int(company_id)})
            if not company:
                raise CompanyNotFoundError(f"Company not found: {company_id}")

            # Check authorization
            if requesting_user_id:
                await self._check_company_access_authorization(requesting_user_id, company_id)

            # Get call statistics
            total_calls = await self.calls_collection.count_documents({"company_id": company_id})
            successful_calls = await self.calls_collection.count_documents({
                "company_id": company_id,
                "status": "completed"
            })
            failed_calls = await self.calls_collection.count_documents({
                "company_id": company_id,
                "status": "failed"
            })

            # Calculate average call duration
            pipeline = [
                {"$match": {"company_id": company_id, "duration": {"$exists": True, "$ne": None}}},
                {"$group": {"_id": None, "avg_duration": {"$avg": "$duration"}}}
            ]
            avg_result = await self.calls_collection.aggregate(pipeline).to_list(1)
            avg_duration = avg_result[0]["avg_duration"] if avg_result else 0.0

            # Get knowledge base entries count
            total_knowledge_entries = await self.db.knowledge_bases.count_documents({"company_id": company_id})

            # Get admin users count
            total_admins = await self.users_collection.count_documents({
                "company_id": company_id,
                "role": "admin"
            })

            # Get last call timestamp
            last_call = await self.calls_collection.find_one(
                {"company_id": company_id},
                sort=[("created_at", -1)]
            )
            last_call_at = last_call["created_at"] if last_call else None

            return CompanyStatsResponse(
                company_id=company_id,
                total_calls=total_calls,
                successful_calls=successful_calls,
                failed_calls=failed_calls,
                avg_call_duration=avg_duration,
                total_knowledge_entries=total_knowledge_entries,
                total_admins=total_admins,
                last_call_at=last_call_at
            )

        except (CompanyNotFoundError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error getting company stats: {str(e)}", exc_info=True)
            raise

    async def get_dashboard_metrics(
        self,
        company_id,
        requesting_user_id: Optional[str] = None
    ) -> DashboardMetricsResponse:
        """
        Get dashboard metrics for admin dashboard

        Args:
            company_id: Company ID (int or str)
            requesting_user_id: ID of user making the request (for authorization)

        Returns:
            Dashboard metrics matching frontend DashboardMetrics type

        Raises:
            CompanyNotFoundError: If company not found
            AuthorizationError: If user doesn't have permission
        """
        try:
            if not company_id:
                raise ValidationError("company_id is required", {"field": "company_id"})

            # Ensure company_id is int for consistent MongoDB queries
            int_company_id = int(company_id)

            company = await self.companies_collection.find_one({"_id": int_company_id})
            if not company:
                raise CompanyNotFoundError(f"Company not found: {company_id}")

            if requesting_user_id:
                await self._check_company_access_authorization(requesting_user_id, str(company_id))

            # Call counts by status — query with both int and str to handle mixed storage
            call_filter = {"company_id": {"$in": [int_company_id, str(int_company_id)]}}

            total_calls = await self.calls_collection.count_documents(call_filter)
            active_calls = await self.calls_collection.count_documents({
                **call_filter,
                "status": {"$in": ["initiated", "in_progress", "ringing"]}
            })
            completed_calls = await self.calls_collection.count_documents({
                **call_filter,
                "status": "completed"
            })
            failed_calls = await self.calls_collection.count_documents({
                **call_filter,
                "status": "failed"
            })

            # Duration aggregation
            pipeline = [
                {"$match": {**call_filter, "duration": {"$exists": True, "$ne": None}}},
                {"$group": {
                    "_id": None,
                    "avg_duration": {"$avg": "$duration"},
                    "total_duration": {"$sum": "$duration"}
                }}
            ]
            duration_result = await self.calls_collection.aggregate(pipeline).to_list(1)
            avg_duration = duration_result[0]["avg_duration"] if duration_result else 0.0
            total_duration = duration_result[0]["total_duration"] if duration_result else 0.0

            # Knowledge base counts — also handle both int and str
            kb_filter = {"company_id": {"$in": [int_company_id, str(int_company_id)]}}
            knowledge_docs_count = await self.db.knowledge_bases.count_documents(kb_filter)

            # Sum up num_chunks across all knowledge docs
            chunks_pipeline = [
                {"$match": kb_filter},
                {"$group": {"_id": None, "total_chunks": {"$sum": "$num_chunks"}}}
            ]
            chunks_result = await self.db.knowledge_bases.aggregate(chunks_pipeline).to_list(1)
            knowledge_chunks_count = chunks_result[0]["total_chunks"] if chunks_result else 0

            return DashboardMetricsResponse(
                total_calls=total_calls,
                active_calls=active_calls,
                completed_calls=completed_calls,
                failed_calls=failed_calls,
                total_duration_minutes=round(total_duration / 60, 2) if total_duration else 0,
                avg_call_duration_seconds=round(avg_duration, 2) if avg_duration else 0,
                knowledge_docs_count=knowledge_docs_count,
                knowledge_chunks_count=knowledge_chunks_count
            )

        except (CompanyNotFoundError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error getting dashboard metrics: {str(e)}", exc_info=True)
            raise

    async def _create_default_agent_config(self, company_id: str) -> None:
        """
        Create default agent configuration for new company

        Args:
            company_id: Company ID
        """
        from app.config import settings

        default_config = {
            "company_id": company_id,
            # AI Provider selection
            "stt_provider": settings.stt_provider,
            "llm_provider": settings.llm_provider,
            "tts_provider": settings.tts_provider,
            "embeddings_provider": settings.embeddings_provider,
            # LLM parameters
            "temperature": 0.7,
            "max_tokens": 150,
            "top_p": 1.0,
            # Agent behavior
            "system_prompt": "You are a helpful customer support agent. Be concise, friendly, and professional.",
            "greeting_message": "Hello! Thank you for calling. How can I help you today?",
            "enable_rag": True,
            "rag_top_k": 5,
            "conversation_history_limit": 10,
            # Advanced settings
            "enable_interruption": True,
            "silence_timeout": 2.0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        await self.agent_configs_collection.insert_one(default_config)
        logger.info(f"Created default agent config for company: {company_id}")

    async def _check_company_access_authorization(
        self,
        requesting_user_id: str,
        company_id: str
    ) -> None:
        """
        Check if requesting user can access company information

        Args:
            requesting_user_id: ID of user making the request
            company_id: Company ID to access

        Raises:
            AuthorizationError: If not authorized
        """
        requesting_user = await self.users_collection.find_one({"_id": int(requesting_user_id)})
        if not requesting_user:
            raise AuthorizationError("Requesting user not found")

        # Superadmin can access all companies
        if requesting_user["role"] == "superadmin":
            return

        # Admin can only access their own company
        if requesting_user["role"] == "admin":
            if requesting_user.get("company_id") != company_id:
                raise AuthorizationError("Cannot access other companies")
            return

        raise AuthorizationError("Insufficient permissions")


# Export service
__all__ = ["CompanyService"]
