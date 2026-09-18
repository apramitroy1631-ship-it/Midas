# app/api/routes_logs.py
"""Developer log viewer. Logs are operational, cross-tenant data (see app/core/log_capture.py),
not tenant-owned business data, so this reads the unscoped collection behind ordinary
tenant auth rather than ScopedCollection - any authenticated caller sees the whole feed."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.db.mongo import raw
from app.tenancy.auth import require_tenant

router = APIRouter(prefix="/v1/logs", tags=["Logs"], dependencies=[Depends(require_tenant)])


@router.get("")
def list_logs(
    category: list[str] | None = Query(default=None),
    level: list[str] | None = Query(default=None),
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
    limit: int = Query(default=300, le=1000),
) -> Any:
    query: dict[str, Any] = {}
    if category:
        query["category"] = {"$in": category}
    if level:
        query["level"] = {"$in": level}
    created_at: dict[str, datetime] = {}
    if since:
        created_at["$gte"] = since if since.tzinfo else since.replace(tzinfo=timezone.utc)
    if until:
        created_at["$lte"] = until if until.tzinfo else until.replace(tzinfo=timezone.utc)
    if created_at:
        query["created_at"] = created_at

    coll = raw("logs")
    docs = list(coll.find(query).sort("created_at", -1).limit(limit))
    entries = []
    for d in docs:
        entries.append(
            {
                "id": str(d["_id"]),
                "created_at": d["created_at"],
                "category": d.get("category", ""),
                "level": d.get("level", "INFO"),
                "message": d.get("message", ""),
            }
        )

    categories = sorted(coll.distinct("category"))
    levels = sorted(coll.distinct("level"))
    return {"entries": entries, "categories": categories, "levels": levels}
