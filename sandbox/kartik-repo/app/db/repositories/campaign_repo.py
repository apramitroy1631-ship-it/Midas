# app/db/repositories/campaign_repo.py
from datetime import datetime, timezone
from typing import Any

from app.db.mongodb import get_campaigns_collection


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def create(data: dict[str, Any]) -> dict[str, Any]:
    """
    Save a full campaign document.
    Expects at least: campaign_id, brand_id, status; plus any graph result fields
    (research, strategy, content, qa_report, analytics, brand_context, goal, target_audience, budget).
    """
    campaign_id = data.get("campaign_id") or data.get("id")
    if not campaign_id:
        return data
    now = _now_iso()
    doc = {
        "_id": campaign_id,
        "brand_id": data.get("brand_id", ""),
        "brand_name": data.get("brand_context", {}).get("name", ""),
        "status": data.get("status", ""),
        "goal": data.get("goal", ""),
        "target_audience": data.get("target_audience", ""),
        "budget": data.get("budget"),
        "research": data.get("research"),
        "strategy": data.get("strategy"),
        "content": data.get("content"),
        "qa_report": data.get("qa_report"),
        "analytics": data.get("analytics"),
        "created_at": now,
        "updated_at": now,
    }
    coll = get_campaigns_collection()
    coll.insert_one(doc)
    return _doc_to_response(doc)


def _doc_to_response(doc: dict[str, Any]) -> dict[str, Any]:
    """Convert MongoDB document to response shape (id instead of _id)."""
    out = dict(doc)
    out["id"] = str(doc["_id"])
    out.pop("_id", None)
    return out


def list_all(brand_id: str | None = None) -> list[dict[str, Any]]:
    """Return all campaigns, optionally filtered by brand_id. Newest first."""
    coll = get_campaigns_collection()
    query = {"brand_id": brand_id} if brand_id else {}
    cursor = coll.find(query).sort("created_at", -1)
    return [_doc_to_response(d) for d in cursor]


def list_by_brand_id(brand_id: str) -> list[dict[str, Any]]:
    """Return all campaigns for the given brand_id."""
    return list_all(brand_id=brand_id)


def get_by_id(brand_id: str, campaign_id: str) -> dict[str, Any] | None:
    """Return one campaign by campaign_id, or None if not found."""
    coll = get_campaigns_collection()
    doc = coll.find_one({"_id": campaign_id})
    if doc is None:
        return None
    return _doc_to_response(doc)


def delete(campaign_id: str) -> bool:
    """Remove campaign by campaign_id. Returns True if deleted."""
    coll = get_campaigns_collection()
    result = coll.delete_one({"_id": campaign_id})
    return result.deleted_count > 0
