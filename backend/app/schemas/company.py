"""
Company Schemas
Request/response models for company management
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime


class CompanyCreate(BaseModel):
    """Schema for creating a new company"""

    name: str = Field(..., min_length=2, max_length=200, description="Company name")
    phone_number: str = Field(..., description="Twilio phone number (E.164 format: +1XXXXXXXXXX)")
    description: Optional[str] = Field(None, max_length=1000, description="Company description")
    industry: Optional[str] = Field(None, max_length=100, description="Industry/vertical")

    # Configuration fields
    status: Optional[str] = Field("active", description="Company status")
    subscription_tier: Optional[str] = Field("free", description="Subscription tier")
    ai_provider: Optional[str] = Field(None, description="AI/LLM provider")
    stt_provider: Optional[str] = Field(None, description="Speech-to-text provider")
    tts_provider: Optional[str] = Field(None, description="Text-to-speech provider")
    max_users: Optional[int] = Field(None, description="Maximum number of users")
    max_monthly_calls: Optional[int] = Field(None, description="Maximum monthly calls")

    @validator('phone_number')
    def validate_phone_format(cls, v):
        """Validate phone is in E.164 format (international)"""
        import re
        # E.164 format: + followed by country code and number (up to 15 digits total)
        if not re.match(r'^\+[1-9]\d{1,14}$', v):
            raise ValueError('Phone number must be in E.164 format: +[country code][number] (e.g., +919876543210)')
        return v

    @validator('status')
    def validate_status(cls, v):
        """Validate status is valid"""
        if v is not None:
            allowed_statuses = ['active', 'inactive', 'suspended']
            if v not in allowed_statuses:
                raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        return v

    @validator('subscription_tier')
    def validate_subscription_tier(cls, v):
        """Validate subscription tier is valid"""
        if v is not None:
            allowed_tiers = ['free', 'basic', 'pro', 'enterprise']
            if v not in allowed_tiers:
                raise ValueError(f"Subscription tier must be one of: {', '.join(allowed_tiers)}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Acme Corporation",
                "phone_number": "+15551234567",
                "description": "Leading provider of roadrunner traps",
                "industry": "Manufacturing",
                "status": "active",
                "subscription_tier": "pro",
                "ai_provider": "openai",
                "stt_provider": "deepgram",
                "tts_provider": "elevenlabs",
                "max_users": 10,
                "max_monthly_calls": 1000
            }
        }


class CompanyUpdate(BaseModel):
    """Schema for updating company information"""

    name: Optional[str] = Field(None, min_length=2, max_length=200, description="Company name")
    phone_number: Optional[str] = Field(None, description="Twilio phone number")
    description: Optional[str] = Field(None, max_length=1000, description="Company description")
    industry: Optional[str] = Field(None, max_length=100, description="Industry/vertical")

    # Configuration fields
    status: Optional[str] = Field(None, description="Company status")
    subscription_tier: Optional[str] = Field(None, description="Subscription tier")
    ai_provider: Optional[str] = Field(None, description="AI/LLM provider")
    stt_provider: Optional[str] = Field(None, description="Speech-to-text provider")
    tts_provider: Optional[str] = Field(None, description="Text-to-speech provider")
    max_users: Optional[int] = Field(None, description="Maximum number of users")
    max_monthly_calls: Optional[int] = Field(None, description="Maximum monthly calls")

    @validator('phone_number')
    def validate_phone_format(cls, v):
        """Validate phone is in E.164 format (international)"""
        if v is not None:
            import re
            if not re.match(r'^\+[1-9]\d{1,14}$', v):
                raise ValueError('Phone number must be in E.164 format: +[country code][number] (e.g., +919876543210)')
        return v

    @validator('status')
    def validate_status(cls, v):
        """Validate status is valid"""
        if v is not None:
            allowed_statuses = ['active', 'inactive', 'suspended']
            if v not in allowed_statuses:
                raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        return v

    @validator('subscription_tier')
    def validate_subscription_tier(cls, v):
        """Validate subscription tier is valid"""
        if v is not None:
            allowed_tiers = ['free', 'basic', 'pro', 'enterprise']
            if v not in allowed_tiers:
                raise ValueError(f"Subscription tier must be one of: {', '.join(allowed_tiers)}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Acme Corporation Inc.",
                "description": "Updated description",
                "subscription_tier": "enterprise"
            }
        }


class CompanyStatusUpdate(BaseModel):
    """Schema for updating company status"""

    status: str = Field(..., description="Company status (active, inactive, suspended)")

    @validator('status')
    def validate_status(cls, v):
        """Validate status is valid"""
        allowed_statuses = ['active', 'inactive', 'suspended']
        if v not in allowed_statuses:
            raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "status": "active"
            }
        }


class CompanyResponse(BaseModel):
    """Response schema for company information"""

    id: int = Field(..., description="Company ID (sequential)")
    name: str = Field(..., description="Company name")
    phone_number: str = Field(..., description="Twilio phone number")
    description: Optional[str] = Field(None, description="Company description")
    industry: Optional[str] = Field(None, description="Industry/vertical")
    status: str = Field(..., description="Company status")

    # Configuration fields
    subscription_tier: Optional[str] = Field("free", description="Subscription tier")
    ai_provider: Optional[str] = Field(None, description="AI/LLM provider")
    stt_provider: Optional[str] = Field(None, description="Speech-to-text provider")
    tts_provider: Optional[str] = Field(None, description="Text-to-speech provider")
    max_users: Optional[int] = Field(None, description="Maximum number of users")
    max_monthly_calls: Optional[int] = Field(None, description="Maximum monthly calls")
    current_call_count: Optional[int] = Field(0, description="Current call count for the month")

    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Stats (populated by service layer)
    total_calls: Optional[int] = Field(None, description="Total number of calls")
    total_admins: Optional[int] = Field(None, description="Total number of admin users")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Acme Corporation",
                "phone_number": "+15551234567",
                "description": "Leading provider of roadrunner traps",
                "industry": "Manufacturing",
                "status": "active",
                "subscription_tier": "pro",
                "ai_provider": "openai",
                "stt_provider": "deepgram",
                "tts_provider": "elevenlabs",
                "max_users": 10,
                "max_monthly_calls": 1000,
                "current_call_count": 245,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "total_calls": 1250,
                "total_admins": 3
            }
        }


class CompanyListResponse(BaseModel):
    """Response schema for paginated company list"""

    companies: list[CompanyResponse] = Field(..., description="List of companies")
    total: int = Field(..., description="Total number of companies")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")

    class Config:
        json_schema_extra = {
            "example": {
                "companies": [
                    {
                        "id": "507f1f77bcf86cd799439012",
                        "name": "Acme Corporation",
                        "phone_number": "+15551234567",
                        "description": "Leading provider",
                        "industry": "Manufacturing",
                        "status": "active",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z",
                        "total_calls": 1250,
                        "total_admins": 3
                    }
                ],
                "total": 25,
                "page": 1,
                "page_size": 20,
                "total_pages": 2
            }
        }


class CompanyStatsResponse(BaseModel):
    """Response schema for company statistics"""

    company_id: int = Field(..., description="Company ID (sequential)")
    total_calls: int = Field(..., description="Total number of calls")
    successful_calls: int = Field(..., description="Number of successful calls")
    failed_calls: int = Field(..., description="Number of failed calls")
    avg_call_duration: float = Field(..., description="Average call duration in seconds")
    total_knowledge_entries: int = Field(..., description="Total knowledge base entries")
    total_admins: int = Field(..., description="Total admin users")
    last_call_at: Optional[datetime] = Field(None, description="Timestamp of last call")

    class Config:
        json_schema_extra = {
            "example": {
                "company_id": "507f1f77bcf86cd799439012",
                "total_calls": 1250,
                "successful_calls": 1180,
                "failed_calls": 70,
                "avg_call_duration": 185.5,
                "total_knowledge_entries": 45,
                "total_admins": 3,
                "last_call_at": "2024-01-20T15:45:00Z"
            }
        }


class DashboardMetricsResponse(BaseModel):
    """Response schema for admin dashboard metrics"""

    total_calls: int = Field(0, description="Total number of calls")
    active_calls: int = Field(0, description="Number of currently active/in-progress calls")
    completed_calls: int = Field(0, description="Number of completed calls")
    failed_calls: int = Field(0, description="Number of failed calls")
    total_duration_minutes: float = Field(0, description="Total call duration in minutes")
    avg_call_duration_seconds: float = Field(0, description="Average call duration in seconds")
    knowledge_docs_count: int = Field(0, description="Number of knowledge base documents")
    knowledge_chunks_count: int = Field(0, description="Total number of indexed knowledge chunks")


# Export schemas
__all__ = [
    "CompanyCreate",
    "CompanyUpdate",
    "CompanyStatusUpdate",
    "CompanyResponse",
    "CompanyListResponse",
    "CompanyStatsResponse",
    "DashboardMetricsResponse"
]
