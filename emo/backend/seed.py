"""Seed default admin users for local development."""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta

import bcrypt
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

USERS = [
    {"email": "hugo@example.com", "password": "emo-test-2026", "name": "Hugo"},
    {"email": "huglostalatac@gmail.com", "password": "emo2026", "name": "Hugo"},
]


async def main():
    import os

    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    for u in USERS:
        existing = await db.users.find_one({"email": u["email"]})
        if existing:
            print(f"exists: {u['email']}")
            user_id = existing["user_id"]
        else:
            user_id = f"user_{uuid.uuid4().hex[:12]}"
            pwd_hash = bcrypt.hashpw(u["password"].encode(), bcrypt.gensalt()).decode()
            await db.users.insert_one(
                {
                    "user_id": user_id,
                    "email": u["email"],
                    "name": u["name"],
                    "picture": None,
                    "auth_provider": "password",
                    "password_hash": pwd_hash,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            print(f"created: {u['email']}")

        await db.licenses.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "paid": True,
                    "status": "active",
                    "interval": "lifetime",
                    "paid_at": datetime.now(timezone.utc).isoformat(),
                },
                "$setOnInsert": {
                    "user_id": user_id,
                    "daily_count": 0,
                    "daily_day": "",
                },
            },
            upsert=True,
        )

    client.close()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
