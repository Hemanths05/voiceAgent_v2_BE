"""
Company Database Model
Pydantic model for companies collection
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from app.database.models.user import PyObjectId


class CompanyBase(BaseModel):
    """Base company model with common fields"""

    name: str = Field(..., min_length=2, max_length=200)
    phone_number: str = Field(..., pattern=r"^\+[1-9]\d{1,14}$")  # E.164 format
    status: str = Field(default="active", pattern="^(active|inactive|suspended)$")

    class Config:
        json_encoders = {PyObjectId: str}
        populate_by_name = True


class CompanyCreate(CompanyBase):
    """Company creation model"""

    pass


class CompanyInDB(CompanyBase):
    """Company model as stored in database"""

    id: int = Field(..., alias="_id", description="Sequential company ID")
    ai_credentials: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {PyObjectId: str}
        populate_by_name = True
        arbitrary_types_allowed = True


class CompanyResponse(BaseModel):
    """Company model for API responses"""

    id: str
    name: str
    phone_number: str
    status: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db(cls, company: CompanyInDB) -> "CompanyResponse":
        """
        Create CompanyResponse from database model

        Args:
            company: Company from database

        Returns:
            CompanyResponse instance
        """
        return cls(
            id=company.id,
            name=company.name,
            phone_number=company.phone_number,
            status=company.status,
            created_at=company.created_at,
            updated_at=company.updated_at,
        )


class CompanyUpdate(BaseModel):
    """Company update model"""

    name: Optional[str] = Field(None, min_length=2, max_length=200)
    phone_number: Optional[str] = Field(None, pattern=r"^\+[1-9]\d{1,14}$")
    status: Optional[str] = Field(None, pattern="^(active|inactive|suspended)$")
    ai_credentials: Optional[Dict[str, Any]] = None


class CompanyWithStats(CompanyResponse):
    """Company model with statistics"""

    total_calls: int = 0
    total_knowledge_entries: int = 0
    avg_call_duration_seconds: float = 0.0
    last_call_at: Optional[datetime] = None


# Export models
__all__ = [
    "CompanyBase",
    "CompanyCreate",
    "CompanyInDB",
    "CompanyResponse",
    "CompanyUpdate",
    "CompanyWithStats",
]
