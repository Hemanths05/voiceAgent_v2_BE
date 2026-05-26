"""
Speech-to-Text (STT) Provider Base Class
Abstract base class that all STT providers must implement
"""
from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel


class STTResponse(BaseModel):
    """
    Standard response format for STT providers
    """
    text: str  # Transcribed text
    confidence: Optional[float] = None  # Confidence score (0.0 to 1.0)
    language: Optional[str] = None  # Detected language code
    duration_seconds: Optional[float] = None  # Audio duration
    provider_metadata: Optional[dict] = None  # Provider-specific metadata


class STTBase(ABC):
    """
    Abstract base class for Speech-to-Text providers

    All STT providers must inherit from this class and implement the transcribe method.
    """

    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        language: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize STT provider

        Args:
            api_key: API key for the provider
            model: Model name (provider-specific)
            language: Language code (e.g., "en", "es", "fr")
            **kwargs: Additional provider-specific parameters
        """
        self.api_key = api_key
        self.model = model
        self.language = language
        self.extra_params = kwargs
        self.provider_name = self.__class__.__name__

    @abstractmethod
    async def transcribe(
        self,
        audio_data: bytes,
        audio_format: str = "wav",
        sample_rate: int = 16000,
        **kwargs
    ) -> STTResponse:
        """
        Transcribe audio to text

        Args:
            audio_data: Raw audio bytes
            audio_format: Audio format (wav, mp3, mulaw, etc.)
            sample_rate: Sample rate in Hz (e.g., 16000, 44100)
            **kwargs: Additional parameters for specific providers

        Returns:
            STTResponse with transcribed text and metadata

        Raises:
            STTProviderError: If transcription fails
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the provider is healthy and accessible

        Returns:
            True if provider is healthy, False otherwise
        """
        pass

    def __repr__(self) -> str:
        return f"{self.provider_name}(model={self.model}, language={self.language})"


# Export base class and response model
__all__ = ["STTBase", "STTResponse"]
