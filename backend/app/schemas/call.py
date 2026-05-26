"""
Call Schemas
Request/response models for call management
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class CallTranscriptMessage(BaseModel):
    """Single message in call transcript"""

    role: str = Field(..., description="Speaker role (user, assistant)")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(..., description="Message timestamp")

    @validator('role')
    def validate_role(cls, v):
        """Validate role"""
        if v not in ['user', 'assistant']:
            raise ValueError("Role must be 'user' or 'assistant'")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "role": "user",
                "content": "Hello, I need help with my account",
                "timestamp": "2024-01-15T10:30:15Z"
            }
        }


class CallCreate(BaseModel):
    """Schema for creating a new call record"""

    call_sid: str = Field(..., description="Twilio Call SID")
    company_id: int = Field(..., description="Company ID")
    from_number: str = Field(..., description="Caller phone number")
    to_number: str = Field(..., description="Twilio phone number called")
    direction: str = Field(default="inbound", description="Call direction")

    @validator('direction')
    def validate_direction(cls, v):
        """Validate direction"""
        if v not in ['inbound', 'outbound']:
            raise ValueError("Direction must be 'inbound' or 'outbound'")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "call_sid": "CA1234567890abcdef1234567890abcd",
                "company_id": "507f1f77bcf86cd799439012",
                "from_number": "+15559876543",
                "to_number": "+15551234567",
                "direction": "inbound"
            }
        }


class CallUpdate(BaseModel):
    """Schema for updating call information"""

    status: Optional[str] = Field(None, description="Call status")
    duration: Optional[float] = Field(None, description="Call duration in seconds")
    transcript: Optional[List[CallTranscriptMessage]] = Field(None, description="Call transcript")
    error_message: Optional[str] = Field(None, description="Error message if call failed")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    @validator('status')
    def validate_status(cls, v):
        """Validate status"""
        if v is not None:
            allowed_statuses = ['initiated', 'in_progress', 'completed', 'failed', 'no_answer']
            if v not in allowed_statuses:
                raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        return v

    @validator('duration')
    def validate_duration(cls, v):
        """Validate duration is positive"""
        if v is not None and v < 0:
            raise ValueError('Duration must be positive')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "status": "completed",
                "duration": 125.5,
                "transcript": [
                    {
                        "role": "user",
                        "content": "Hello",
                        "timestamp": "2024-01-15T10:30:15Z"
                    },
                    {
                        "role": "assistant",
                        "content": "Hi! How can I help you today?",
                        "timestamp": "2024-01-15T10:30:17Z"
                    }
                ]
            }
        }


class CallResponse(BaseModel):
    """Response schema for call information"""

    id: str = Field(..., description="Call record ID")
    call_sid: str = Field(..., description="Twilio Call SID")
    company_id: int = Field(..., description="Company ID")
    from_number: str = Field(..., description="Caller phone number")
    to_number: str = Field(..., description="Twilio phone number called")
    direction: str = Field(..., description="Call direction")
    status: str = Field(..., description="Call status")
    duration: Optional[float] = Field(None, description="Call duration in seconds")
    transcript: Optional[List[CallTranscriptMessage]] = Field(None, description="Call transcript")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    created_at: datetime = Field(..., description="Call start timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439014",
                "call_sid": "CA1234567890abcdef1234567890abcd",
                "company_id": "507f1f77bcf86cd799439012",
                "from_number": "+15559876543",
                "to_number": "+15551234567",
                "direction": "inbound",
                "status": "completed",
                "duration": 125.5,
                "transcript": [
                    {
                        "role": "user",
                        "content": "Hello",
                        "timestamp": "2024-01-15T10:30:15Z"
                    }
                ],
                "error_message": None,
                "metadata": {"agent_version": "v1.0"},
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:32:05Z"
            }
        }


class CallListResponse(BaseModel):
    """Response schema for paginated call list"""

    items: List[CallResponse] = Field(..., description="List of calls")
    total: int = Field(..., description="Total number of calls")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": "507f1f77bcf86cd799439014",
                        "call_sid": "CA1234567890abcdef",
                        "company_id": "507f1f77bcf86cd799439012",
                        "from_number": "+15559876543",
                        "to_number": "+15551234567",
                        "direction": "inbound",
                        "status": "completed",
                        "duration": 125.5,
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:32:05Z"
                    }
                ],
                "total": 1250,
                "page": 1,
                "page_size": 20,
                "total_pages": 63
            }
        }


class CallStatsResponse(BaseModel):
    """Response schema for call statistics"""

    company_id: Optional[int] = Field(None, description="Company ID (if filtered)")
    total_calls: int = Field(..., description="Total number of calls")
    completed_calls: int = Field(..., description="Number of completed calls")
    failed_calls: int = Field(..., description="Number of failed calls")
    in_progress_calls: int = Field(..., description="Number of ongoing calls")
    avg_duration: float = Field(..., description="Average call duration in seconds")
    total_duration: float = Field(..., description="Total call duration in seconds")
    calls_today: int = Field(..., description="Number of calls today")
    calls_this_week: int = Field(..., description="Number of calls this week")
    calls_this_month: int = Field(..., description="Number of calls this month")

    class Config:
        json_schema_extra = {
            "example": {
                "company_id": "507f1f77bcf86cd799439012",
                "total_calls": 1250,
                "completed_calls": 1180,
                "failed_calls": 70,
                "in_progress_calls": 5,
                "avg_duration": 145.8,
                "total_duration": 182250.0,
                "calls_today": 45,
                "calls_this_week": 285,
                "calls_this_month": 1250
            }
        }


class CallFilterParams(BaseModel):
    """Query parameters for filtering calls"""

    status: Optional[str] = Field(None, description="Filter by status")
    from_number: Optional[str] = Field(None, description="Filter by caller number")
    direction: Optional[str] = Field(None, description="Filter by direction")
    start_date: Optional[datetime] = Field(None, description="Filter calls after this date")
    end_date: Optional[datetime] = Field(None, description="Filter calls before this date")
    min_duration: Optional[float] = Field(None, description="Filter calls longer than this")
    max_duration: Optional[float] = Field(None, description="Filter calls shorter than this")

    @validator('status')
    def validate_status(cls, v):
        """Validate status"""
        if v is not None:
            allowed_statuses = ['initiated', 'in_progress', 'completed', 'failed', 'no_answer']
            if v not in allowed_statuses:
                raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        return v

    @validator('direction')
    def validate_direction(cls, v):
        """Validate direction"""
        if v is not None and v not in ['inbound', 'outbound']:
            raise ValueError("Direction must be 'inbound' or 'outbound'")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "status": "completed",
                "direction": "inbound",
                "start_date": "2024-01-01T00:00:00Z",
                "min_duration": 60.0
            }
        }


# Export schemas
__all__ = [
    "CallTranscriptMessage",
    "CallCreate",
    "CallUpdate",
    "CallResponse",
    "CallListResponse",
    "CallStatsResponse",
    "CallFilterParams"
]
