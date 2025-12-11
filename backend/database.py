"""
MongoDB Database Connection Service

This module handles the connection to MongoDB using motor (async driver).
"""

import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection settings
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("MONGODB_DATABASE", "prompt_to_animate")

# Global client instance
_client: AsyncIOMotorClient = None


async def get_database():
    """
    Get the MongoDB database instance.
    Creates a connection if one doesn't exist.
    """
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(MONGODB_URI)
    return _client[DATABASE_NAME]


async def get_chats_collection():
    """Get the chats collection."""
    db = await get_database()
    return db["chats"]


async def close_database_connection():
    """Close the MongoDB connection."""
    global _client
    if _client is not None:
        _client.close()
        _client = None


# Connection event handlers for FastAPI
async def connect_to_mongo():
    """Called on application startup."""
    global _client
    _client = AsyncIOMotorClient(MONGODB_URI)
    # Verify connection
    try:
        await _client.admin.command('ping')
        print(f"✅ Connected to MongoDB: {DATABASE_NAME}")
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        raise


async def close_mongo_connection():
    """Called on application shutdown."""
    global _client
    if _client:
        _client.close()
        print("🔌 MongoDB connection closed")
