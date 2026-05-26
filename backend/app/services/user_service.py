"""
User Service
Handles user CRUD operations and management
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
import math

from app.core.security import get_password_hash
from app.core.exceptions import (
    UserNotFoundError,
    UserAlreadyExistsError,
    ValidationError,
    AuthorizationError
)
from app.core.logging_config import get_logger
from app.database.mongodb import get_database
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserListResponse
from app.utils.validators import Validators

logger = get_logger(__name__)


class UserService:
    """
    Service for handling user management operations
    """

    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        """
        Initialize user service

        Args:
            db: MongoDB database instance (if None, will use get_database())
        """
        self.db = db or get_database()
        self.users_collection = self.db.users

    async def create_user(self, data: UserCreate, created_by_user_id: Optional[str] = None) -> UserResponse:
        """
        Create a new user

        Args:
            data: User creation data
            created_by_user_id: ID of user creating this user (for authorization check)

        Returns:
            Created user information

        Raises:
            UserAlreadyExistsError: If email already exists
            ValidationError: If validation fails
            AuthorizationError: If created_by user doesn't have permission
        """
        try:
            # Validate email
            email = Validators.validate_email(data.email)

            # Check if user already exists
            existing_user = await self.users_collection.find_one({"email": email})
            if existing_user:
                raise UserAlreadyExistsError(f"User with email {email} already exists")

            # If created by another user, check authorization
            if created_by_user_id:
                creator = await self.users_collection.find_one({"_id": ObjectId(created_by_user_id)})
                if not creator:
                    raise AuthorizationError("Creator user not found")

                # Only superadmin can create users
                if creator["role"] != "superadmin":
                    raise AuthorizationError("Only superadmin can create users")

            # Validate company_id if provided
            if data.company_id:
                Validators.validate_mongodb_id(data.company_id, "company_id")
                company = await self.db.companies.find_one({"_id": ObjectId(data.company_id)})
                if not company:
                    raise ValidationError("Invalid company_id", {"company_id": data.company_id})

            # Validate role
            if data.role not in ["superadmin", "admin"]:
                raise ValidationError("Invalid role", {"role": data.role})

            # Admin users must have company_id
            if data.role == "admin" and not data.company_id:
                raise ValidationError("Admin users must have company_id")

            # Hash password
            hashed_password = get_password_hash(data.password)

            # Create user document
            user_doc = {
                "email": email,
                "hashed_password": hashed_password,
                "full_name": data.full_name,
                "role": data.role,
                "company_id": data.company_id,
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            # Insert user
            result = await self.users_collection.insert_one(user_doc)
            user_id = str(result.inserted_id)

            logger.info(f"User created: {email} (role={data.role}, id={user_id})")

            return UserResponse(
                id=user_id,
                email=email,
                full_name=data.full_name,
                role=data.role,
                company_id=data.company_id,
                is_active=True,
                created_at=user_doc["created_at"],
                updated_at=user_doc["updated_at"]
            )

        except (UserAlreadyExistsError, ValidationError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}", exc_info=True)
            raise

    async def get_user(self, user_id: str, requesting_user_id: Optional[str] = None) -> UserResponse:
        """
        Get user by ID

        Args:
            user_id: User ID to retrieve
            requesting_user_id: ID of user making the request (for authorization)

        Returns:
            User information

        Raises:
            UserNotFoundError: If user not found
            AuthorizationError: If requesting user doesn't have permission
        """
        try:
            Validators.validate_mongodb_id(user_id, "user_id")

            # Get user
            user = await self.users_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                raise UserNotFoundError(f"User not found: {user_id}")

            # Check authorization if requesting user is provided
            if requesting_user_id:
                await self._check_user_access_authorization(
                    requesting_user_id,
                    user.get("company_id")
                )

            return UserResponse(
                id=str(user["_id"]),
                email=user["email"],
                full_name=user["full_name"],
                role=user["role"],
                company_id=user.get("company_id"),
                is_active=user.get("is_active", True),
                created_at=user["created_at"],
                updated_at=user["updated_at"]
            )

        except (UserNotFoundError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error getting user: {str(e)}", exc_info=True)
            raise

    async def update_user(
        self,
        user_id: str,
        data: UserUpdate,
        updating_user_id: Optional[str] = None
    ) -> UserResponse:
        """
        Update user information

        Args:
            user_id: User ID to update
            data: Update data
            updating_user_id: ID of user making the update (for authorization)

        Returns:
            Updated user information

        Raises:
            UserNotFoundError: If user not found
            ValidationError: If validation fails
            AuthorizationError: If updating user doesn't have permission
        """
        try:
            Validators.validate_mongodb_id(user_id, "user_id")

            # Get user
            user = await self.users_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                raise UserNotFoundError(f"User not found: {user_id}")

            # Check authorization
            if updating_user_id:
                await self._check_user_modification_authorization(
                    updating_user_id,
                    user.get("company_id")
                )

            # Build update document
            update_doc = {"updated_at": datetime.utcnow()}

            if data.full_name is not None:
                update_doc["full_name"] = data.full_name

            if data.role is not None:
                if data.role not in ["superadmin", "admin"]:
                    raise ValidationError("Invalid role", {"role": data.role})
                update_doc["role"] = data.role

            if data.company_id is not None:
                Validators.validate_mongodb_id(data.company_id, "company_id")
                company = await self.db.companies.find_one({"_id": ObjectId(data.company_id)})
                if not company:
                    raise ValidationError("Invalid company_id", {"company_id": data.company_id})
                update_doc["company_id"] = data.company_id

            if data.is_active is not None:
                update_doc["is_active"] = data.is_active

            # Update user
            await self.users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_doc}
            )

            logger.info(f"User updated: {user_id}")

            # Return updated user
            return await self.get_user(user_id)

        except (UserNotFoundError, ValidationError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}", exc_info=True)
            raise

    async def delete_user(self, user_id: str, deleting_user_id: Optional[str] = None) -> None:
        """
        Delete user (soft delete - set is_active to False)

        Args:
            user_id: User ID to delete
            deleting_user_id: ID of user performing deletion (for authorization)

        Raises:
            UserNotFoundError: If user not found
            AuthorizationError: If deleting user doesn't have permission
        """
        try:
            Validators.validate_mongodb_id(user_id, "user_id")

            # Get user
            user = await self.users_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                raise UserNotFoundError(f"User not found: {user_id}")

            # Check authorization
            if deleting_user_id:
                await self._check_user_modification_authorization(
                    deleting_user_id,
                    user.get("company_id")
                )

            # Soft delete - set is_active to False
            await self.users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "is_active": False,
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            logger.info(f"User deleted (soft): {user_id}")

        except (UserNotFoundError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}", exc_info=True)
            raise

    async def list_users(
        self,
        page: int = 1,
        page_size: int = 20,
        company_id: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        requesting_user_id: Optional[str] = None
    ) -> UserListResponse:
        """
        List users with pagination and filtering

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            company_id: Filter by company
            role: Filter by role
            is_active: Filter by active status
            requesting_user_id: ID of user making the request (for authorization)

        Returns:
            Paginated user list

        Raises:
            AuthorizationError: If requesting user doesn't have permission
        """
        try:
            # Build filter
            filter_doc: Dict[str, Any] = {}

            # Authorization check
            if requesting_user_id:
                requesting_user = await self.users_collection.find_one({"_id": ObjectId(requesting_user_id)})
                if not requesting_user:
                    raise AuthorizationError("Requesting user not found")

                # Admin users can only see users from their company
                if requesting_user["role"] == "admin":
                    if company_id and company_id != requesting_user.get("company_id"):
                        raise AuthorizationError("Cannot access users from other companies")
                    filter_doc["company_id"] = requesting_user.get("company_id")

            # Apply filters
            if company_id and "company_id" not in filter_doc:
                filter_doc["company_id"] = company_id

            if role:
                filter_doc["role"] = role

            if is_active is not None:
                filter_doc["is_active"] = is_active

            # Get total count
            total = await self.users_collection.count_documents(filter_doc)

            # Calculate pagination
            skip = (page - 1) * page_size
            total_pages = math.ceil(total / page_size) if total > 0 else 1

            # Get users
            cursor = self.users_collection.find(filter_doc).sort("created_at", -1).skip(skip).limit(page_size)
            users = await cursor.to_list(length=page_size)

            # Build response
            user_responses = [
                UserResponse(
                    id=str(user["_id"]),
                    email=user["email"],
                    full_name=user["full_name"],
                    role=user["role"],
                    company_id=user.get("company_id"),
                    is_active=user.get("is_active", True),
                    created_at=user["created_at"],
                    updated_at=user["updated_at"]
                )
                for user in users
            ]

            return UserListResponse(
                users=user_responses,
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages
            )

        except AuthorizationError:
            raise
        except Exception as e:
            logger.error(f"Error listing users: {str(e)}", exc_info=True)
            raise

    async def _check_user_access_authorization(
        self,
        requesting_user_id: str,
        target_company_id: Optional[str]
    ) -> None:
        """
        Check if requesting user can access user information

        Args:
            requesting_user_id: ID of user making the request
            target_company_id: Company ID of target user

        Raises:
            AuthorizationError: If not authorized
        """
        requesting_user = await self.users_collection.find_one({"_id": ObjectId(requesting_user_id)})
        if not requesting_user:
            raise AuthorizationError("Requesting user not found")

        # Superadmin can access all users
        if requesting_user["role"] == "superadmin":
            return

        # Admin can only access users from their company
        if requesting_user["role"] == "admin":
            if requesting_user.get("company_id") != target_company_id:
                raise AuthorizationError("Cannot access users from other companies")
            return

        raise AuthorizationError("Insufficient permissions")

    async def _check_user_modification_authorization(
        self,
        modifying_user_id: str,
        target_company_id: Optional[str]
    ) -> None:
        """
        Check if requesting user can modify user

        Args:
            modifying_user_id: ID of user making the modification
            target_company_id: Company ID of target user

        Raises:
            AuthorizationError: If not authorized
        """
        modifying_user = await self.users_collection.find_one({"_id": ObjectId(modifying_user_id)})
        if not modifying_user:
            raise AuthorizationError("Modifying user not found")

        # Only superadmin can modify users
        if modifying_user["role"] != "superadmin":
            raise AuthorizationError("Only superadmin can modify users")


# Export service
__all__ = ["UserService"]
