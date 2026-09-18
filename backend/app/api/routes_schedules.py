# app/api/routes_schedules.py
from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from app.db.scoped import brands as brands_coll
from app.db.scoped import scheduled_campaigns as schedules_coll
from app.schemas.schedule import ScheduleCreate, ScheduleResponse
from app.tenancy.auth import require_tenant

router = APIRouter(prefix="/v1/schedules", tags=["Schedules"], dependencies=[Depends(require_tenant)])


def _to_response(doc: dict[str, Any]) -> ScheduleResponse:
    out = dict(doc)
    out["id"] = str(doc["_id"])
    out.pop("_id", None)
    return ScheduleResponse(**out)


@router.get("", response_model=list[ScheduleResponse])
def list_schedules() -> Any:
    return [_to_response(d) for d in schedules_coll.find(sort=[("created_at", -1)])]


@router.post("", response_model=ScheduleResponse, status_code=201)
def create_schedule(payload: ScheduleCreate) -> Any:
    brand = brands_coll.find_one({"_id": payload.brand_id})
    if brand is None:
        raise HTTPException(status_code=404, detail="Brand not found.")

    try:
        start = date.fromisoformat(payload.start_date)
        end = date.fromisoformat(payload.end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="start_date/end_date must be YYYY-MM-DD.")
    if end < start:
        raise HTTPException(status_code=400, detail="end_date can't be before start_date.")
    if start < date.today():
        raise HTTPException(status_code=400, detail="start_date can't be in the past.")
    if not payload.weekdays or any(d < 0 or d > 6 for d in payload.weekdays):
        raise HTTPException(status_code=400, detail="Pick at least one weekday (0=Monday..6=Sunday).")

    doc = schedules_coll.insert(
        {
            "_id": str(uuid.uuid4()),
            "brand_id": payload.brand_id,
            "brand_name": brand.get("name", ""),
            "goal": payload.goal,
            "target_audience": payload.target_audience,
            "budget": payload.budget,
            "channels": payload.channels,
            "start_date": payload.start_date,
            "end_date": payload.end_date,
            "weekdays": sorted(set(payload.weekdays)),
            "active": True,
            "last_run_date": None,
        }
    )
    return _to_response(doc)


@router.delete("/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: str) -> None:
    if not schedules_coll.delete({"_id": schedule_id}):
        raise HTTPException(status_code=404, detail="Schedule not found.")


@router.patch("/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(schedule_id: str, active: bool = Body(embed=True)) -> Any:
    if not schedules_coll.update({"_id": schedule_id}, {"active": active}):
        raise HTTPException(status_code=404, detail="Schedule not found.")
    return _to_response(schedules_coll.find_one({"_id": schedule_id}))
