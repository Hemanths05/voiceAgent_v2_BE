"""
Google TTS Provider
Implementation of TTS using Google's Gemini TTS API
"""
from typing import Optional
import httpx
import base64
from app.providers.base.tts_base import TTSBase, TTSResponse
from app.core.exceptions import TTSProviderError, ProviderAPIKeyMissingError
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Available Gemini TTS voices
GEMINI_TTS_VOICES = [
    "Zephyr", "Puck", "Charon", "Kore", "Fenrir",
    "Aoede", "Leda", "Orus", "Vale",
]

GEMINI_TTS_MODEL = "gemini-2.5-flash-preview-tts"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GoogleTTS(TTSBase):
    """
    Google TTS provider using Gemini TTS API
    Outputs PCM audio at 24kHz
    """

    def __init__(
        self,
        api_key: str,
        model: Optional[str] = None,
        voice_id: Optional[str] = None,
        language: Optional[str] = None,
        **kwargs
    ):
        # The config maps google_tts_voice as the "model" for google provider.
        # If model is a known voice name, treat it as voice_id instead.
        if model and model in GEMINI_TTS_VOICES:
            voice_id = voice_id or model
            model = GEMINI_TTS_MODEL
        elif not model:
            model = GEMINI_TTS_MODEL

        if not voice_id:
            voice_id = "Kore"

        super().__init__(api_key, model, voice_id, language, **kwargs)

        if not api_key:
            raise ProviderAPIKeyMissingError("tts", "google")

        self.client = httpx.AsyncClient(timeout=30)

    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        audio_format: str = "pcm",
        sample_rate: int = 24000,
        **kwargs
    ) -> TTSResponse:
        try:
            voice = voice_id or self.voice_id or "Kore"

            logger.info(
                f"Synthesizing with Google TTS: "
                f"text_length={len(text)}, voice={voice}, model={self.model}"
            )

            resp = await self.client.post(
                f"{GEMINI_API_URL}/{self.model}:generateContent",
                params={"key": self.api_key},
                json={
                    "contents": [{"parts": [{"text": text}]}],
                    "generationConfig": {
                        "responseModalities": ["AUDIO"],
                        "speechConfig": {
                            "voiceConfig": {
                                "prebuiltVoiceConfig": {
                                    "voiceName": voice
                                }
                            }
                        }
                    }
                }
            )

            if resp.status_code != 200:
                raise TTSProviderError(
                    "google",
                    f"Gemini TTS API error {resp.status_code}: {resp.text[:300]}"
                )

            data = resp.json()
            parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])

            audio_data = None
            for part in parts:
                if "inlineData" in part:
                    audio_data = base64.b64decode(part["inlineData"]["data"])
                    break

            if not audio_data:
                raise TTSProviderError("google", "No audio data in response")

            logger.info(
                f"Google TTS synthesis successful: "
                f"audio_size={len(audio_data)} bytes, format=pcm, rate=24000"
            )

            return TTSResponse(
                audio_data=audio_data,
                audio_format="pcm",
                sample_rate=24000,
                duration_seconds=None,
                provider_metadata={
                    "model": self.model,
                    "voice_id": voice,
                    "provider": "google",
                }
            )

        except TTSProviderError:
            raise
        except Exception as e:
            error_msg = f"Google TTS synthesis failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise TTSProviderError("google", error_msg)

    async def health_check(self) -> bool:
        try:
            resp = await self.client.post(
                f"{GEMINI_API_URL}/{self.model}:generateContent",
                params={"key": self.api_key},
                json={
                    "contents": [{"parts": [{"text": "test"}]}],
                    "generationConfig": {
                        "responseModalities": ["AUDIO"],
                        "speechConfig": {
                            "voiceConfig": {
                                "prebuiltVoiceConfig": {
                                    "voiceName": "Kore"
                                }
                            }
                        }
                    }
                }
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Google TTS health check failed: {str(e)}")
            return False

    async def get_available_voices(self) -> list:
        return [{"id": v, "name": v, "description": f"Gemini TTS voice: {v}"} for v in GEMINI_TTS_VOICES]


__all__ = ["GoogleTTS"]
