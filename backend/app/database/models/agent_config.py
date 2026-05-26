"""
Agent Configuration Database Model
Pydantic model for agent_configs collection
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.database.models.user import PyObjectId


class AgentConfigBase(BaseModel):
    """Base agent configuration model with common fields"""

    company_id: int = Field(..., description="Company ID (unique per company)")

    # Provider Selection
    stt_provider: str = Field(
        default="groq",
        pattern="^(groq|openai|assemblyai|deepgram)$"
    )
    llm_provider: str = Field(
        default="groq",
        pattern="^(groq|openai|anthropic|gemini)$"
    )
    llm_model: str = Field(default="llama-3.3-70b-versatile")
    tts_provider: str = Field(
        default="elevenlabs",
        pattern="^(elevenlabs|openai|google|azure)$"
    )
    voice_id: Optional[str] = Field(default="XFyHddC2zKKgLBooDuhH")  # ElevenLabs default
    embedding_provider: str = Field(
        default="openai",
        pattern="^(openai|voyage|cohere|gemini)$"
    )

    # LLM Parameters
    system_prompt: str = Field(
        default="You are a helpful and friendly customer support agent. "
        "You provide accurate information based on the company's knowledge base. "
        "Be concise and professional."
    )
    greeting_message: str = Field(
        default="Hello! Thank you for calling. How can I assist you today?"
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=150, ge=1, le=4096)
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)

    class Config:
        json_encoders = {PyObjectId: str}
        populate_by_name = True


class AgentConfigCreate(AgentConfigBase):
    """Agent configuration creation model"""

    pass


class AgentConfigInDB(AgentConfigBase):
    """Agent configuration model as stored in database"""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {PyObjectId: str}
        populate_by_name = True
        arbitrary_types_allowed = True


class AgentConfigResponse(BaseModel):
    """Agent configuration model for API responses"""

    id: str
    company_id: str
    stt_provider: str
    llm_provider: str
    llm_model: str
    tts_provider: str
    voice_id: Optional[str]
    embedding_provider: str
    system_prompt: str
    greeting_message: str
    temperature: float
    max_tokens: int
    top_p: Optional[float]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db(cls, config: AgentConfigInDB) -> "AgentConfigResponse":
        """
        Create AgentConfigResponse from database model

        Args:
            config: Agent configuration from database

        Returns:
            AgentConfigResponse instance
        """
        return cls(
            id=str(config.id),
            company_id=config.company_id,
            stt_provider=config.stt_provider,
            llm_provider=config.llm_provider,
            llm_model=config.llm_model,
            tts_provider=config.tts_provider,
            voice_id=config.voice_id,
            embedding_provider=config.embedding_provider,
            system_prompt=config.system_prompt,
            greeting_message=config.greeting_message,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            top_p=config.top_p,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )


class AgentConfigUpdate(BaseModel):
    """Agent configuration update model"""

    stt_provider: Optional[str] = Field(None, pattern="^(groq|openai|assemblyai|deepgram)$")
    llm_provider: Optional[str] = Field(None, pattern="^(groq|openai|anthropic|gemini)$")
    llm_model: Optional[str] = None
    tts_provider: Optional[str] = Field(None, pattern="^(elevenlabs|openai|google|azure)$")
    voice_id: Optional[str] = None
    embedding_provider: Optional[str] = Field(None, pattern="^(openai|voyage|cohere|gemini)$")
    system_prompt: Optional[str] = None
    greeting_message: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=4096)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)


# Export models
__all__ = [
    "AgentConfigBase",
    "AgentConfigCreate",
    "AgentConfigInDB",
    "AgentConfigResponse",
    "AgentConfigUpdate",
]
