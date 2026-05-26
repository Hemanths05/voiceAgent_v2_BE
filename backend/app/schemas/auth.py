"""
Authentication Schemas
Request/response models for authentication endpoints
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime


class RegisterRequest(BaseModel):
    """Request schema for user registration (company admin only)"""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password (min 8 chars)")
    full_name: str = Field(..., min_length=2, max_length=100, description="User full name")
    company_number: int = Field(..., description="Company Number (numeric ID - contact superadmin for your company number)")

    @validator('password')
    def validate_password_strength(cls, v):
        """Validate password has sufficient complexity"""
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "email": "admin@example.com",
                "password": "SecurePass123",
                "full_name": "John Doe",
                "company_number": 1
            }
        }


class LoginRequest(BaseModel):
    """Request schema for user login"""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "admin@example.com",
                "password": "SecurePass123"
            }
        }


class RefreshTokenRequest(BaseModel):
    """Request schema for refreshing access token"""

    refresh_token: str = Field(..., description="Refresh token")

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class TokenResponse(BaseModel):
    """Response schema for authentication tokens"""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }


class UserResponse(BaseModel):
    """Response schema for user information"""

    id: int = Field(..., description="User ID (sequential)")
    email: str = Field(..., description="User email")
    full_name: str = Field(..., description="User full name")
    role: str = Field(..., description="User role (superadmin, admin)")
    company_id: Optional[int] = Field(None, description="Company ID (for admin users)")
    is_active: bool = Field(default=True, description="Whether user is active")
    created_at: datetime = Field(..., description="User creation timestamp")
    updated_at: datetime = Field(..., description="User last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 2,
                "email": "admin@example.com",
                "full_name": "John Doe",
                "role": "admin",
                "company_id": 1,
                "is_active": True,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }


class LoginResponse(BaseModel):
    """Response schema for successful login"""

    user: UserResponse = Field(..., description="User information")
    tokens: TokenResponse = Field(..., description="Authentication tokens")

    class Config:
        json_schema_extra = {
            "example": {
                "user": {
                    "id": "507f1f77bcf86cd799439011",
                    "email": "admin@example.com",
                    "full_name": "John Doe",
                    "role": "admin",
                    "company_id": "507f1f77bcf86cd799439012",
                    "is_active": True,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z"
                },
                "tokens": {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "expires_in": 3600
                }
            }
        }


class ChangePasswordRequest(BaseModel):
    """Request schema for changing password"""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password (min 8 chars)")

    @validator('new_password')
    def validate_password_strength(cls, v):
        """Validate password has sufficient complexity"""
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "current_password": "OldPass123",
                "new_password": "NewSecurePass456"
            }
        }


# Export schemas
__all__ = [
    "RegisterRequest",
    "LoginRequest",
    "RefreshTokenRequest",
    "TokenResponse",
    "UserResponse",
    "LoginResponse",
    "ChangePasswordRequest"
]
