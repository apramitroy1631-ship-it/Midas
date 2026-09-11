# app/db/repositories/brand_repo.py
from datetime import datetime, timezone
from typing import Any

from app.db.mongodb import get_brands_collection


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _doc_to_response(doc: dict[str, Any]) -> dict[str, Any]:
    """Convert MongoDB document to API response shape."""
    memory = doc.get("memory") or {}
    return {
        "id": str(doc["_id"]),
        "name": doc.get("name", ""),
        "description": doc.get("description", ""),
        "industry": doc.get("industry", ""),
        "tone": doc.get("tone", ""),
        "usp": doc.get("usp", ""),
        "target_audience": doc.get("target_audience", ""),
        "memory": memory,
        "created_at": doc.get("created_at", ""),
        "updated_at": doc.get("updated_at", ""),
    }


def _to_plain_dict(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, dict):
        return {k: _to_plain_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_plain_dict(x) for x in obj]
    return obj


def create(data: dict[str, Any]) -> dict[str, Any]:
    """Persist new brand in MongoDB with full document shape."""
    brand_id = data.get("id")
    if not brand_id:
        return data
    now = _now_iso()
    memory = {
        "past_campaigns": [],
        "latest_insights": data.get("latest_insights", []),
        "brand_guidelines": _to_plain_dict(data.get("brand_guidelines") or {}),
    }
    doc = {
        "_id": brand_id,
        "name": data.get("name", ""),
        "description": data.get("description", ""),
        "industry": data.get("industry", ""),
        "tone": data.get("tone", ""),
        "usp": data.get("usp", ""),
        "target_audience": data.get("target_audience", ""),
        "memory": memory,
        "created_at": now,
        "updated_at": now,
    }
    coll = get_brands_collection()
    coll.insert_one(doc)
    return _doc_to_response(doc)


def list_all() -> list[dict[str, Any]]:
    """List all brands; returns id and name only."""
    coll = get_brands_collection()
    cursor = coll.find({}, projection=["_id", "name"])
    return [{"id": str(d["_id"]), "name": d.get("name", "")} for d in cursor]


def get_by_id(brand_id: str) -> dict[str, Any] | None:
    """Load full brand document from MongoDB."""
    coll = get_brands_collection()
    doc = coll.find_one({"_id": brand_id})
    if doc is None:
        return None
    return _doc_to_response(doc)


def update(brand_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
    """Update brand in MongoDB. Merges memory subfields with existing memory."""
    coll = get_brands_collection()
    doc = coll.find_one({"_id": brand_id})
    if doc is None:
        return None
    now = _now_iso()
    set_fields: dict[str, Any] = {"updated_at": now}
    for key in ("name", "description", "industry", "tone", "usp", "target_audience"):
        if key in data and data[key] is not None:
            set_fields[key] = data[key]
    memory = dict(doc.get("memory") or {})
    if "brand_guidelines" in data and data["brand_guidelines"] is not None:
        memory["brand_guidelines"] = _to_plain_dict(data["brand_guidelines"])
    if "latest_insights" in data and data["latest_insights"] is not None:
        memory["latest_insights"] = data["latest_insights"]
    set_fields["memory"] = memory
    coll.update_one({"_id": brand_id}, {"$set": set_fields})
    return get_by_id(brand_id)


def delete(brand_id: str) -> bool:
    """Remove brand from MongoDB."""
    coll = get_brands_collection()
    result = coll.delete_one({"_id": brand_id})
    return result.deleted_count > 0
