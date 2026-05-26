"""
Test Script for AI Providers
Demonstrates how to use the provider factories and test each provider
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.providers.factories.stt_factory import STTFactory
from app.providers.factories.llm_factory import LLMFactory
from app.providers.factories.tts_factory import TTSFactory
from app.providers.factories.embeddings_factory import EmbeddingsFactory
from app.providers.base.llm_base import LLMMessage
from app.config import settings


async def test_stt_provider():
    """Test STT provider (requires actual audio file)"""
    print("\n" + "="*60)
    print("Testing STT Provider (Groq Whisper)")
    print("="*60)

    try:
        # Create STT provider using factory
        stt = STTFactory.create(
            provider_name="groq",
            # api_key will be loaded from config
        )

        print(f"✓ Created provider: {stt}")
        print(f"  Available providers: {STTFactory.get_available_providers()}")

        # Health check
        is_healthy = await stt.health_check()
        print(f"  Health check: {'✓ Healthy' if is_healthy else '✗ Unhealthy'}")

        # Note: Actual transcription requires audio file
        print("  Note: Actual transcription requires audio file (skipping)")

    except Exception as e:
        print(f"✗ Error: {str(e)}")


async def test_llm_provider():
    """Test LLM provider"""
    print("\n" + "="*60)
    print("Testing LLM Provider (Groq Llama)")
    print("="*60)

    try:
        # Create LLM provider using factory
        llm = LLMFactory.create(
            provider_name="groq",
            temperature=0.7,
            max_tokens=100,
        )

        print(f"✓ Created provider: {llm}")
        print(f"  Available providers: {LLMFactory.get_available_providers()}")

        # Health check
        is_healthy = await llm.health_check()
        print(f"  Health check: {'✓ Healthy' if is_healthy else '✗ Unhealthy'}")

        # Test generation
        if is_healthy:
            messages = [
                LLMMessage(role="system", content="You are a helpful assistant."),
                LLMMessage(role="user", content="Say hello in 5 words or less."),
            ]

            print("  Generating response...")
            response = await llm.generate(messages)
            print(f"  Response: {response.content}")
            print(f"  Tokens: {response.total_tokens}")

    except Exception as e:
        print(f"✗ Error: {str(e)}")


async def test_tts_provider():
    """Test TTS provider"""
    print("\n" + "="*60)
    print("Testing TTS Provider (ElevenLabs)")
    print("="*60)

    try:
        # Create TTS provider using factory
        tts = TTSFactory.create(
            provider_name="elevenlabs",
        )

        print(f"✓ Created provider: {tts}")
        print(f"  Available providers: {TTSFactory.get_available_providers()}")

        # Health check
        is_healthy = await tts.health_check()
        print(f"  Health check: {'✓ Healthy' if is_healthy else '✗ Unhealthy'}")

        # Test synthesis
        if is_healthy:
            print("  Synthesizing speech...")
            response = await tts.synthesize(
                text="Hello! This is a test of the text-to-speech system.",
                audio_format="mp3_44100_128"
            )
            print(f"  Audio generated: {len(response.audio_data)} bytes")
            print(f"  Format: {response.audio_format}, Sample rate: {response.sample_rate}Hz")

    except Exception as e:
        print(f"✗ Error: {str(e)}")


async def test_embeddings_provider():
    """Test Embeddings provider"""
    print("\n" + "="*60)
    print("Testing Embeddings Provider (Gemini)")
    print("="*60)

    try:
        # Create Embeddings provider using factory
        embeddings = EmbeddingsFactory.create(
            provider_name="gemini",
        )

        print(f"✓ Created provider: {embeddings}")
        print(f"  Available providers: {EmbeddingsFactory.get_available_providers()}")

        # Health check
        is_healthy = await embeddings.health_check()
        print(f"  Health check: {'✓ Healthy' if is_healthy else '✗ Unhealthy'}")

        # Test embedding generation
        if is_healthy:
            texts = [
                "This is a test document about AI voice agents.",
                "Voice agents can handle customer support calls.",
            ]

            print(f"  Generating embeddings for {len(texts)} texts...")
            response = await embeddings.embed(texts)
            print(f"  Embeddings generated: {len(response.embeddings)} vectors")
            print(f"  Dimensions: {response.dimensions}")
            print(f"  Sample vector (first 5 dims): {response.embeddings[0][:5]}")

    except Exception as e:
        print(f"✗ Error: {str(e)}")


async def main():
    """Run all provider tests"""
    print("\n" + "="*60)
    print("Voice Agent Platform - Provider Architecture Test")
    print("="*60)
    print(f"Environment: {settings.environment}")
    print(f"Configured providers:")
    print(f"  STT: {settings.stt_provider}")
    print(f"  LLM: {settings.llm_provider}")
    print(f"  TTS: {settings.tts_provider}")
    print(f"  Embeddings: {settings.embeddings_provider}")

    # Test each provider type
    await test_stt_provider()
    await test_llm_provider()
    await test_tts_provider()
    await test_embeddings_provider()

    print("\n" + "="*60)
    print("Provider Architecture Test Complete")
    print("="*60)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
