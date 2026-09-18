# app/db/scoped.py
"""Tenant-scoped collection wrapper.

This is where multi-tenant isolation is actually enforced. Every filter is
intersected with the active tenant before it reaches Mongo, and every inserted
document is stamped with it. A caller cannot widen the scope: passing
`{"tenant_id": "someone-else"}` is overwritten, not merged, so a crafted filter
cannot escape the tenant.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from pymongo.collection import Collection

from app.db.mongo import get_db
from app.tenancy.context import current_tenant


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class ScopedCollection:
    """A pymongo Collection that can only ever see one tenant's documents."""

    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def _coll(self) -> Collection:
        return get_db()[self._name]

    # -- scoping ----------------------------------------------------------
    def _scope(self, query: Mapping[str, Any] | None = None) -> dict[str, Any]:
        scoped = dict(query or {})
        scoped["tenant_id"] = current_tenant()  # last write wins — cannot be overridden
        return scoped

    def _stamp(self, doc: Mapping[str, Any]) -> dict[str, Any]:
        stamped = dict(doc)
        stamped["tenant_id"] = current_tenant()
        stamped.setdefault("created_at", utcnow())
        stamped["updated_at"] = utcnow()
        return stamped

    # -- reads ------------------------------------------------------------
    def find_one(self, query: Mapping[str, Any] | None = None, **kw) -> dict[str, Any] | None:
        return self._coll.find_one(self._scope(query), **kw)

    def find(
        self,
        query: Mapping[str, Any] | None = None,
        *,
        sort: list[tuple[str, int]] | None = None,
        limit: int = 0,
        **kw,
    ) -> list[dict[str, Any]]:
        cursor = self._coll.find(self._scope(query), **kw)
        if sort:
            cursor = cursor.sort(sort)
        if limit:
            cursor = cursor.limit(limit)
        return list(cursor)

    def count(self, query: Mapping[str, Any] | None = None) -> int:
        return self._coll.count_documents(self._scope(query))

    # -- writes -----------------------------------------------------------
    def insert(self, doc: Mapping[str, Any]) -> dict[str, Any]:
        stamped = self._stamp(doc)
        self._coll.insert_one(stamped)
        return stamped

    def insert_many(self, docs: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
        stamped = [self._stamp(d) for d in docs]
        if stamped:
            self._coll.insert_many(stamped)
        return stamped

    def update(self, query: Mapping[str, Any], changes: Mapping[str, Any]) -> bool:
        payload = dict(changes)
        payload["updated_at"] = utcnow()
        payload.pop("tenant_id", None)  # a document can never be moved between tenants
        result = self._coll.update_one(self._scope(query), {"$set": payload})
        return result.matched_count > 0

    def push(self, query: Mapping[str, Any], field: str, value: Any) -> bool:
        result = self._coll.update_one(
            self._scope(query),
            {"$push": {field: value}, "$set": {"updated_at": utcnow()}},
        )
        return result.matched_count > 0

    def delete(self, query: Mapping[str, Any]) -> int:
        return self._coll.delete_one(self._scope(query)).deleted_count


brands = ScopedCollection("brands")
runs = ScopedCollection("runs")
assets = ScopedCollection("assets")
audit = ScopedCollection("audit")
scheduled_campaigns = ScopedCollection("scheduled_campaigns")
