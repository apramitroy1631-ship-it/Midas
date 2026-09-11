# app/db/mongodb.py
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from app.core.settings import settings

_client: MongoClient | None = None


def get_client() -> MongoClient:
    """Lazy MongoDB client singleton."""
    global _client
    if _client is None:
        _client = MongoClient(settings.mongodb_uri)
    return _client


def get_database() -> Database:
    return get_client()[settings.mongodb_db_name]


def get_brands_collection() -> Collection:
    """Collection for all brand-related data (name, context, memory)."""
    return get_database()["brands"]


def get_campaigns_collection() -> Collection:
    """Collection for campaign runs (by brand, full graph result + metadata)."""
    return get_database()["campaigns"]
