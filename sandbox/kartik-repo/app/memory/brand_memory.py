# app/memory/brand_memory.py
from typing import Any

from app.db.mongodb import get_brands_collection


def get_memory(brand_id: str) -> dict[str, Any]:
    """Return memory for brand from MongoDB."""
    coll = get_brands_collection()
    doc = coll.find_one({"_id": brand_id}, projection=["memory"])
    if doc is None:
        return {}
    return dict(doc.get("memory") or {})


def set_memory(brand_id: str, memory: dict[str, Any]) -> None:
    """Set memory for brand in MongoDB (replaces memory field)."""
    coll = get_brands_collection()
    # Ensure document exists (e.g. created by brand_repo first)
    coll.update_one(
        {"_id": brand_id},
        {"$set": {"memory": memory}},
        upsert=False,
    )


def delete_memory(brand_id: str) -> None:
    """Clear memory for brand in MongoDB (set to empty dict)."""
    coll = get_brands_collection()
    coll.update_one(
        {"_id": brand_id},
        {"$set": {"memory": {}}},
    )
