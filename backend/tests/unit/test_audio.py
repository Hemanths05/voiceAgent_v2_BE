"""
Unit Tests for Audio Utilities
Tests audio format conversion and buffering
"""
import pytest
import base64
from app.utils.audio import AudioConverter, AudioBuffer


class TestAudioConverter:
    """Test AudioConverter class"""

    def test_mulaw_to_pcm(self, sample_audio_mulaw):
        """Test mulaw to PCM conversion"""
        pcm_data = AudioConverter.mulaw_to_pcm(sample_audio_mulaw, sample_rate=8000)

        assert isinstance(pcm_data, bytes)
        assert len(pcm_data) > 0
        # PCM should be ~2x the size of mulaw (16-bit vs 8-bit)
        assert len(pcm_data) >= len(sample_audio_mulaw)

    def test_pcm_to_mulaw(self, sample_audio_pcm):
        """Test PCM to mulaw conversion"""
        mulaw_data = AudioConverter.pcm_to_mulaw(sample_audio_pcm, sample_rate=8000)

        assert isinstance(mulaw_data, bytes)
        assert len(mulaw_data) > 0
        # Mulaw should be ~0.5x the size of PCM (8-bit vs 16-bit)
        assert len(mulaw_data) <= len(sample_audio_pcm)

    def test_roundtrip_conversion(self, sample_audio_mulaw):
        """Test roundtrip conversion (mulaw -> PCM -> mulaw)"""
        # Convert to PCM
        pcm_data = AudioConverter.mulaw_to_pcm(sample_audio_mulaw, sample_rate=8000)

        # Convert back to mulaw
        mulaw_data = AudioConverter.pcm_to_mulaw(pcm_data, sample_rate=8000)

        # Should be same length as original
        assert len(mulaw_data) == len(sample_audio_mulaw)

    def test_pcm_to_wav(self, sample_audio_pcm):
        """Test PCM to WAV conversion"""
        wav_data = AudioConverter.pcm_to_wav(
            sample_audio_pcm,
            sample_rate=8000,
            sample_width=2,
            channels=1
        )

        assert isinstance(wav_data, bytes)
        assert len(wav_data) > len(sample_audio_pcm)  # WAV has header
        # Check WAV header
        assert wav_data[:4] == b'RIFF'
        assert wav_data[8:12] == b'WAVE'

    def test_wav_to_pcm(self):
        """Test WAV to PCM conversion"""
        # Create a simple WAV file
        sample_pcm = bytes([0x00] * 320)
        wav_data = AudioConverter.pcm_to_wav(sample_pcm, sample_rate=8000, sample_width=2, channels=1)

        # Convert back to PCM
        pcm_data, sample_rate, sample_width, channels = AudioConverter.wav_to_pcm(wav_data)

        assert isinstance(pcm_data, bytes)
        assert sample_rate == 8000
        assert sample_width == 2
        assert channels == 1
        assert len(pcm_data) == len(sample_pcm)

    def test_twilio_to_stt_format(self, sample_audio_mulaw):
        """Test Twilio mulaw to STT WAV format"""
        # Encode to base64 (as Twilio sends it)
        mulaw_base64 = base64.b64encode(sample_audio_mulaw).decode('utf-8')

        # Convert to STT format
        wav_data = AudioConverter.twilio_to_stt_format(mulaw_base64, target_sample_rate=16000)

        assert isinstance(wav_data, bytes)
        # Should be WAV format
        assert wav_data[:4] == b'RIFF'
        assert wav_data[8:12] == b'WAVE'

    def test_tts_to_twilio_format(self):
        """Test TTS WAV to Twilio mulaw format"""
        # Create sample WAV
        sample_pcm = bytes([0x00] * 320)
        wav_data = AudioConverter.pcm_to_wav(sample_pcm, sample_rate=16000, sample_width=2, channels=1)

        # Convert to Twilio format
        mulaw_base64 = AudioConverter.tts_to_twilio_format(
            wav_data,
            input_format="wav",
            input_sample_rate=16000
        )

        assert isinstance(mulaw_base64, str)
        # Should be valid base64
        try:
            decoded = base64.b64decode(mulaw_base64)
            assert isinstance(decoded, bytes)
        except Exception:
            pytest.fail("Invalid base64 output")

    def test_resample_audio(self, sample_audio_pcm):
        """Test audio resampling"""
        # Resample from 8kHz to 16kHz
        resampled = AudioConverter.resample_audio(
            sample_audio_pcm,
            from_rate=8000,
            to_rate=16000,
            sample_width=2
        )

        assert isinstance(resampled, bytes)
        # Should be approximately 2x the size (double sample rate)
        assert len(resampled) > len(sample_audio_pcm)


class TestAudioBuffer:
    """Test AudioBuffer class"""

    def test_buffer_initialization(self):
        """Test buffer initialization"""
        buffer = AudioBuffer(max_duration_ms=2000)

        assert buffer.max_duration_ms == 2000
        assert buffer.get_duration_ms() == 0
        assert buffer.is_empty()
        assert not buffer.is_ready()

    def test_buffer_append(self, sample_audio_mulaw):
        """Test appending audio to buffer"""
        buffer = AudioBuffer(max_duration_ms=2000)

        # Append 20ms of audio
        buffer.append(sample_audio_mulaw, duration_ms=20)

        assert not buffer.is_empty()
        assert buffer.get_duration_ms() == 20
        assert not buffer.is_ready()  # Not ready until 2000ms

    def test_buffer_ready(self, sample_audio_mulaw):
        """Test buffer ready state"""
        buffer = AudioBuffer(max_duration_ms=100)  # Small buffer for testing

        # Append multiple chunks
        for _ in range(10):
            buffer.append(sample_audio_mulaw, duration_ms=20)

        # Should be ready after 100ms (5 chunks)
        assert buffer.is_ready()

    def test_buffer_get_and_clear(self, sample_audio_mulaw):
        """Test getting buffer contents and clearing"""
        buffer = AudioBuffer(max_duration_ms=100)

        # Append some audio
        buffer.append(sample_audio_mulaw, duration_ms=20)
        buffer.append(sample_audio_mulaw, duration_ms=20)

        # Get buffer
        data = buffer.get_buffer()
        assert len(data) == len(sample_audio_mulaw) * 2

        # Clear buffer
        buffer.clear()
        assert buffer.is_empty()
        assert buffer.get_duration_ms() == 0

    def test_buffer_overflow(self, sample_audio_mulaw):
        """Test buffer doesn't overflow max duration"""
        buffer = AudioBuffer(max_duration_ms=100)

        # Try to append more than max duration
        for _ in range(20):  # 400ms total
            buffer.append(sample_audio_mulaw, duration_ms=20)

        # Duration should be capped
        assert buffer.get_duration_ms() <= buffer.max_duration_ms + 20  # Allow one chunk over
