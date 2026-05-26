"""
User Database Model
Pydantic model for users collection
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom type for MongoDB ObjectId"""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, schema):
        schema.update(type="string")
        return schema


class UserBase(BaseModel):
    """Base user model with common fields"""

    email: EmailStr
    role: str = Field(..., pattern="^(superadmin|admin)$")
    company_id: Optional[str] = None

    class Config:
        json_encoders = {ObjectId: str}
        populate_by_name = True


class UserCreate(UserBase):
    """User creation model"""

    password: str = Field(..., min_length=8)


class UserInDB(UserBase):
    """User model as stored in database"""

    id: int = Field(..., alias="_id", description="Sequential user ID")
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {ObjectId: str}
        populate_by_name = True
        arbitrary_types_allowed = True


class UserResponse(BaseModel):
    """User model for API responses (without password_hash)"""

    id: int
    email: EmailStr
    role: str
    company_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db(cls, user: UserInDB) -> "UserResponse":
        """
        Create UserResponse from database model

        Args:
            user: User from database

        Returns:
            UserResponse instance
        """
        return cls(
            id=user.id,
            email=user.email,
            role=user.role,
            company_id=user.company_id,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


class UserUpdate(BaseModel):
    """User update model"""

    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    role: Optional[str] = Field(None, pattern="^(superadmin|admin)$")
    company_id: Optional[str] = None


# Export models
__all__ = [
    "PyObjectId",
    "UserBase",
    "UserCreate",
    "UserInDB",
    "UserResponse",
    "UserUpdate",
]
