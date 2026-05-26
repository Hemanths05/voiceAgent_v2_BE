#!/usr/bin/env python3
"""
Seed Superadmin User
Creates the initial superadmin user for the platform

Usage:
    python scripts/seed_superadmin.py --email admin@example.com --password securepass123 --name "Super Admin"

Or use environment variables:
    SUPERADMIN_EMAIL=admin@example.com \
    SUPERADMIN_PASSWORD=securepass123 \
    SUPERADMIN_NAME="Super Admin" \
    python scripts/seed_superadmin.py
"""
import asyncio
import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from app.config import settings
from app.core.security import get_password_hash
from app.utils.validators import Validators
from app.core.logging_config import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


async def create_superadmin(email: str, password: str, name: str) -> bool:
    """
    Create superadmin user

    Args:
        email: Superadmin email
        password: Superadmin password
        name: Superadmin name

    Returns:
        True if successful, False otherwise
    """
    try:
        # Validate inputs
        logger.info("Validating inputs...")
        email = Validators.validate_email(email)

        if len(password) < 8:
            logger.error("Password must be at least 8 characters long")
            return False

        # Connect to MongoDB
        logger.info(f"Connecting to MongoDB: {settings.mongodb_url}")
        client = AsyncIOMotorClient(settings.mongodb_url)
        db = client[settings.mongodb_db_name]

        # Check if superadmin already exists
        existing_user = await db.users.find_one({"email": email})
        if existing_user:
            logger.warning(f"User with email {email} already exists!")
            choice = input("Do you want to update this user? (yes/no): ")
            if choice.lower() != "yes":
                logger.info("Aborted.")
                client.close()
                return False

            # Update existing user
            hashed_password = get_password_hash(password)
            await db.users.update_one(
                {"email": email},
                {
                    "$set": {
                        "password_hash": hashed_password,
                        "name": name,
                        "role": "superadmin",
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            logger.info(f"✓ Updated existing user: {email}")

        else:
            # Create new superadmin
            hashed_password = get_password_hash(password)

            user_doc = {
                "email": email,
                "password_hash": hashed_password,
                "name": name,
                "role": "superadmin",
                "company_id": None,
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            result = await db.users.insert_one(user_doc)
            logger.info(f"✓ Created superadmin user: {email} (ID: {result.inserted_id})")

        # Create indexes if they don't exist
        await db.users.create_index("email", unique=True)
        logger.info("✓ Ensured database indexes")

        # Close connection
        client.close()

        logger.info("=" * 60)
        logger.info("Superadmin user created successfully!")
        logger.info(f"Email: {email}")
        logger.info(f"Name: {name}")
        logger.info("=" * 60)
        logger.info("\nYou can now login at: " + settings.public_url + "/docs")
        logger.info("\nNext steps:")
        logger.info("1. Start the server: uvicorn app.main:app --reload")
        logger.info("2. Login with the credentials above")
        logger.info("3. Create companies via POST /api/superadmin/companies")
        logger.info("4. Create admin users for companies")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"Error creating superadmin: {str(e)}", exc_info=True)
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Create initial superadmin user for Voice Agent Platform"
    )

    parser.add_argument(
        "--email",
        type=str,
        default=os.getenv("SUPERADMIN_EMAIL"),
        help="Superadmin email address"
    )

    parser.add_argument(
        "--password",
        type=str,
        default=os.getenv("SUPERADMIN_PASSWORD"),
        help="Superadmin password (min 8 characters)"
    )

    parser.add_argument(
        "--name",
        type=str,
        default=os.getenv("SUPERADMIN_NAME", "Super Admin"),
        help="Superadmin name"
    )

    args = parser.parse_args()

    # Validate required arguments
    if not args.email:
        logger.error("Email is required. Use --email or set SUPERADMIN_EMAIL environment variable")
        sys.exit(1)

    if not args.password:
        logger.error("Password is required. Use --password or set SUPERADMIN_PASSWORD environment variable")
        sys.exit(1)

    # Print configuration
    print("=" * 60)
    print("Voice Agent Platform - Superadmin Setup")
    print("=" * 60)
    print(f"Email: {args.email}")
    print(f"Name: {args.name}")
    print(f"MongoDB: {settings.mongodb_url}")
    print(f"Database: {settings.mongodb_db_name}")
    print("=" * 60)

    # Confirm
    confirm = input("\nProceed with creating superadmin? (yes/no): ")
    if confirm.lower() != "yes":
        print("Aborted.")
        sys.exit(0)

    # Create superadmin
    success = asyncio.run(create_superadmin(args.email, args.password, args.name))

    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
