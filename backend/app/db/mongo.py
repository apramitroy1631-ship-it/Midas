# app/db/mongo.py
from __future__ import annotations

import logging

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from app.core.settings import settings

logger = logging.getLogger("db.mongo")

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
    return _client


def get_db() -> Database:
    return get_client()[settings.mongodb_db_name]


def raw(name: str) -> Collection:
    """Unscoped collection handle. Only the tenant registry itself may use this."""
    return get_db()[name]


def ensure_indexes() -> None:
    """Create the compound (tenant_id, ...) indexes every scoped query relies on."""
    db = get_db()
    db["tenants"].create_index([("api_key_hash", ASCENDING)], unique=True)
    db["tenants"].create_index([("slug", ASCENDING)], unique=True)

    db["users"].create_index([("email", ASCENDING)], unique=True)
    db["sessions"].create_index([("token_hash", ASCENDING)], unique=True)

    for name in ("brands", "runs", "assets", "audit"):
        db[name].create_index([("tenant_id", ASCENDING), ("created_at", DESCENDING)])

    db["runs"].create_index([("tenant_id", ASCENDING), ("brand_id", ASCENDING)])
    db["assets"].create_index([("tenant_id", ASCENDING), ("brand_id", ASCENDING)])
    logger.info("Mongo indexes ensured on db=%s", settings.mongodb_db_name)
