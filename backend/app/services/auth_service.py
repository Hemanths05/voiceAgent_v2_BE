"""
Authentication Service
Handles user authentication, registration, and token management
"""
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token
from app.core.exceptions import (
    AuthenticationError,
    UserAlreadyExistsError,
    UserNotFoundError,
    InvalidTokenError,
    ValidationError
)
from app.core.logging_config import get_logger
from app.database.mongodb import get_database
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse, LoginResponse
from app.utils.validators import Validators
from app.utils.counter import Counter

logger = get_logger(__name__)


class AuthService:
    """
    Service for handling authentication operations
    """

    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        """
        Initialize auth service

        Args:
            db: MongoDB database instance (if None, will use get_database())
        """
        self.db = db or get_database()
        self.users_collection = self.db.users
        self.counter = Counter(self.db)

    async def register(self, data: RegisterRequest) -> LoginResponse:
        """
        Register a new user

        Args:
            data: Registration data

        Returns:
            Login response with user info and tokens

        Raises:
            UserAlreadyExistsError: If email already exists
            ValidationError: If validation fails
        """
        try:
            # Validate email format
            email = Validators.validate_email(data.email)

            # Check if user already exists
            existing_user = await self.users_collection.find_one({"email": email})
            if existing_user:
                raise UserAlreadyExistsError(f"User with email {email} already exists")

            # Validate company_number (required for registration)
            # Note: Superadmin accounts should be created directly in the database
            if not data.company_number:
                raise ValidationError(
                    "company_number is required for registration. Contact superadmin to get your company number.",
                    {"company_number": "required"}
                )

            # Look up company by _id (company_number is the sequential integer ID)
            company = await self.db.companies.find_one({"_id": data.company_number})
            if not company:
                raise ValidationError(
                    f"Invalid company number: {data.company_number}. Please contact superadmin for a valid company number.",
                    {"company_number": data.company_number}
                )

            # Get the actual company ID (integer)
            company_id = company["_id"]

            # Hash password
            hashed_password = get_password_hash(data.password)

            # Registration always creates admin users (company admins)
            # Superadmin accounts must be created manually in the database
            role = "admin"

            # Get next user ID from counter
            user_id = await self.counter.get_next_sequence("user")

            # Create user document with sequential _id
            user_doc = {
                "_id": user_id,
                "email": email,
                "hashed_password": hashed_password,
                "full_name": data.full_name,
                "role": role,
                "company_id": company_id,
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            # Insert user
            await self.users_collection.insert_one(user_doc)

            logger.info(f"User registered successfully: {email} (role={role})")

            # Generate tokens (convert to string for JWT)
            tokens = self._generate_tokens(str(user_id), email, role, company_id)

            # Build response
            user_response = UserResponse(
                id=user_id,
                email=email,
                full_name=data.full_name,
                role=role,
                company_id=company_id,
                is_active=True,
                created_at=user_doc["created_at"],
                updated_at=user_doc["updated_at"]
            )

            return LoginResponse(user=user_response, tokens=tokens)

        except (UserAlreadyExistsError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error during registration: {str(e)}", exc_info=True)
            raise

    async def login(self, data: LoginRequest) -> LoginResponse:
        """
        Login user and generate tokens

        Args:
            data: Login credentials

        Returns:
            Login response with user info and tokens

        Raises:
            AuthenticationError: If credentials are invalid
        """
        try:
            # Validate email format
            email = Validators.validate_email(data.email)

            # Find user
            user = await self.users_collection.find_one({"email": email})
            if not user:
                raise AuthenticationError("Invalid email or password")

            # Verify password
            if not verify_password(data.password, user["hashed_password"]):
                raise AuthenticationError("Invalid email or password")

            # Check if user is active
            if not user.get("is_active", True):
                raise AuthenticationError("User account is inactive")

            user_id = user["_id"]

            logger.info(f"User logged in successfully: {email}")

            # Generate tokens (convert to string for JWT)
            tokens = self._generate_tokens(str(user_id), email, user["role"], user.get("company_id"))

            # Build response
            user_response = UserResponse(
                id=user_id,
                email=user["email"],
                full_name=user["full_name"],
                role=user["role"],
                company_id=user.get("company_id"),
                is_active=user.get("is_active", True),
                created_at=user["created_at"],
                updated_at=user["updated_at"]
            )

            return LoginResponse(user=user_response, tokens=tokens)

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Error during login: {str(e)}", exc_info=True)
            raise AuthenticationError("Login failed")

    def _generate_tokens(self, user_id: str, email: str, role: str, company_id: Optional[int] = None) -> TokenResponse:
        """
        Generate access and refresh tokens

        Args:
            user_id: User ID
            email: User email
            role: User role
            company_id: Company ID (optional, for admin users)

        Returns:
            Token response
        """
        # Create token payload
        token_data = {
            "sub": user_id,
            "email": email,
            "role": role
        }

        # Include company_id for admin users
        if company_id is not None:
            token_data["company_id"] = company_id

        # Generate tokens
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        from app.config import settings

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60
        )

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """
        Generate new access token from refresh token

        Args:
            refresh_token: Refresh token

        Returns:
            New token response

        Raises:
            InvalidTokenError: If refresh token is invalid
        """
        from app.core.security import decode_token

        try:
            # Decode refresh token
            payload = decode_token(refresh_token)

            # Verify token type
            if payload.get("type") != "refresh":
                raise InvalidTokenError("Invalid token type")

            user_id = payload.get("sub")
            email = payload.get("email")
            role = payload.get("role")
            company_id = payload.get("company_id")

            if not user_id or not email or not role:
                raise InvalidTokenError("Invalid token payload")

            # Verify user still exists and is active
            user = await self.users_collection.find_one({"_id": int(user_id)})
            if not user or not user.get("is_active", True):
                raise InvalidTokenError("User is no longer active")

            logger.info(f"Refreshed access token for user: {email}")

            # Generate new tokens with company_id from user document (in case it changed)
            return self._generate_tokens(user_id, email, role, user.get("company_id"))

        except InvalidTokenError:
            raise
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}", exc_info=True)
            raise InvalidTokenError("Failed to refresh token")

    async def get_current_user(self, user_id: str) -> UserResponse:
        """
        Get current user information

        Args:
            user_id: User ID from token

        Returns:
            User information

        Raises:
            UserNotFoundError: If user not found
        """
        try:
            user = await self.users_collection.find_one({"_id": int(user_id)})
            if not user:
                raise UserNotFoundError(f"User not found: {user_id}")

            return UserResponse(
                id=user["_id"],
                email=user["email"],
                full_name=user["full_name"],
                role=user["role"],
                company_id=user.get("company_id"),
                is_active=user.get("is_active", True),
                created_at=user["created_at"],
                updated_at=user["updated_at"]
            )

        except UserNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting current user: {str(e)}", exc_info=True)
            raise

    async def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str
    ) -> None:
        """
        Change user password

        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password

        Raises:
            UserNotFoundError: If user not found
            AuthenticationError: If current password is incorrect
        """
        try:
            # Find user
            user = await self.users_collection.find_one({"_id": int(user_id)})
            if not user:
                raise UserNotFoundError(f"User not found: {user_id}")

            # Verify current password
            if not verify_password(current_password, user["hashed_password"]):
                raise AuthenticationError("Current password is incorrect")

            # Validate new password
            Validators.validate_password(new_password)

            # Hash new password
            new_hashed_password = get_password_hash(new_password)

            # Update password
            await self.users_collection.update_one(
                {"_id": int(user_id)},
                {
                    "$set": {
                        "hashed_password": new_hashed_password,
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            logger.info(f"Password changed for user: {user['email']}")

        except (UserNotFoundError, AuthenticationError):
            raise
        except Exception as e:
            logger.error(f"Error changing password: {str(e)}", exc_info=True)
            raise


# Export service
__all__ = ["AuthService"]
