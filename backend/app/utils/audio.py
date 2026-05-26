"""
Audio Conversion Utilities
Handles conversion between different audio formats for Twilio integration
"""
import audioop
import base64
import io
import wave
from typing import Tuple, Optional
from pydub import AudioSegment
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class AudioConverter:
    """
    Handles audio format conversions for the voice pipeline

    Key formats:
    - mulaw (8kHz, 8-bit): Twilio's default format for WebSocket
    - PCM (16kHz, 16-bit): Standard format for STT providers
    - WAV: Container format for PCM data
    """

    @staticmethod
    def mulaw_to_pcm(mulaw_data: bytes, sample_rate: int = 8000) -> bytes:
        """
        Convert mulaw audio to linear PCM

        Args:
            mulaw_data: mulaw encoded audio bytes
            sample_rate: Sample rate of the mulaw audio (default: 8000Hz)

        Returns:
            PCM audio bytes (16-bit linear)
        """
        try:
            # Convert mulaw to linear PCM (16-bit)
            pcm_data = audioop.ulaw2lin(mulaw_data, 2)  # 2 = 16-bit width
            logger.debug(f"Converted {len(mulaw_data)} bytes mulaw to {len(pcm_data)} bytes PCM")
            return pcm_data
        except Exception as e:
            logger.error(f"Error converting mulaw to PCM: {str(e)}")
            raise

    @staticmethod
    def pcm_to_mulaw(pcm_data: bytes, sample_rate: int = 8000) -> bytes:
        """
        Convert linear PCM to mulaw

        Args:
            pcm_data: Linear PCM audio bytes (16-bit)
            sample_rate: Sample rate of the PCM audio

        Returns:
            mulaw encoded audio bytes
        """
        try:
            # Convert linear PCM to mulaw
            mulaw_data = audioop.lin2ulaw(pcm_data, 2)  # 2 = 16-bit width
            logger.debug(f"Converted {len(pcm_data)} bytes PCM to {len(mulaw_data)} bytes mulaw")
            return mulaw_data
        except Exception as e:
            logger.error(f"Error converting PCM to mulaw: {str(e)}")
            raise

    @staticmethod
    def resample_audio(
        audio_data: bytes,
        from_rate: int,
        to_rate: int,
        sample_width: int = 2
    ) -> bytes:
        """
        Resample audio to a different sample rate

        Args:
            audio_data: Raw audio bytes
            from_rate: Current sample rate
            to_rate: Target sample rate
            sample_width: Sample width in bytes (1=8-bit, 2=16-bit)

        Returns:
            Resampled audio bytes
        """
        try:
            if from_rate == to_rate:
                return audio_data

            # Resample audio
            resampled_data, _ = audioop.ratecv(
                audio_data,
                sample_width,
                1,  # mono
                from_rate,
                to_rate,
                None  # state
            )
            logger.debug(f"Resampled audio from {from_rate}Hz to {to_rate}Hz")
            return resampled_data
        except Exception as e:
            logger.error(f"Error resampling audio: {str(e)}")
            raise

    @staticmethod
    def pcm_to_wav(
        pcm_data: bytes,
        sample_rate: int = 16000,
        sample_width: int = 2,
        channels: int = 1
    ) -> bytes:
        """
        Convert raw PCM data to WAV format

        Args:
            pcm_data: Raw PCM audio bytes
            sample_rate: Sample rate in Hz
            sample_width: Sample width in bytes (2 for 16-bit)
            channels: Number of audio channels (1 for mono)

        Returns:
            WAV formatted audio bytes
        """
        try:
            # Create WAV file in memory
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(channels)
                wav_file.setsampwidth(sample_width)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(pcm_data)

            wav_data = wav_buffer.getvalue()
            logger.debug(f"Converted {len(pcm_data)} bytes PCM to {len(wav_data)} bytes WAV")
            return wav_data
        except Exception as e:
            logger.error(f"Error converting PCM to WAV: {str(e)}")
            raise

    @staticmethod
    def wav_to_pcm(wav_data: bytes) -> Tuple[bytes, int, int, int]:
        """
        Extract PCM data from WAV file

        Args:
            wav_data: WAV formatted audio bytes

        Returns:
            Tuple of (pcm_data, sample_rate, sample_width, channels)
        """
        try:
            wav_buffer = io.BytesIO(wav_data)
            with wave.open(wav_buffer, 'rb') as wav_file:
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                sample_rate = wav_file.getframerate()
                pcm_data = wav_file.readframes(wav_file.getnframes())

            logger.debug(
                f"Extracted {len(pcm_data)} bytes PCM from WAV "
                f"(rate={sample_rate}, width={sample_width}, channels={channels})"
            )
            return pcm_data, sample_rate, sample_width, channels
        except Exception as e:
            logger.error(f"Error extracting PCM from WAV: {str(e)}")
            raise

    @classmethod
    def twilio_to_stt_format(
        cls,
        mulaw_base64: str,
        target_sample_rate: int = 16000
    ) -> bytes:
        """
        Convert Twilio's mulaw base64 audio to format suitable for STT providers

        Pipeline:
        1. Decode base64 → mulaw bytes
        2. Convert mulaw → PCM (8kHz, 16-bit)
        3. Resample PCM 8kHz → 16kHz
        4. Wrap in WAV container

        Args:
            mulaw_base64: Base64 encoded mulaw audio from Twilio
            target_sample_rate: Target sample rate for STT (default: 16000Hz)

        Returns:
            WAV formatted audio bytes ready for STT
        """
        try:
            # Step 1: Decode base64
            mulaw_data = base64.b64decode(mulaw_base64)

            # Step 2: Convert mulaw to PCM
            pcm_data = cls.mulaw_to_pcm(mulaw_data, sample_rate=8000)

            # Step 3: Resample to target rate
            if target_sample_rate != 8000:
                pcm_data = cls.resample_audio(
                    pcm_data,
                    from_rate=8000,
                    to_rate=target_sample_rate,
                    sample_width=2
                )

            # Step 4: Wrap in WAV
            wav_data = cls.pcm_to_wav(
                pcm_data,
                sample_rate=target_sample_rate,
                sample_width=2,
                channels=1
            )

            logger.debug(
                f"Converted Twilio audio: {len(mulaw_data)} bytes mulaw → "
                f"{len(wav_data)} bytes WAV ({target_sample_rate}Hz)"
            )
            return wav_data

        except Exception as e:
            logger.error(f"Error converting Twilio audio to STT format: {str(e)}")
            raise

    @classmethod
    def tts_to_twilio_format(
        cls,
        audio_data: bytes,
        input_format: str = "wav",
        input_sample_rate: Optional[int] = None
    ) -> str:
        """
        Convert TTS output to Twilio's mulaw base64 format

        Pipeline:
        1. Extract PCM from WAV/MP3/etc (if needed)
        2. Resample to 8kHz (if needed)
        3. Convert PCM → mulaw
        4. Encode to base64

        Args:
            audio_data: Audio bytes from TTS provider
            input_format: Format of input audio ("wav", "pcm", "mp3", etc.)
            input_sample_rate: Sample rate of input (required if format="pcm")

        Returns:
            Base64 encoded mulaw audio for Twilio
        """
        try:
            # Step 1: Get PCM data
            if input_format.lower() == "wav":
                pcm_data, sample_rate, _, _ = cls.wav_to_pcm(audio_data)
            elif input_format.lower() == "pcm":
                if input_sample_rate is None:
                    raise ValueError("input_sample_rate required when format='pcm'")
                pcm_data = audio_data
                sample_rate = input_sample_rate
            elif input_format.lower() in ["mp3", "m4a", "ogg", "flac"]:
                # Use pydub to decode compressed formats (MP3, M4A, OGG, FLAC)
                logger.debug(f"Decoding {input_format} audio using pydub")
                audio_segment = AudioSegment.from_file(io.BytesIO(audio_data), format=input_format.lower())

                # Convert to PCM: 16-bit, mono
                audio_segment = audio_segment.set_channels(1).set_sample_width(2)
                sample_rate = audio_segment.frame_rate
                pcm_data = audio_segment.raw_data

                logger.debug(f"Decoded {input_format}: sample_rate={sample_rate}Hz, pcm_size={len(pcm_data)} bytes")
            else:
                raise ValueError(f"Unsupported input format: {input_format}")

            # Step 2: Resample to 8kHz if needed
            if sample_rate != 8000:
                pcm_data = cls.resample_audio(
                    pcm_data,
                    from_rate=sample_rate,
                    to_rate=8000,
                    sample_width=2
                )

            # Step 3: Convert to mulaw
            mulaw_data = cls.pcm_to_mulaw(pcm_data, sample_rate=8000)

            # Step 4: Encode to base64
            mulaw_base64 = base64.b64encode(mulaw_data).decode('utf-8')

            logger.debug(
                f"Converted TTS audio: {len(audio_data)} bytes {input_format} → "
                f"{len(mulaw_data)} bytes mulaw (base64: {len(mulaw_base64)} chars)"
            )
            return mulaw_base64

        except Exception as e:
            logger.error(f"Error converting TTS audio to Twilio format: {str(e)}")
            raise

    @staticmethod
    def get_audio_duration(
        audio_data: bytes,
        sample_rate: int,
        sample_width: int = 2,
        channels: int = 1
    ) -> float:
        """
        Calculate duration of audio in seconds

        Args:
            audio_data: Raw audio bytes
            sample_rate: Sample rate in Hz
            sample_width: Sample width in bytes
            channels: Number of channels

        Returns:
            Duration in seconds
        """
        num_samples = len(audio_data) // (sample_width * channels)
        duration = num_samples / sample_rate
        return duration

    @staticmethod
    def normalize_volume(audio_data: bytes, target_level: float = 0.8) -> bytes:
        """
        Normalize audio volume to target level

        Args:
            audio_data: PCM audio bytes (16-bit)
            target_level: Target volume level (0.0 to 1.0)

        Returns:
            Volume-normalized audio bytes
        """
        try:
            # Get current RMS
            current_rms = audioop.rms(audio_data, 2)

            if current_rms == 0:
                return audio_data

            # Calculate scaling factor
            max_rms = 32767 * target_level  # Max value for 16-bit audio
            factor = max_rms / current_rms

            # Apply scaling (limit to prevent clipping)
            factor = min(factor, 2.0)
            normalized = audioop.mul(audio_data, 2, factor)

            logger.debug(f"Normalized audio volume: RMS {current_rms} → {audioop.rms(normalized, 2)}")
            return normalized

        except Exception as e:
            logger.error(f"Error normalizing volume: {str(e)}")
            return audio_data  # Return original on error


class AudioBuffer:
    """
    Buffer for accumulating audio chunks before processing
    Used to handle network jitter and ensure sufficient audio for STT
    """

    def __init__(self, target_duration: float = 2.0, sample_rate: int = 8000):
        """
        Initialize audio buffer

        Args:
            target_duration: Target buffer duration in seconds
            sample_rate: Sample rate of audio
        """
        self.target_duration = target_duration
        self.sample_rate = sample_rate
        self.buffer: bytes = b""
        self.target_bytes = int(target_duration * sample_rate)  # For mulaw, 1 byte per sample
        logger.debug(f"Initialized audio buffer: target={target_duration}s, {self.target_bytes} bytes")

    def add_chunk(self, chunk: bytes) -> None:
        """Add audio chunk to buffer"""
        self.buffer += chunk

    def is_ready(self) -> bool:
        """Check if buffer has enough data for processing"""
        return len(self.buffer) >= self.target_bytes

    def get_and_clear(self) -> bytes:
        """Get buffered audio and clear buffer"""
        data = self.buffer
        self.buffer = b""
        return data

    def get_duration(self) -> float:
        """Get current buffer duration in seconds"""
        return len(self.buffer) / self.sample_rate

    def clear(self) -> None:
        """Clear buffer"""
        self.buffer = b""


# Export public classes
__all__ = ["AudioConverter", "AudioBuffer"]
