# app/db/tenants.py
"""Tenant registry.

The one collection that is deliberately *not* tenant-scoped, because it is the
thing that defines the scopes. Keys are stored as SHA-256 hashes; the raw key
is shown exactly once, at creation.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

from app.db.mongo import raw
from app.db.scoped import utcnow

_KEY_PREFIX = "bx_live_"


def hash_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_key() -> tuple[str, str, str]:
    """Return (raw_key, hash, display_prefix)."""
    raw_key = _KEY_PREFIX + secrets.token_urlsafe(32)
    return raw_key, hash_key(raw_key), raw_key[: len(_KEY_PREFIX) + 6] + "..."


def _period() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _to_response(doc: dict[str, Any]) -> dict[str, Any]:
    out = dict(doc)
    out["id"] = str(doc["_id"])
    out.pop("_id", None)
    out.pop("api_key_hash", None)
    return out


def create(data: dict[str, Any]) -> tuple[dict[str, Any], str]:
    raw_key, key_hash, prefix = generate_key()
    tenant_id = str(uuid.uuid4())
    slug = (data.get("slug") or data["name"]).lower().replace(" ", "-")[:40]

    doc = {
        "_id": tenant_id,
        "name": data["name"],
        "slug": slug,
        "status": "active",
        "api_key_hash": key_hash,
        "api_key_prefix": prefix,
        "policy": data.get("policy") or {},
        "autopilot": data.get("autopilot") or {},
        "limits": data.get("limits") or {},
        "usage": {"runs_this_period": 0, "spend_usd": 0.0, "period": _period()},
        "model_overrides": {},
        "created_at": utcnow(),
        "updated_at": utcnow(),
    }
    raw("tenants").insert_one(doc)
    return _to_response(doc), raw_key


def get(tenant_id: str) -> dict[str, Any] | None:
    doc = raw("tenants").find_one({"_id": tenant_id})
    return _to_response(doc) if doc else None


def get_by_api_key(api_key: str) -> dict[str, Any] | None:
    doc = raw("tenants").find_one({"api_key_hash": hash_key(api_key)})
    return _to_response(doc) if doc else None


def list_all() -> list[dict[str, Any]]:
    return [_to_response(d) for d in raw("tenants").find({}).sort("created_at", 1)]


def update(tenant_id: str, changes: dict[str, Any]) -> dict[str, Any] | None:
    payload = {k: v for k, v in changes.items() if v is not None}
    if not payload:
        return get(tenant_id)
    payload["updated_at"] = utcnow()
    raw("tenants").update_one({"_id": tenant_id}, {"$set": payload})
    return get(tenant_id)


def record_run(tenant_id: str, cost_usd: float = 0.0) -> None:
    """Increment usage counters, rolling the period over when the month changes."""
    doc = raw("tenants").find_one({"_id": tenant_id})
    if not doc:
        return
    usage = doc.get("usage") or {}
    period = _period()
    if usage.get("period") != period:
        usage = {"runs_this_period": 0, "spend_usd": 0.0, "period": period}
    usage["runs_this_period"] = usage.get("runs_this_period", 0) + 1
    usage["spend_usd"] = round(usage.get("spend_usd", 0.0) + cost_usd, 4)
    raw("tenants").update_one(
        {"_id": tenant_id}, {"$set": {"usage": usage, "updated_at": utcnow()}}
    )


def quota_exceeded(tenant: dict[str, Any]) -> str | None:
    """Return a human-readable reason if this tenant may not start a run."""
    if tenant.get("status") != "active":
        return "Tenant is " + str(tenant.get("status")) + "."
    limits = tenant.get("limits") or {}
    usage = tenant.get("usage") or {}
    if usage.get("period") != _period():
        return None  # fresh period; counters reset on the next record_run
    quota = limits.get("monthly_run_quota")
    if quota is not None and usage.get("runs_this_period", 0) >= quota:
        return "Monthly run quota reached (" + str(quota) + " runs)."
    budget = limits.get("monthly_budget_usd")
    if budget is not None and usage.get("spend_usd", 0.0) >= budget:
        return "Monthly budget reached ($" + str(budget) + ")."
    return None
