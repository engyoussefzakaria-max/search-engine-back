from motor.motor_asyncio import AsyncIOMotorClient
from core.config import settings

class MongoDB:
    client: AsyncIOMotorClient = None
    database = None

mongodb = MongoDB()


async def connect_to_mongo():
    mongodb.client = AsyncIOMotorClient(settings.MONGO_URI)

    # Select database
    mongodb.database = mongodb.client[settings.MONGO_DB_NAME]

    # Optional: test connection
    await mongodb.client.admin.command("ping")

    print(f"✅ Connected to MongoDB: {settings.MONGO_DB_NAME}")


async def close_mongo_connection():
    if mongodb.client:
        mongodb.client.close()
        print("❌ MongoDB connection closed")


def get_db():
    return mongodb.database