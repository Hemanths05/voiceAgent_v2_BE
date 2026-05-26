"""
Application Configuration
Loads and validates all environment variables using Pydantic Settings
"""
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # ==================== APPLICATION ====================
    app_name: str = Field(default="Voice Agent Platform")
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    # ==================== SERVER ====================
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    public_url: str = Field(default="http://localhost:8000")

    # ==================== SECURITY ====================
    secret_key: str = Field(min_length=32)
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=15)
    refresh_token_expire_days: int = Field(default=7)

    # ==================== MONGODB ====================
    mongodb_url: str = Field(...)
    mongodb_db_name: str = Field(default="voice_agent_platform")
    mongodb_max_pool_size: int = Field(default=10)
    mongodb_min_pool_size: int = Field(default=1)

    # ==================== QDRANT ====================
    qdrant_url: str = Field(...)
    qdrant_api_key: Optional[str] = Field(default=None)
    qdrant_collection_name: str = Field(default="knowledge_base")
    qdrant_vector_size: int = Field(default=1536)

    # ==================== TWILIO ====================
    twilio_account_sid: str = Field(...)
    twilio_auth_token: str = Field(...)
    twilio_phone_number: str = Field(...)

    # WebSocket URL for Twilio Media Streams (wss://your-domain.com)
    websocket_base_url: Optional[str] = Field(default=None)

    # ==================== AI PROVIDER SELECTION ====================
    stt_provider: str = Field(default="groq")
    llm_provider: str = Field(default="groq")
    tts_provider: str = Field(default="elevenlabs")
    embeddings_provider: str = Field(default="openai")

    # ==================== AI PROVIDER API KEYS ====================
    # STT
    groq_api_key: Optional[str] = Field(default=None)
    openai_api_key: Optional[str] = Field(default=None)
    assemblyai_api_key: Optional[str] = Field(default=None)
    deepgram_api_key: Optional[str] = Field(default=None)

    # LLM
    anthropic_api_key: Optional[str] = Field(default=None)
    google_api_key: Optional[str] = Field(default=None)

    # TTS
    elevenlabs_api_key: Optional[str] = Field(default=None)
    google_cloud_tts_credentials_path: Optional[str] = Field(default=None)
    azure_tts_key: Optional[str] = Field(default=None)
    azure_tts_region: Optional[str] = Field(default="eastus")

    # Embeddings
    voyage_api_key: Optional[str] = Field(default=None)
    cohere_api_key: Optional[str] = Field(default=None)

    # ==================== AI PROVIDER MODELS ====================
    # STT Models
    groq_whisper_model: str = Field(default="whisper-large-v3")
    openai_whisper_model: str = Field(default="whisper-1")
    assemblyai_model: str = Field(default="best")
    deepgram_model: str = Field(default="nova-2")

    # LLM Models
    groq_llm_model: str = Field(default="llama-3.3-70b-versatile")
    openai_llm_model: str = Field(default="gpt-4o")
    anthropic_llm_model: str = Field(default="claude-3-5-sonnet-20241022")
    gemini_llm_model: str = Field(default="gemini-2.0-flash-exp")

    # TTS Models/Voices
    elevenlabs_voice_id: str = Field(default="XFyHddC2zKKgLBooDuhH")
    elevenlabs_model_id: str = Field(default="eleven_monolingual_v1")
    openai_tts_model: str = Field(default="tts-1")
    openai_tts_voice: str = Field(default="alloy")
    google_tts_voice: str = Field(default="en-US-Neural2-C")
    azure_tts_voice: str = Field(default="en-US-AriaNeural")

    # Embeddings Models
    openai_embeddings_model: str = Field(default="text-embedding-ada-002")
    voyage_embeddings_model: str = Field(default="voyage-2")
    cohere_embeddings_model: str = Field(default="embed-english-v3.0")
    gemini_embeddings_model: str = Field(default="models/text-embedding-004")

    # ==================== AGENT DEFAULT SETTINGS ====================
    default_system_prompt: str = Field(
        default="You are a helpful and friendly customer support agent. "
        "You provide accurate information based on the company's knowledge base. "
        "Be concise and professional."
    )
    default_greeting: str = Field(
        default="Hello! Thank you for calling. How can I assist you today?"
    )
    default_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    default_max_tokens: int = Field(default=150, ge=1, le=4096)
    default_top_p: float = Field(default=1.0, ge=0.0, le=1.0)

    # ==================== RAG CONFIGURATION ====================
    rag_chunk_size: int = Field(default=512, ge=100, le=2000)
    rag_chunk_overlap: int = Field(default=50, ge=0, le=500)
    rag_top_k: int = Field(default=5, ge=1, le=20)
    rag_similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

    # ==================== FILE UPLOAD ====================
    max_upload_size_mb: int = Field(default=50, ge=1, le=500)
    allowed_file_types: str = Field(default="pdf,txt,docx,csv,xlsx")

    @property
    def allowed_file_types_list(self) -> List[str]:
        """Get allowed file types as a list"""
        return [ft.strip() for ft in self.allowed_file_types.split(",")]

    # ==================== RATE LIMITING ====================
    rate_limit_per_minute: int = Field(default=60, ge=1)
    rate_limit_per_hour: int = Field(default=1000, ge=1)

    # ==================== AUDIO PROCESSING ====================
    audio_sample_rate: int = Field(default=16000)
    audio_buffer_size_seconds: int = Field(default=2, ge=1, le=10)
    audio_channels: int = Field(default=1)

    # ==================== CORS ====================
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:8000")
    cors_allow_credentials: bool = Field(default=True)
    cors_allow_methods: str = Field(default="*")
    cors_allow_headers: str = Field(default="*")

    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list"""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # ==================== VALIDATORS ====================
    @validator("stt_provider")
    def validate_stt_provider(cls, v):
        valid_providers = ["groq", "openai", "assemblyai", "deepgram"]
        if v.lower() not in valid_providers:
            raise ValueError(f"STT provider must be one of {valid_providers}")
        return v.lower()

    @validator("llm_provider")
    def validate_llm_provider(cls, v):
        valid_providers = ["groq", "openai", "anthropic", "gemini"]
        if v.lower() not in valid_providers:
            raise ValueError(f"LLM provider must be one of {valid_providers}")
        return v.lower()

    @validator("tts_provider")
    def validate_tts_provider(cls, v):
        valid_providers = ["elevenlabs", "openai", "google", "azure"]
        if v.lower() not in valid_providers:
            raise ValueError(f"TTS provider must be one of {valid_providers}")
        return v.lower()

    @validator("embeddings_provider")
    def validate_embeddings_provider(cls, v):
        valid_providers = ["openai", "voyage", "cohere", "gemini"]
        if v.lower() not in valid_providers:
            raise ValueError(f"Embeddings provider must be one of {valid_providers}")
        return v.lower()

    @validator("environment")
    def validate_environment(cls, v):
        valid_envs = ["development", "staging", "production"]
        if v.lower() not in valid_envs:
            raise ValueError(f"Environment must be one of {valid_envs}")
        return v.lower()

    @validator("log_level")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()


# Global settings instance
settings = Settings()


# Helper functions
def get_provider_api_key(provider_type: str, provider_name: str) -> Optional[str]:
    """
    Get API key for a specific provider

    Args:
        provider_type: Type of provider (stt, llm, tts, embeddings)
        provider_name: Name of provider (groq, openai, etc.)

    Returns:
        API key if available, None otherwise
    """
    key_mapping = {
        "groq": settings.groq_api_key,
        "openai": settings.openai_api_key,
        "assemblyai": settings.assemblyai_api_key,
        "deepgram": settings.deepgram_api_key,
        "anthropic": settings.anthropic_api_key,
        "google": settings.google_api_key,
        "gemini": settings.google_api_key,
        "elevenlabs": settings.elevenlabs_api_key,
        "azure": settings.azure_tts_key,
        "voyage": settings.voyage_api_key,
        "cohere": settings.cohere_api_key,
    }

    return key_mapping.get(provider_name.lower())


def get_provider_model(provider_type: str, provider_name: str) -> str:
    """
    Get model name for a specific provider

    Args:
        provider_type: Type of provider (stt, llm, tts, embeddings)
        provider_name: Name of provider (groq, openai, etc.)

    Returns:
        Model name
    """
    if provider_type == "stt":
        model_mapping = {
            "groq": settings.groq_whisper_model,
            "openai": settings.openai_whisper_model,
            "assemblyai": settings.assemblyai_model,
            "deepgram": settings.deepgram_model,
        }
    elif provider_type == "llm":
        model_mapping = {
            "groq": settings.groq_llm_model,
            "openai": settings.openai_llm_model,
            "anthropic": settings.anthropic_llm_model,
            "gemini": settings.gemini_llm_model,
        }
    elif provider_type == "tts":
        model_mapping = {
            "elevenlabs": settings.elevenlabs_model_id,
            "openai": settings.openai_tts_model,
            "google": settings.google_tts_voice,
            "azure": settings.azure_tts_voice,
        }
    elif provider_type == "embeddings":
        model_mapping = {
            "openai": settings.openai_embeddings_model,
            "voyage": settings.voyage_embeddings_model,
            "cohere": settings.cohere_embeddings_model,
            "gemini": settings.gemini_embeddings_model,
        }
    else:
        return ""

    return model_mapping.get(provider_name.lower(), "")


# Export settings and helpers
__all__ = ["settings", "get_provider_api_key", "get_provider_model", "Settings"]
