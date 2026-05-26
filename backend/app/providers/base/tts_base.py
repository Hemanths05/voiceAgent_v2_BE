"""
Text-to-Speech (TTS) Provider Base Class
Abstract base class that all TTS providers must implement
"""
from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel


class TTSResponse(BaseModel):
    """
    Standard response format for TTS providers
    """
    audio_data: bytes  # Raw audio bytes
    audio_format: str  # Audio format (mp3, wav, pcm, etc.)
    sample_rate: int  # Sample rate in Hz (e.g., 22050, 44100)
    duration_seconds: Optional[float] = None  # Audio duration
    provider_metadata: Optional[dict] = None  # Provider-specific metadata


class TTSBase(ABC):
    """
    Abstract base class for Text-to-Speech providers

    All TTS providers must inherit from this class and implement the synthesize method.
    """

    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        voice_id: Optional[str] = None,
        language: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize TTS provider

        Args:
            api_key: API key for the provider
            model: Model name (provider-specific)
            voice_id: Voice ID or name
            language: Language code (e.g., "en-US", "es-ES")
            **kwargs: Additional provider-specific parameters
        """
        self.api_key = api_key
        self.model = model
        self.voice_id = voice_id
        self.language = language
        self.extra_params = kwargs
        self.provider_name = self.__class__.__name__

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        audio_format: str = "mp3",
        sample_rate: int = 22050,
        **kwargs
    ) -> TTSResponse:
        """
        Convert text to speech

        Args:
            text: Text to convert to speech
            voice_id: Override default voice ID
            audio_format: Desired audio format (mp3, wav, pcm, etc.)
            sample_rate: Desired sample rate in Hz
            **kwargs: Additional parameters for specific providers

        Returns:
            TTSResponse with audio data and metadata

        Raises:
            TTSProviderError: If synthesis fails
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

    async def get_available_voices(self) -> list:
        """
        Get list of available voices (optional)

        Returns:
            List of available voice IDs/names

        Note:
            Not all providers may implement this method
        """
        return []

    def __repr__(self) -> str:
        return (
            f"{self.provider_name}(model={self.model}, "
            f"voice_id={self.voice_id}, language={self.language})"
        )


# Export base class and response model
__all__ = ["TTSBase", "TTSResponse"]
