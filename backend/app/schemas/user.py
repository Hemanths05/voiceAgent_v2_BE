"""
User Schemas
Request/response models for user management
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    """Schema for creating a new user"""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    full_name: str = Field(..., min_length=2, max_length=100, description="User full name")
    role: str = Field(..., description="User role (superadmin, admin)")
    company_id: Optional[int] = Field(None, description="Company ID (required for admin role)")

    @validator('role')
    def validate_role(cls, v):
        """Validate role is valid"""
        allowed_roles = ['superadmin', 'admin']
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of: {', '.join(allowed_roles)}")
        return v

    @validator('company_id')
    def validate_company_id_for_admin(cls, v, values):
        """Validate company_id is provided for admin role"""
        if values.get('role') == 'admin' and not v:
            raise ValueError('company_id is required for admin role')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "email": "newadmin@example.com",
                "password": "SecurePass123",
                "full_name": "Jane Smith",
                "role": "admin",
                "company_id": "507f1f77bcf86cd799439012"
            }
        }


class UserUpdate(BaseModel):
    """Schema for updating user information"""

    full_name: Optional[str] = Field(None, min_length=2, max_length=100, description="User full name")
    role: Optional[str] = Field(None, description="User role")
    company_id: Optional[int] = Field(None, description="Company ID")
    is_active: Optional[bool] = Field(None, description="Whether user is active")

    @validator('role')
    def validate_role(cls, v):
        """Validate role is valid"""
        if v is not None:
            allowed_roles = ['superadmin', 'admin']
            if v not in allowed_roles:
                raise ValueError(f"Role must be one of: {', '.join(allowed_roles)}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "Jane Doe",
                "is_active": True
            }
        }


class UserResponse(BaseModel):
    """Response schema for user information"""

    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: str = Field(..., description="User full name")
    role: str = Field(..., description="User role")
    company_id: Optional[int] = Field(None, description="Company ID")
    is_active: bool = Field(..., description="Whether user is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "email": "admin@example.com",
                "full_name": "John Doe",
                "role": "admin",
                "company_id": "507f1f77bcf86cd799439012",
                "is_active": True,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }


class UserListResponse(BaseModel):
    """Response schema for paginated user list"""

    users: list[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")

    class Config:
        json_schema_extra = {
            "example": {
                "users": [
                    {
                        "id": "507f1f77bcf86cd799439011",
                        "email": "admin@example.com",
                        "full_name": "John Doe",
                        "role": "admin",
                        "company_id": "507f1f77bcf86cd799439012",
                        "is_active": True,
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z"
                    }
                ],
                "total": 50,
                "page": 1,
                "page_size": 20,
                "total_pages": 3
            }
        }


# Export schemas
__all__ = [
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserListResponse"
]
