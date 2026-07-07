"""
MongoDB connection. Uses motor (async driver) so it plays nicely with FastAPI.

Local setup options:
  1. Install MongoDB Community locally (brew install mongodb-community on macOS)
     and use MONGO_URI=mongodb://localhost:27017
  2. Use a free MongoDB Atlas cluster and paste its connection string instead.

Either way, set MONGO_URI in a .env file — never hardcode it.
"""
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "app_tracker")

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(MONGO_URI)
    return _client


def get_database():
    return get_client()[DB_NAME]


def get_applications_collection():
    return get_database()["applications"]
