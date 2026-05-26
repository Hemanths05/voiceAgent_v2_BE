"""
ElevenLabs TTS Provider
Implementation of TTS using ElevenLabs API
"""
from typing import Optional
from elevenlabs.client import AsyncElevenLabs
from elevenlabs import Voice, VoiceSettings
from app.providers.base.tts_base import TTSBase, TTSResponse
from app.core.exceptions import TTSProviderError, ProviderAPIKeyMissingError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ElevenLabsTTS(TTSBase):
    """
    ElevenLabs Text-to-Speech provider
    High-quality voice synthesis with voice cloning support
    """

    def __init__(
        self,
        api_key: str,
        model: str = "eleven_monolingual_v1",
        voice_id: str = "XFyHddC2zKKgLBooDuhH",  # Default voice (Rachel)
        language: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize ElevenLabs TTS provider

        Args:
            api_key: ElevenLabs API key
            model: Model ID (eleven_monolingual_v1, eleven_multilingual_v2, etc.)
            voice_id: Voice ID
            language: Language code (not used by ElevenLabs directly)
            **kwargs: Additional parameters (stability, similarity_boost, etc.)
        """
        super().__init__(api_key, model, voice_id, language, **kwargs)

        if not api_key:
            raise ProviderAPIKeyMissingError("tts", "elevenlabs")

        # Initialize ElevenLabs client
        self.client = AsyncElevenLabs(api_key=api_key)

        # Voice settings
        self.stability = kwargs.get("stability", 0.5)
        self.similarity_boost = kwargs.get("similarity_boost", 0.75)

    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        audio_format: str = "pcm_16000",
        sample_rate: int = 16000,
        **kwargs
    ) -> TTSResponse:
        """
        Convert text to speech using ElevenLabs

        Args:
            text: Text to convert to speech
            voice_id: Override default voice ID
            audio_format: Audio format (mp3_44100_128, pcm_16000, etc.)
            sample_rate: Sample rate (used for response metadata)
            **kwargs: Additional parameters

        Returns:
            TTSResponse with audio data

        Raises:
            TTSProviderError: If synthesis fails
        """
        try:
            # Use provided voice_id or default
            voice = voice_id or self.voice_id

            logger.info(
                f"Synthesizing with ElevenLabs: "
                f"text_length={len(text)}, voice={voice}, model={self.model}"
            )

            # Get voice settings
            stability = kwargs.get("stability", self.stability)
            similarity_boost = kwargs.get("similarity_boost", self.similarity_boost)

            # Map format to ElevenLabs format
            # ElevenLabs format: mp3_44100_128, pcm_16000, pcm_22050, pcm_24000, etc.
            elevenlabs_format = audio_format

            # Call ElevenLabs API
            audio_generator = self.client.text_to_speech.convert(
                voice_id=voice,
                text=text,
                model_id=self.model,
                voice_settings=VoiceSettings(
                    stability=stability,
                    similarity_boost=similarity_boost,
                ),
                output_format=elevenlabs_format,
            )

            # Collect audio chunks
            audio_chunks = []
            async for chunk in audio_generator:
                if chunk:
                    audio_chunks.append(chunk)

            # Combine chunks
            audio_data = b"".join(audio_chunks)

            # Determine actual format from requested format
            if "mp3" in elevenlabs_format:
                actual_format = "mp3"
                actual_sample_rate = 44100
            elif "pcm" in elevenlabs_format:
                actual_format = "pcm"
                # Extract sample rate from format string
                if "16000" in elevenlabs_format:
                    actual_sample_rate = 16000
                elif "22050" in elevenlabs_format:
                    actual_sample_rate = 22050
                elif "24000" in elevenlabs_format:
                    actual_sample_rate = 24000
                else:
                    actual_sample_rate = sample_rate
            else:
                actual_format = "mp3"
                actual_sample_rate = sample_rate

            logger.info(
                f"✓ ElevenLabs synthesis successful: "
                f"audio_size={len(audio_data)} bytes, format={actual_format}"
            )

            return TTSResponse(
                audio_data=audio_data,
                audio_format=actual_format,
                sample_rate=actual_sample_rate,
                duration_seconds=None,  # ElevenLabs doesn't provide duration directly
                provider_metadata={
                    "model": self.model,
                    "voice_id": voice,
                    "provider": "elevenlabs",
                    "stability": stability,
                    "similarity_boost": similarity_boost,
                }
            )

        except Exception as e:
            error_msg = f"ElevenLabs synthesis failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise TTSProviderError("elevenlabs", error_msg)

    async def health_check(self) -> bool:
        """
        Check if ElevenLabs API is accessible

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try to get user info as a health check
            user = await self.client.user.get()
            return user is not None
        except Exception as e:
            logger.error(f"ElevenLabs health check failed: {str(e)}")
            return False

    async def get_available_voices(self) -> list:
        """
        Get list of available voices

        Returns:
            List of voice dictionaries with id, name, and description
        """
        try:
            voices_response = await self.client.voices.get_all()
            voices = [
                {
                    "id": voice.voice_id,
                    "name": voice.name,
                    "description": voice.description or "",
                }
                for voice in voices_response.voices
            ]
            return voices
        except Exception as e:
            logger.error(f"Failed to get ElevenLabs voices: {str(e)}")
            return []


# Export provider
__all__ = ["ElevenLabsTTS"]
