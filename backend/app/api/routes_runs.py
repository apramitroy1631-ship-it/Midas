# app/api/routes_runs.py
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from app.db import tenants as tenant_repo
from app.db.scoped import assets as assets_coll
from app.db.scoped import audit as audit_coll
from app.db.scoped import runs as runs_coll
from app.graph.runner import RunError, stream_run
from app.schemas.run import AssetResponse, AssetUpdate, RunDetail, RunRequest, RunSummary
from app.tenancy.auth import require_tenant

router = APIRouter(prefix="/v1", tags=["Runs"], dependencies=[Depends(require_tenant)])


def _sse(event: str, data: dict[str, Any]) -> dict[str, str]:
    return {"event": event, "data": json.dumps(data, default=str)}


def _summary(doc: dict[str, Any]) -> dict[str, Any]:
    out = dict(doc)
    out["id"] = str(doc["_id"])
    out.pop("_id", None)
    return out


@router.post("/runs/stream")
async def create_run_stream(payload: RunRequest, tenant: dict = Depends(require_tenant)) -> Any:
    """Start an autonomous campaign run and stream every agent step as SSE.

    Emits: start, step (one per node, including each revision cycle), done, error.
    Omit `goal` and the Campaign Director picks one from brand memory itself.
    """
    blocked = tenant_repo.quota_exceeded(tenant)
    if blocked:
        raise HTTPException(status_code=429, detail=blocked)

    async def generator():
        try:
            async for event_name, data in stream_run(
                brand_id=payload.brand_id,
                tenant=tenant,
                goal=payload.goal,
                audience=payload.target_audience,
                channels=payload.channels,
                budget=payload.budget,
                trigger=payload.trigger,
            ):
                yield _sse(event_name, data)
        except RunError as exc:
            yield _sse("error", {"message": str(exc)})
        except Exception as exc:  # noqa: BLE001 - the client must always learn why a run died
            yield _sse("error", {"message": str(exc)})

    return EventSourceResponse(generator())


@router.get("/runs", response_model=list[RunSummary])
def list_runs(
    brand_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> Any:
    query = {"brand_id": brand_id} if brand_id else {}
    docs = runs_coll.find(query, sort=[("created_at", -1)], limit=limit)
    return [RunSummary(**_summary(d)) for d in docs]


@router.get("/runs/{run_id}", response_model=RunDetail)
def get_run(run_id: str) -> Any:
    doc = runs_coll.find_one({"_id": run_id})
    if doc is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    return RunDetail(**_summary(doc))


@router.get("/assets", response_model=list[AssetResponse])
def list_assets(
    brand_id: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> Any:
    query: dict[str, Any] = {}
    if brand_id:
        query["brand_id"] = brand_id
    if channel:
        query["channel"] = channel
    if status:
        query["status"] = status
    docs = assets_coll.find(query, sort=[("created_at", -1)], limit=limit)
    return [AssetResponse(**_summary(d)) for d in docs]


@router.patch("/assets/{asset_id}", response_model=AssetResponse)
def update_asset(asset_id: str, payload: AssetUpdate) -> Any:
    """Persist edits made in the content canvas. Channel and status are not
    editable here — those come from the pipeline, not a manual rewrite."""
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    if changes and not assets_coll.update({"_id": asset_id}, changes):
        raise HTTPException(status_code=404, detail="Asset not found.")
    doc = assets_coll.find_one({"_id": asset_id})
    if doc is None:
        raise HTTPException(status_code=404, detail="Asset not found.")
    return AssetResponse(**_summary(doc))


@router.delete("/assets/{asset_id}", status_code=204)
def delete_asset(asset_id: str) -> None:
    if not assets_coll.delete({"_id": asset_id}):
        raise HTTPException(status_code=404, detail="Asset not found.")


@router.post("/assets/bulk-delete")
def bulk_delete_assets(payload: dict[str, list[str]]) -> Any:
    """`{"ids": [...]}` — deletes whichever of those ids belong to this
    tenant (ScopedCollection can't touch anyone else's) and reports how
    many actually existed, since a stale id in the list isn't an error."""
    ids = payload.get("ids") or []
    deleted = sum(1 for asset_id in ids if assets_coll.delete({"_id": asset_id}))
    return {"deleted": deleted, "requested": len(ids)}


@router.get("/audit")
def list_audit(limit: int = Query(default=100, ge=1, le=500)) -> Any:
    """Every autonomous decision this tenant's system has made, newest first."""
    return [_summary(d) for d in audit_coll.find(sort=[("created_at", -1)], limit=limit)]


@router.get("/stats")
def stats() -> Any:
    """Headline numbers for the dashboard."""
    runs = runs_coll.find(sort=[("created_at", -1)], limit=200)
    completed = [r for r in runs if r.get("status") in ("published", "published_partial", "review_pending")]
    scores = [r.get("goal_alignment_score") for r in completed if r.get("goal_alignment_score")]
    safety = [r.get("brand_safety_score") for r in completed if r.get("brand_safety_score")]
    revisions = [r.get("revisions", 0) for r in completed]
    spend = sum((r.get("usage") or {}).get("cost_usd", 0.0) for r in runs)

    return {
        "total_runs": len(runs),
        "published_runs": len(completed),
        "abandoned_runs": len([r for r in runs if r.get("status") == "abandoned"]),
        "failed_runs": len([r for r in runs if r.get("status") == "failed"]),
        "total_assets": assets_coll.count(),
        "self_directed_runs": len([r for r in runs if r.get("goal_origin") == "self-directed"]),
        "avg_goal_alignment": round(sum(scores) / len(scores), 1) if scores else None,
        "avg_brand_safety": round(sum(safety) / len(safety), 1) if safety else None,
        "avg_revisions": round(sum(revisions) / len(revisions), 2) if revisions else 0,
        "llm_spend_usd": round(spend, 4),
    }
