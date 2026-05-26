"""
Call Database Model
Pydantic model for calls collection
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.database.models.user import PyObjectId


class CallBase(BaseModel):
    """Base call model with common fields"""

    call_sid: str = Field(..., min_length=34, max_length=34)  # Twilio SID format
    company_id: int = Field(...)
    caller_number: str = Field(..., pattern=r"^\+[1-9]\d{1,14}$")  # E.164 format
    direction: str = Field(..., pattern="^(inbound|outbound)$")
    status: str = Field(
        default="ringing",
        pattern="^(ringing|in-progress|completed|failed|no-answer|busy|canceled)$"
    )

    class Config:
        json_encoders = {PyObjectId: str}
        populate_by_name = True


class CallCreate(CallBase):
    """Call creation model"""

    pass


class CallInDB(CallBase):
    """Call model as stored in database"""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    duration: Optional[int] = None  # Duration in seconds
    transcript: Optional[str] = None
    recording_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None

    class Config:
        json_encoders = {PyObjectId: str}
        populate_by_name = True
        arbitrary_types_allowed = True


class CallResponse(BaseModel):
    """Call model for API responses"""

    id: str
    call_sid: str
    company_id: int
    caller_number: str
    direction: str
    status: str
    duration: Optional[int] = None
    transcript: Optional[str] = None
    recording_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    ended_at: Optional[datetime] = None

    @classmethod
    def from_db(cls, call: CallInDB) -> "CallResponse":
        """
        Create CallResponse from database model

        Args:
            call: Call from database

        Returns:
            CallResponse instance
        """
        return cls(
            id=str(call.id),
            call_sid=call.call_sid,
            company_id=call.company_id,
            caller_number=call.caller_number,
            direction=call.direction,
            status=call.status,
            duration=call.duration,
            transcript=call.transcript,
            recording_url=call.recording_url,
            created_at=call.created_at,
            updated_at=call.updated_at,
            ended_at=call.ended_at,
        )


class CallUpdate(BaseModel):
    """Call update model"""

    status: Optional[str] = Field(
        None,
        pattern="^(ringing|in-progress|completed|failed|no-answer|busy|canceled)$"
    )
    duration: Optional[int] = Field(None, ge=0)
    transcript: Optional[str] = None
    recording_url: Optional[str] = None
    ended_at: Optional[datetime] = None


class CallListItem(BaseModel):
    """Simplified call model for list endpoints"""

    id: str
    call_sid: str
    caller_number: str
    direction: str
    status: str
    duration: Optional[int] = None
    created_at: datetime


class CallAnalytics(BaseModel):
    """Call analytics for dashboard"""

    total_calls: int = 0
    completed_calls: int = 0
    failed_calls: int = 0
    avg_duration_seconds: float = 0.0
    total_duration_seconds: int = 0
    calls_today: int = 0
    calls_this_week: int = 0
    calls_this_month: int = 0


# Export models
__all__ = [
    "CallBase",
    "CallCreate",
    "CallInDB",
    "CallResponse",
    "CallUpdate",
    "CallListItem",
    "CallAnalytics",
]
