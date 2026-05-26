"""
Update Company Phone Number
Adds Twilio phone number to the company record
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

async def update_company_phone():
    """Update company with Twilio phone number"""

    # Connect to MongoDB
    mongodb_url = os.getenv("MONGODB_URL")
    mongodb_db_name = os.getenv("MONGODB_DB_NAME", "voice_agent_platform")

    client = AsyncIOMotorClient(mongodb_url)
    db = client[mongodb_db_name]

    try:
        # Get the company (assuming company ID is 1)
        company_id = 1
        twilio_phone = "+13082808634"

        # Update company with phone number
        result = await db.companies.update_one(
            {"_id": company_id},
            {
                "$set": {
                    "phone_number": twilio_phone,
                    "twilio_phone_number": twilio_phone
                }
            }
        )

        if result.matched_count > 0:
            print(f"✓ Successfully updated company {company_id}")
            print(f"  Phone number: {twilio_phone}")

            # Verify the update
            company = await db.companies.find_one({"_id": company_id})
            if company:
                print(f"\nCompany details:")
                print(f"  ID: {company['_id']}")
                print(f"  Name: {company.get('name', 'N/A')}")
                print(f"  Phone: {company.get('phone_number', 'N/A')}")
                print(f"  Status: {company.get('status', 'N/A')}")
        else:
            print(f"✗ Company {company_id} not found")

            # List all companies
            print("\nAvailable companies:")
            async for company in db.companies.find():
                print(f"  - ID: {company['_id']}, Name: {company.get('name', 'N/A')}")

    except Exception as e:
        print(f"✗ Error: {str(e)}")

    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(update_company_phone())
