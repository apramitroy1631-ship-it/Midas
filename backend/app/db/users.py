# app/db/users.py
"""Login accounts for the console.

Deliberately separate from the tenant's own API key: a tenant key is a
service credential (shared, never rotated per-person); a user account is a
person's own login. Not tenant-scoped via ScopedCollection for the same
reason app/db/tenants.py isn't — resolving *which* tenant a login belongs to
is the whole point, so it can't depend on already knowing the tenant.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import uuid
from typing import Any

from app.db.mongo import raw
from app.db.scoped import utcnow

_PBKDF2_ROUNDS = 200_000


def _hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ROUNDS).hex()


def _to_response(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": doc["_id"],
        "tenant_id": doc["tenant_id"],
        "email": doc["email"],
        "phone": doc.get("phone"),
        "created_at": doc["created_at"],
    }


def create(tenant_id: str, email: str, password: str, phone: str | None = None) -> dict[str, Any]:
    salt = os.urandom(16)
    doc = {
        "_id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "email": email.strip().lower(),
        "phone": (phone or "").strip() or None,
        "password_hash": _hash_password(password, salt),
        "password_salt": salt.hex(),
        "created_at": utcnow(),
    }
    raw("users").insert_one(doc)
    return _to_response(doc)


def get_by_email(email: str) -> dict[str, Any] | None:
    return raw("users").find_one({"email": email.strip().lower()})


def verify_password(user: dict[str, Any], password: str) -> bool:
    salt = bytes.fromhex(user["password_salt"])
    candidate = _hash_password(password, salt)
    return hmac.compare_digest(candidate, user["password_hash"])


def list_for_tenant(tenant_id: str) -> list[dict[str, Any]]:
    return [_to_response(d) for d in raw("users").find({"tenant_id": tenant_id}).sort("created_at", 1)]
