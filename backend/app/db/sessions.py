# app/db/sessions.py
"""Login sessions.

Issued on a successful email/password login and sent back by the console as
the same X-API-Key header a tenant key would use — see app/tenancy/auth.py.
The distinct "sess_" prefix (vs. a tenant key's "bx_live_") is what lets a
single header carry either kind of credential without ambiguity.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.db.mongo import raw
from app.db.scoped import utcnow

PREFIX = "sess_"
_TTL_DAYS = 30


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create(tenant_id: str, user_id: str) -> str:
    token = PREFIX + secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(days=_TTL_DAYS)).isoformat(
        timespec="seconds"
    ).replace("+00:00", "Z")
    doc = {
        "_id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "user_id": user_id,
        "token_hash": _hash(token),
        "created_at": utcnow(),
        "expires_at": expires_at,
    }
    raw("sessions").insert_one(doc)
    return token


def resolve_tenant_id(token: str) -> str | None:
    doc = raw("sessions").find_one({"token_hash": _hash(token)})
    if not doc:
        return None
    if doc["expires_at"] < utcnow():
        return None
    return doc["tenant_id"]


def resolve_user_id(token: str) -> str | None:
    doc = raw("sessions").find_one({"token_hash": _hash(token)})
    if not doc:
        return None
    if doc["expires_at"] < utcnow():
        return None
    return doc["user_id"]


def revoke(token: str) -> bool:
    result = raw("sessions").delete_one({"token_hash": _hash(token)})
    return result.deleted_count > 0
