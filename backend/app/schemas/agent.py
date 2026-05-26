"""
Agent Configuration Schemas
Request/response models for agent configuration management
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime


class AgentConfigUpdate(BaseModel):
    """Schema for updating agent configuration"""

    # AI Provider selection
    stt_provider: Optional[str] = Field(None, description="STT provider (groq, openai, assemblyai, deepgram)")
    llm_provider: Optional[str] = Field(None, description="LLM provider (groq, openai, anthropic, gemini)")
    tts_provider: Optional[str] = Field(None, description="TTS provider (elevenlabs, openai, google, azure)")
    embeddings_provider: Optional[str] = Field(None, description="Embeddings provider (openai, voyage, cohere, gemini)")

    # AI Provider models
    stt_model: Optional[str] = Field(None, description="STT model name")
    llm_model: Optional[str] = Field(None, description="LLM model name")
    tts_model: Optional[str] = Field(None, description="TTS model name")
    embeddings_model: Optional[str] = Field(None, description="Embeddings model name")

    # LLM parameters
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="LLM temperature (0-2)")
    max_tokens: Optional[int] = Field(None, ge=1, le=4096, description="Max tokens to generate")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="LLM top_p parameter")

    # TTS parameters
    voice_id: Optional[str] = Field(None, description="TTS voice ID")
    voice_settings: Optional[Dict[str, Any]] = Field(None, description="TTS voice settings")

    # Agent behavior
    system_prompt: Optional[str] = Field(
        None,
        min_length=10,
        max_length=5000,
        description="System prompt for LLM"
    )
    greeting_message: Optional[str] = Field(
        None,
        max_length=500,
        description="Initial greeting message"
    )
    enable_rag: Optional[bool] = Field(None, description="Enable RAG (knowledge base)")
    rag_top_k: Optional[int] = Field(None, ge=1, le=20, description="Number of knowledge chunks to retrieve")
    conversation_history_limit: Optional[int] = Field(
        None,
        ge=0,
        le=50,
        description="Number of previous messages to include"
    )

    # Fallback configuration
    fallback_stt_provider: Optional[str] = Field(None, description="Fallback STT provider")
    fallback_llm_provider: Optional[str] = Field(None, description="Fallback LLM provider")
    fallback_tts_provider: Optional[str] = Field(None, description="Fallback TTS provider")

    # Advanced settings
    enable_interruption: Optional[bool] = Field(None, description="Allow user to interrupt agent")
    silence_timeout: Optional[float] = Field(None, ge=0.5, le=10.0, description="Silence timeout in seconds")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    @validator('stt_provider', 'fallback_stt_provider')
    def validate_stt_provider(cls, v):
        """Validate STT provider"""
        if v is not None:
            allowed = ['groq', 'openai', 'assemblyai', 'deepgram']
            if v not in allowed:
                raise ValueError(f"STT provider must be one of: {', '.join(allowed)}")
        return v

    @validator('llm_provider', 'fallback_llm_provider')
    def validate_llm_provider(cls, v):
        """Validate LLM provider"""
        if v is not None:
            allowed = ['groq', 'openai', 'anthropic', 'gemini']
            if v not in allowed:
                raise ValueError(f"LLM provider must be one of: {', '.join(allowed)}")
        return v

    @validator('tts_provider', 'fallback_tts_provider')
    def validate_tts_provider(cls, v):
        """Validate TTS provider"""
        if v is not None:
            allowed = ['elevenlabs', 'openai', 'google', 'azure']
            if v not in allowed:
                raise ValueError(f"TTS provider must be one of: {', '.join(allowed)}")
        return v

    @validator('embeddings_provider')
    def validate_embeddings_provider(cls, v):
        """Validate embeddings provider"""
        if v is not None:
            allowed = ['openai', 'voyage', 'cohere', 'gemini']
            if v not in allowed:
                raise ValueError(f"Embeddings provider must be one of: {', '.join(allowed)}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "llm_provider": "groq",
                "llm_model": "llama-3.3-70b-versatile",
                "temperature": 0.7,
                "max_tokens": 150,
                "system_prompt": "You are a helpful customer support agent. Be concise and friendly.",
                "greeting_message": "Hello! Thank you for calling. How can I help you today?",
                "enable_rag": True,
                "rag_top_k": 5,
                "conversation_history_limit": 10
            }
        }


class AgentConfigResponse(BaseModel):
    """Response schema for agent configuration"""

    id: str = Field(..., description="Configuration ID")
    company_id: int = Field(..., description="Company ID")

    # AI Provider selection
    stt_provider: str = Field(..., description="STT provider")
    llm_provider: str = Field(..., description="LLM provider")
    tts_provider: str = Field(..., description="TTS provider")
    embeddings_provider: str = Field(..., description="Embeddings provider")

    # AI Provider models
    stt_model: Optional[str] = Field(None, description="STT model name")
    llm_model: Optional[str] = Field(None, description="LLM model name")
    tts_model: Optional[str] = Field(None, description="TTS model name")
    embeddings_model: Optional[str] = Field(None, description="Embeddings model name")

    # LLM parameters
    temperature: float = Field(..., description="LLM temperature")
    max_tokens: int = Field(..., description="Max tokens to generate")
    top_p: float = Field(..., description="LLM top_p parameter")

    # TTS parameters
    voice_id: Optional[str] = Field(None, description="TTS voice ID")
    voice_settings: Optional[Dict[str, Any]] = Field(None, description="TTS voice settings")

    # Agent behavior
    system_prompt: str = Field(..., description="System prompt for LLM")
    greeting_message: str = Field(..., description="Initial greeting message")
    enable_rag: bool = Field(..., description="Enable RAG")
    rag_top_k: int = Field(..., description="Number of knowledge chunks to retrieve")
    conversation_history_limit: int = Field(..., description="Number of previous messages to include")

    # Fallback configuration
    fallback_stt_provider: Optional[str] = Field(None, description="Fallback STT provider")
    fallback_llm_provider: Optional[str] = Field(None, description="Fallback LLM provider")
    fallback_tts_provider: Optional[str] = Field(None, description="Fallback TTS provider")

    # Advanced settings
    enable_interruption: bool = Field(..., description="Allow user to interrupt agent")
    silence_timeout: float = Field(..., description="Silence timeout in seconds")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439015",
                "company_id": "507f1f77bcf86cd799439012",
                "stt_provider": "groq",
                "llm_provider": "groq",
                "tts_provider": "elevenlabs",
                "embeddings_provider": "gemini",
                "stt_model": "whisper-large-v3",
                "llm_model": "llama-3.3-70b-versatile",
                "tts_model": "eleven_multilingual_v2",
                "embeddings_model": "models/embedding-001",
                "temperature": 0.7,
                "max_tokens": 150,
                "top_p": 1.0,
                "voice_id": "XFyHddC2zKKgLBooDuhH",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
                "system_prompt": "You are a helpful customer support agent.",
                "greeting_message": "Hello! How can I help you today?",
                "enable_rag": True,
                "rag_top_k": 5,
                "conversation_history_limit": 10,
                "fallback_llm_provider": "openai",
                "enable_interruption": True,
                "silence_timeout": 2.0,
                "metadata": {"version": "v1.0"},
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }


class AgentTestRequest(BaseModel):
    """Request schema for testing agent configuration"""

    test_message: str = Field(..., min_length=1, max_length=500, description="Test message")
    include_rag: bool = Field(default=True, description="Test with RAG enabled")

    class Config:
        json_schema_extra = {
            "example": {
                "test_message": "What are your business hours?",
                "include_rag": True
            }
        }


class AgentTestResponse(BaseModel):
    """Response schema for agent test"""

    test_message: str = Field(..., description="Original test message")
    agent_response: str = Field(..., description="Agent's response")
    rag_results: Optional[list] = Field(None, description="RAG search results used")
    latency_ms: float = Field(..., description="Response latency in milliseconds")
    providers_used: Dict[str, str] = Field(..., description="Providers used for test")

    class Config:
        json_schema_extra = {
            "example": {
                "test_message": "What are your business hours?",
                "agent_response": "Our business hours are Monday through Friday, 9 AM to 5 PM.",
                "rag_results": [
                    {
                        "title": "Company Info",
                        "text": "Business hours: Mon-Fri 9-5",
                        "score": 0.89
                    }
                ],
                "latency_ms": 1250.5,
                "providers_used": {
                    "stt": "groq",
                    "llm": "groq",
                    "tts": "elevenlabs",
                    "embeddings": "gemini"
                }
            }
        }


# Export schemas
__all__ = [
    "AgentConfigUpdate",
    "AgentConfigResponse",
    "AgentTestRequest",
    "AgentTestResponse"
]
