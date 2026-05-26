"""
Authentication API Routes
Handles user registration, login, token refresh, and current user info
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional

from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    LoginResponse,
    TokenResponse,
    UserResponse
)
from app.services.auth_service import AuthService
from app.core.dependencies import get_current_user
from app.core.exceptions import (
    ValidationError,
    AuthenticationError,
    UserAlreadyExistsError
)
from app.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new company admin",
    description="Register a new company admin user. Requires a valid company_id. Superadmin accounts must be created directly in the database."
)
async def register(data: RegisterRequest):
    """
    Register a new user

    Args:
        data: Registration data including email, password, name, and optional company_id

    Returns:
        LoginResponse with access token, refresh token, and user info

    Raises:
        HTTPException 400: If validation fails or user already exists
        HTTPException 404: If company_id provided but company not found
        HTTPException 500: If registration fails
    """
    try:
        auth_service = AuthService()
        response = await auth_service.register(data)

        logger.info(f"User registered successfully: {data.email}")
        return response

    except ValidationError as e:
        logger.warning(f"Registration validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except UserAlreadyExistsError as e:
        logger.warning(f"User already exists: {data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Registration failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login user",
    description="Authenticate user with email and password"
)
async def login(data: LoginRequest):
    """
    Login user

    Args:
        data: Login credentials (email and password)

    Returns:
        LoginResponse with access token, refresh token, and user info

    Raises:
        HTTPException 401: If credentials are invalid
        HTTPException 500: If login fails
    """
    try:
        auth_service = AuthService()
        response = await auth_service.login(data)

        logger.info(f"User logged in successfully: {data.email}")
        return response

    except AuthenticationError as e:
        logger.warning(f"Login failed for {data.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    except Exception as e:
        logger.error(f"Login failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Get a new access token using a valid refresh token"
)
async def refresh_token(refresh_token: str):
    """
    Refresh access token

    Args:
        refresh_token: Valid refresh token

    Returns:
        TokenResponse with new access token and refresh token

    Raises:
        HTTPException 401: If refresh token is invalid
        HTTPException 500: If token refresh fails
    """
    try:
        auth_service = AuthService()
        response = await auth_service.refresh_token(refresh_token)

        logger.debug("Token refreshed successfully")
        return response

    except AuthenticationError as e:
        logger.warning(f"Token refresh failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    except Exception as e:
        logger.error(f"Token refresh failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed. Please try again."
        )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get information about the currently authenticated user"
)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
):
    """
    Get current user information

    Args:
        current_user: Current authenticated user (injected by dependency)

    Returns:
        UserResponse with user information

    Raises:
        HTTPException 401: If not authenticated
    """
    try:
        # current_user is already validated and contains user info
        # The get_current_user dependency handles authentication

        logger.debug(f"User info retrieved: {current_user.get('id')}")

        return UserResponse(
            id=current_user["id"],
            email=current_user["email"],
            name=current_user["name"],
            role=current_user["role"],
            company_id=current_user.get("company_id"),
            is_active=current_user["is_active"],
            created_at=current_user["created_at"],
            updated_at=current_user["updated_at"]
        )

    except Exception as e:
        logger.error(f"Failed to get user info: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user information"
        )


# Export router
__all__ = ["router"]
