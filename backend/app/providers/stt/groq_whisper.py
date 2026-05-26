"""
Groq Whisper STT Provider
Implementation of STT using Groq's Whisper API
"""
import io
from typing import Optional
from groq import AsyncGroq
from app.providers.base.stt_base import STTBase, STTResponse
from app.core.exceptions import STTProviderError, ProviderAPIKeyMissingError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class GroqWhisperSTT(STTBase):
    """
    Groq Whisper Speech-to-Text provider
    Uses Groq's fast Whisper implementation
    """

    def __init__(
        self,
        api_key: str,
        model: str = "whisper-large-v3",
        language: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize Groq Whisper STT provider

        Args:
            api_key: Groq API key
            model: Whisper model (whisper-large-v3, whisper-large-v3-turbo)
            language: Language code (e.g., "en", "es", "fr")
            **kwargs: Additional parameters
        """
        super().__init__(api_key, model, language, **kwargs)

        if not api_key:
            raise ProviderAPIKeyMissingError("stt", "groq")

        # Initialize Groq client
        self.client = AsyncGroq(api_key=api_key)

    async def transcribe(
        self,
        audio_data: bytes,
        audio_format: str = "wav",
        sample_rate: int = 16000,
        **kwargs
    ) -> STTResponse:
        """
        Transcribe audio to text using Groq Whisper

        Args:
            audio_data: Raw audio bytes
            audio_format: Audio format (wav, mp3, m4a, etc.)
            sample_rate: Sample rate in Hz
            **kwargs: Additional parameters

        Returns:
            STTResponse with transcribed text

        Raises:
            STTProviderError: If transcription fails
        """
        try:
            logger.info(
                f"Transcribing audio with Groq Whisper: "
                f"format={audio_format}, sample_rate={sample_rate}, "
                f"size={len(audio_data)} bytes"
            )

            # Create a file-like object from audio bytes
            # Groq expects a file with proper extension
            audio_file = io.BytesIO(audio_data)
            audio_file.name = f"audio.{audio_format}"

            # Call Groq Whisper API
            transcription = await self.client.audio.transcriptions.create(
                file=audio_file,
                model=self.model,
                language=self.language,
                response_format="verbose_json",  # Get detailed response
                **kwargs
            )

            # Extract response data
            text = transcription.text
            language = getattr(transcription, "language", self.language)
            duration = getattr(transcription, "duration", None)

            logger.info(
                f"✓ Groq Whisper transcription successful: "
                f"text_length={len(text)}, language={language}"
            )

            return STTResponse(
                text=text,
                confidence=None,  # Groq doesn't provide confidence scores
                language=language,
                duration_seconds=duration,
                provider_metadata={
                    "model": self.model,
                    "provider": "groq",
                }
            )

        except Exception as e:
            error_msg = f"Groq Whisper transcription failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise STTProviderError("groq", error_msg)

    async def health_check(self) -> bool:
        """
        Check if Groq Whisper API is accessible

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try to list models as a health check
            models = await self.client.models.list()
            return len(models.data) > 0
        except Exception as e:
            logger.error(f"Groq Whisper health check failed: {str(e)}")
            return False


# Export provider
__all__ = ["GroqWhisperSTT"]
