"""
Script to create a superadmin user directly in MongoDB
Run this script once to create the initial superadmin account

Usage:
    python create_superadmin.py
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from app.core.security import get_password_hash
from app.config import settings
from app.utils.counter import Counter


async def create_superadmin():
    """Create a superadmin user in MongoDB"""

    print("=" * 60)
    print("Creating SuperAdmin Account")
    print("=" * 60)

    # Get superadmin details from user input
    email = input("\nEnter superadmin email: ").strip()
    password = input("Enter superadmin password (min 8 chars, uppercase, lowercase, digit): ").strip()
    full_name = input("Enter superadmin full name: ").strip()

    # Validate inputs
    if not email or not password or not full_name:
        print("\n❌ Error: All fields are required")
        return

    if len(password) < 8:
        print("\n❌ Error: Password must be at least 8 characters")
        return

    if not any(c.isupper() for c in password):
        print("\n❌ Error: Password must contain at least one uppercase letter")
        return

    if not any(c.islower() for c in password):
        print("\n❌ Error: Password must contain at least one lowercase letter")
        return

    if not any(c.isdigit() for c in password):
        print("\n❌ Error: Password must contain at least one digit")
        return

    # Connect to MongoDB
    print(f"\nConnecting to MongoDB at {settings.mongodb_url}...")
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.mongodb_db_name]
    users_collection = db.users

    # Check if superadmin already exists
    existing_superadmin = await users_collection.find_one({"role": "superadmin"})
    if existing_superadmin:
        print(f"\n⚠️  Warning: A superadmin already exists: {existing_superadmin['email']}")
        confirm = input("Do you want to create another superadmin? (yes/no): ").strip().lower()
        if confirm != "yes":
            print("\n❌ Cancelled")
            client.close()
            return

    # Check if email already exists
    existing_user = await users_collection.find_one({"email": email})
    if existing_user:
        print(f"\n❌ Error: User with email {email} already exists")
        client.close()
        return

    # Hash password
    hashed_password = get_password_hash(password)

    # Generate user ID using counter
    counter = Counter(db)
    user_id = await counter.get_next_sequence("user")

    # Create superadmin document with sequential _id
    superadmin_doc = {
        "_id": user_id,
        "email": email,
        "hashed_password": hashed_password,
        "full_name": full_name,
        "role": "superadmin",
        "company_id": None,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    # Insert superadmin
    await users_collection.insert_one(superadmin_doc)

    print("\n" + "=" * 60)
    print("✅ SuperAdmin created successfully!")
    print("=" * 60)
    print(f"User ID: {user_id}")
    print(f"Email: {email}")
    print(f"Full Name: {full_name}")
    print(f"Role: superadmin")
    print("=" * 60)
    print("\nYou can now login with these credentials at /login")
    print("=" * 60)

    client.close()


if __name__ == "__main__":
    asyncio.run(create_superadmin())
