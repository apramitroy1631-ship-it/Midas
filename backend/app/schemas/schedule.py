# app/schemas/schedule.py
from __future__ import annotations

from pydantic import BaseModel, Field


class ScheduleCreate(BaseModel):
    brand_id: str
    goal: str | None = None
    target_audience: str | None = None
    budget: float = 0
    channels: list[str] | None = None
    start_date: str  # "YYYY-MM-DD", today or later
    end_date: str  # "YYYY-MM-DD", on or after start_date
    weekdays: list[int] = Field(default_factory=list)  # 0=Monday .. 6=Sunday


class ScheduleResponse(BaseModel):
    id: str
    tenant_id: str = ""
    brand_id: str
    brand_name: str = ""
    goal: str | None = None
    target_audience: str | None = None
    budget: float = 0
    channels: list[str] | None = None
    start_date: str
    end_date: str
    weekdays: list[int]
    active: bool = True
    last_run_date: str | None = None
    created_at: str = ""
    updated_at: str = ""
