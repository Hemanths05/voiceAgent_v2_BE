"""
Update Agent TTS Provider
Changes TTS provider from google to elevenlabs
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

async def update_agent_tts():
    """Update agent config TTS provider to elevenlabs"""

    # Connect to MongoDB
    mongodb_url = os.getenv("MONGODB_URL")
    mongodb_db_name = os.getenv("MONGODB_DB_NAME", "voice_agent_platform")

    client = AsyncIOMotorClient(mongodb_url)
    db = client[mongodb_db_name]

    try:
        # Update all agent configs to use elevenlabs
        result = await db.agent_configs.update_many(
            {"tts_provider": "google"},
            {
                "$set": {
                    "tts_provider": "elevenlabs",
                    "tts_model": "eleven_monolingual_v1",
                    "tts_voice": "XFyHddC2zKKgLBooDuhH"  # Default ElevenLabs voice
                }
            }
        )

        print(f"✓ Updated {result.modified_count} agent config(s)")

        # Verify the update
        configs = await db.agent_configs.find().to_list(length=10)
        for config in configs:
            print(f"\nAgent Config (Company {config.get('company_id')}):")
            print(f"  STT Provider: {config.get('stt_provider')}")
            print(f"  LLM Provider: {config.get('llm_provider')}")
            print(f"  TTS Provider: {config.get('tts_provider')}")
            print(f"  TTS Voice: {config.get('tts_voice')}")

    except Exception as e:
        print(f"✗ Error: {str(e)}")

    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(update_agent_tts())
