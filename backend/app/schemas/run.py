# app/schemas/run.py
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    """Kick off a campaign run.

    `goal` is optional on purpose: with no goal the orchestrator reads brand
    memory and chooses one itself, which is how autopilot runs work.
    """

    brand_id: str
    goal: str | None = None
    target_audience: str | None = None
    budget: float = 5000.0
    trigger: str = "manual"  # manual | autopilot | api
    channels: list[str] | None = None  # e.g. ["email"] — omit to let the Director choose


class RunSummary(BaseModel):
    id: str
    brand_id: str
    brand_name: str = ""
    status: str
    goal: str = ""
    goal_origin: str = ""
    trigger: str = "manual"
    revisions: int = 0
    qa_passed: bool | None = None
    brand_safety_score: int | None = None
    goal_alignment_score: int | None = None
    asset_count: int = 0
    duration_ms: int = 0
    created_at: str = ""


class RunDetail(RunSummary):
    plan: dict[str, Any] | None = None
    research: dict[str, Any] | None = None
    strategy: dict[str, Any] | None = None
    content: dict[str, Any] | None = None
    seo: dict[str, Any] | None = None
    qa_report: dict[str, Any] | None = None
    analytics: dict[str, Any] | None = None
    learning: dict[str, Any] | None = None
    events: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class AssetResponse(BaseModel):
    id: str
    run_id: str
    brand_id: str
    brand_name: str = ""
    channel: str
    headline: str
    body: str
    call_to_action: str
    status: str = "published"
    seo: dict[str, Any] | None = None
    goal: str = ""
    created_at: str = ""


class AssetUpdate(BaseModel):
    """Edits made in the content canvas. All optional — only what changed is sent."""

    headline: str | None = None
    body: str | None = None
    call_to_action: str | None = None


class AssetRegenerateRequest(BaseModel):
    """Operator feedback driving a targeted content fix - not a new run."""

    feedback: str
