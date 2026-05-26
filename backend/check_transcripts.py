"""
Check Call Transcripts in MongoDB
Verifies that call transcripts are being stored correctly
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
from datetime import datetime

# Load environment variables
load_dotenv()

async def check_recent_calls():
    """Check recent call transcripts in MongoDB"""

    # Connect to MongoDB
    mongodb_url = os.getenv("MONGODB_URL")
    mongodb_db_name = os.getenv("MONGODB_DB_NAME", "voice_agent_platform")

    client = AsyncIOMotorClient(mongodb_url)
    db = client[mongodb_db_name]

    try:
        print("=" * 70)
        print("CHECKING RECENT CALL TRANSCRIPTS")
        print("=" * 70)

        # Get most recent calls (last 5)
        calls = await db.calls.find().sort("created_at", -1).limit(5).to_list(length=5)

        if not calls:
            print("\n❌ No calls found in database")
            return

        for i, call in enumerate(calls, 1):
            print(f"\n{'='*70}")
            print(f"CALL #{i}")
            print(f"{'='*70}")
            print(f"Call SID: {call.get('call_sid')}")
            print(f"Company ID: {call.get('company_id')}")
            print(f"From: {call.get('caller_number')}")
            print(f"To: {call.get('called_number')}")
            print(f"Status: {call.get('status')}")
            print(f"Duration: {call.get('duration')}s")
            print(f"Created: {call.get('created_at')}")

            # Check transcript
            transcript = call.get('transcript', [])
            print(f"\nTranscript Messages: {len(transcript)}")

            if not transcript:
                print("⚠️  Transcript is EMPTY")
            else:
                print("\nConversation:")
                print("-" * 70)
                for msg in transcript:
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')
                    timestamp = msg.get('timestamp', '')

                    # Format role
                    role_label = "🤖 Agent" if role == "assistant" else "👤 User"

                    print(f"\n{role_label} ({timestamp}):")
                    print(f"  {content}")

                print("-" * 70)

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(check_recent_calls())
