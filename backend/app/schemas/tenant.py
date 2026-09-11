# app/schemas/tenant.py
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Autonomy = Literal["autonomous", "review_required"]


class TenantPolicy(BaseModel):
    """How much rope the agents get for this tenant."""

    autonomy: Autonomy = Field(
        default="autonomous",
        description=(
            "autonomous: agents self-correct and publish without a human. "
            "review_required: finished content parks in a review queue instead of publishing."
        ),
    )
    auto_publish: bool = True
    max_revision_cycles: int = Field(default=2, ge=0, le=5)
    # Hard rules the QA agent treats as blocking, on top of whatever it infers.
    forbidden_claims: list[str] = Field(default_factory=list)
    required_disclaimers: list[str] = Field(default_factory=list)
    banned_phrases: list[str] = Field(default_factory=list)


class AutopilotConfig(BaseModel):
    """Unattended operation: the system picks its own goals and runs itself."""

    enabled: bool = False
    interval_minutes: int = Field(default=1440, ge=5)
    brand_id: str | None = None
    last_run_at: str | None = None
    next_run_at: str | None = None


class TenantLimits(BaseModel):
    monthly_run_quota: int = Field(default=200, ge=0)
    monthly_budget_usd: float = Field(default=250.0, ge=0)


class TenantUsage(BaseModel):
    runs_this_period: int = 0
    spend_usd: float = 0.0
    period: str = ""


class TenantCreate(BaseModel):
    name: str
    slug: str = ""
    policy: TenantPolicy = Field(default_factory=TenantPolicy)
    autopilot: AutopilotConfig = Field(default_factory=AutopilotConfig)
    limits: TenantLimits = Field(default_factory=TenantLimits)


class TenantUpdate(BaseModel):
    name: str | None = None
    policy: TenantPolicy | None = None
    autopilot: AutopilotConfig | None = None
    limits: TenantLimits | None = None
    model_overrides: dict[str, Any] | None = None


class TenantResponse(BaseModel):
    id: str
    name: str
    slug: str
    status: str = "active"
    api_key_prefix: str = ""
    policy: TenantPolicy = Field(default_factory=TenantPolicy)
    autopilot: AutopilotConfig = Field(default_factory=AutopilotConfig)
    limits: TenantLimits = Field(default_factory=TenantLimits)
    usage: TenantUsage = Field(default_factory=TenantUsage)
    model_overrides: dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


class TenantCreated(TenantResponse):
    """Returned once, at creation. The raw key is never retrievable again."""

    api_key: str
