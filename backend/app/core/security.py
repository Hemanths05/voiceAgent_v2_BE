"""
Security Module
Handles JWT token generation/validation and password hashing
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings
from app.core.exceptions import InvalidTokenError


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ==================== Password Hashing ====================

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


# Alias for backward compatibility
get_password_hash = hash_password


# ==================== JWT Token Generation ====================

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token

    Args:
        data: Data to encode in token (typically user_id, email, role)
        expires_delta: Optional expiration time delta

    Returns:
        JWT token string
    """
    to_encode = data.copy()

    # Set expiration
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })

    # Encode token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.jwt_algorithm
    )

    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token

    Args:
        data: Data to encode in token
        expires_delta: Optional expiration time delta

    Returns:
        JWT refresh token string
    """
    to_encode = data.copy()

    # Set expiration (refresh tokens have longer expiration)
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            days=settings.refresh_token_expire_days
        )

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })

    # Encode token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.jwt_algorithm
    )

    return encoded_jwt


# ==================== JWT Token Validation ====================

def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        InvalidTokenError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        raise InvalidTokenError(f"Token validation failed: {str(e)}")


def verify_access_token(token: str) -> Dict[str, Any]:
    """
    Verify an access token

    Args:
        token: JWT access token

    Returns:
        Decoded token payload

    Raises:
        InvalidTokenError: If token is invalid, expired, or not an access token
    """
    payload = decode_token(token)

    # Verify token type
    if payload.get("type") != "access":
        raise InvalidTokenError("Invalid token type")

    return payload


def verify_refresh_token(token: str) -> Dict[str, Any]:
    """
    Verify a refresh token

    Args:
        token: JWT refresh token

    Returns:
        Decoded token payload

    Raises:
        InvalidTokenError: If token is invalid, expired, or not a refresh token
    """
    payload = decode_token(token)

    # Verify token type
    if payload.get("type") != "refresh":
        raise InvalidTokenError("Invalid token type")

    return payload


def get_token_expiry(token: str) -> Optional[datetime]:
    """
    Get expiration time of a token

    Args:
        token: JWT token

    Returns:
        Expiration datetime or None if invalid
    """
    try:
        payload = decode_token(token)
        exp_timestamp = payload.get("exp")
        if exp_timestamp:
            return datetime.fromtimestamp(exp_timestamp)
    except InvalidTokenError:
        pass

    return None


def is_token_expired(token: str) -> bool:
    """
    Check if a token is expired

    Args:
        token: JWT token

    Returns:
        True if expired, False otherwise
    """
    expiry = get_token_expiry(token)
    if expiry:
        return datetime.utcnow() > expiry
    return True


# ==================== Token Payload Helpers ====================

def create_token_payload(
    user_id: str,
    email: str,
    role: str,
    company_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create standard token payload

    Args:
        user_id: User ID
        email: User email
        role: User role (superadmin, admin)
        company_id: Company ID (None for superadmin)

    Returns:
        Token payload dictionary
    """
    payload = {
        "sub": user_id,  # Subject (user_id)
        "email": email,
        "role": role,
    }

    if company_id:
        payload["company_id"] = company_id

    return payload


def extract_user_from_token(token: str) -> Dict[str, Any]:
    """
    Extract user information from token

    Args:
        token: JWT access token

    Returns:
        Dictionary with user_id, email, role, company_id

    Raises:
        InvalidTokenError: If token is invalid
    """
    payload = verify_access_token(token)

    user_info = {
        "user_id": payload.get("sub"),
        "email": payload.get("email"),
        "role": payload.get("role"),
        "company_id": payload.get("company_id"),
    }

    return user_info


# Export functions
__all__ = [
    "hash_password",
    "get_password_hash",  # Alias for hash_password
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "verify_access_token",
    "verify_refresh_token",
    "get_token_expiry",
    "is_token_expired",
    "create_token_payload",
    "extract_user_from_token",
]
