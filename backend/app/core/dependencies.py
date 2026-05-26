"""
FastAPI Dependencies
Provides dependency injection for authentication, authorization, and database access
"""
from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase
from qdrant_client import AsyncQdrantClient

from app.core.security import verify_access_token, extract_user_from_token
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    InvalidTokenError,
)
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# HTTP Bearer security scheme
security = HTTPBearer()


# ==================== Database Dependencies ====================

async def get_mongodb() -> AsyncIOMotorDatabase:
    """
    Get MongoDB database instance

    Returns:
        AsyncIOMotorDatabase instance

    Note:
        This will be properly implemented after database module is created
    """
    from app.database.mongodb import get_database
    return get_database()


async def get_qdrant() -> AsyncQdrantClient:
    """
    Get Qdrant client instance

    Returns:
        AsyncQdrantClient instance

    Note:
        This will be properly implemented after database module is created
    """
    from app.database.qdrant import get_qdrant_client
    return get_qdrant_client()


# ==================== Authentication Dependencies ====================

async def get_token_from_header(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Extract JWT token from Authorization header

    Args:
        credentials: HTTP authorization credentials

    Returns:
        JWT token string

    Raises:
        AuthenticationError: If token is missing or invalid format
    """
    if not credentials:
        raise AuthenticationError("Missing authorization header")

    token = credentials.credentials

    if not token:
        raise AuthenticationError("Missing token")

    return token


async def get_current_user(
    token: str = Depends(get_token_from_header)
) -> dict:
    """
    Get current user from JWT token

    Args:
        token: JWT access token

    Returns:
        Dictionary with user information (user_id, email, role, company_id)

    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        user_info = extract_user_from_token(token)

        if not user_info.get("user_id"):
            raise AuthenticationError("Invalid token payload")

        return user_info

    except InvalidTokenError as e:
        raise AuthenticationError(str(e))
    except Exception as e:
        logger.error(f"Error extracting user from token: {str(e)}", exc_info=True)
        raise AuthenticationError("Failed to authenticate user")


# ==================== Authorization Dependencies ====================

def require_role(*allowed_roles: str):
    """
    Dependency factory that creates a role-based access control dependency

    Args:
        *allowed_roles: One or more allowed roles (e.g., "superadmin", "admin")

    Returns:
        Dependency function that checks user role

    Example:
        @router.get("/admin/dashboard", dependencies=[Depends(require_role("admin", "superadmin"))])
        async def get_dashboard():
            ...
    """
    async def check_role(current_user: dict = Depends(get_current_user)) -> dict:
        """
        Check if current user has required role

        Args:
            current_user: Current user information

        Returns:
            Current user if authorized

        Raises:
            AuthorizationError: If user doesn't have required role
        """
        user_role = current_user.get("role")

        if user_role not in allowed_roles:
            raise AuthorizationError(
                f"Insufficient permissions. Required roles: {', '.join(allowed_roles)}"
            )

        return current_user

    return check_role


async def require_superadmin(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Dependency that requires superadmin role

    Args:
        current_user: Current user information

    Returns:
        Current user if superadmin

    Raises:
        AuthorizationError: If user is not superadmin
    """
    if current_user.get("role") != "superadmin":
        raise AuthorizationError("Superadmin access required")

    return current_user


async def require_admin(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Dependency that requires admin role

    Args:
        current_user: Current user information

    Returns:
        Current user if admin

    Raises:
        AuthorizationError: If user is not admin
    """
    if current_user.get("role") != "admin":
        raise AuthorizationError("Admin access required")

    return current_user


async def get_company_id(
    current_user: dict = Depends(get_current_user)
) -> str:
    """
    Get company ID from current user

    Args:
        current_user: Current user information

    Returns:
        Company ID

    Raises:
        AuthorizationError: If user is not associated with a company
    """
    company_id = current_user.get("company_id")

    if not company_id:
        raise AuthorizationError("User not associated with a company")

    return company_id


# ==================== Multi-Tenancy Dependencies ====================

async def enforce_company_isolation(
    resource_company_id: str,
    current_user: dict = Depends(get_current_user)
) -> bool:
    """
    Enforce company-level data isolation

    Args:
        resource_company_id: Company ID of the resource being accessed
        current_user: Current user information

    Returns:
        True if access is allowed

    Raises:
        AuthorizationError: If user tries to access another company's resource
    """
    # Superadmin can access all resources
    if current_user.get("role") == "superadmin":
        return True

    # Admin can only access their company's resources
    user_company_id = current_user.get("company_id")

    if user_company_id != resource_company_id:
        raise AuthorizationError("Access denied to this company's resources")

    return True


# ==================== Optional Authentication ====================

async def get_current_user_optional(
    authorization: Optional[str] = Header(None)
) -> Optional[dict]:
    """
    Get current user from token, but don't require authentication

    Args:
        authorization: Authorization header

    Returns:
        User information if authenticated, None otherwise
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    try:
        token = authorization.replace("Bearer ", "")
        user_info = extract_user_from_token(token)
        return user_info
    except Exception:
        return None


# ==================== Request Context Dependencies ====================

async def get_request_id(request_id: Optional[str] = Header(None, alias="X-Request-ID")) -> Optional[str]:
    """
    Get request ID from header

    Args:
        request_id: Request ID from header

    Returns:
        Request ID or None
    """
    return request_id


# Export dependencies
__all__ = [
    "get_mongodb",
    "get_qdrant",
    "get_token_from_header",
    "get_current_user",
    "get_current_user_optional",
    "require_role",
    "require_superadmin",
    "require_admin",
    "get_company_id",
    "enforce_company_isolation",
    "get_request_id",
]
