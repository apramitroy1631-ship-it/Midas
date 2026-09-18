# app/schemas/brand.py
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BrandGuidelines(BaseModel):
    visual_style: str = ""
    preferred_channels: list[str] = Field(default_factory=list)
    content_restrictions: list[str] = Field(default_factory=list)


class BrandMemory(BaseModel):
    """What the system has learned about this brand from its own past runs.

    Written back by the learn node at the end of every run, and read by the
    orchestrator at the start of the next one. This is the loop that lets the
    system improve without anyone editing a prompt.
    """

    past_campaigns: list[str] = Field(default_factory=list)
    latest_insights: list[str] = Field(default_factory=list)
    winning_angles: list[str] = Field(default_factory=list)
    exhausted_angles: list[str] = Field(default_factory=list)
    brand_guidelines: BrandGuidelines | dict[str, Any] = Field(default_factory=dict)
    # Durable research facts (audience, market size, competitors) - reused by the
    # Research agent across runs instead of re-deriving them from scratch every time.
    market_facts: dict[str, Any] = Field(default_factory=dict)


class BrandCreate(BaseModel):
    name: str = ""
    description: str = ""
    industry: str = ""
    tone: str = ""
    usp: str = ""
    target_audience: str = ""
    website: str = ""
    brand_guidelines: BrandGuidelines | dict[str, Any] = Field(default_factory=dict)
    latest_insights: list[str] = Field(default_factory=list)


class BrandUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    industry: str | None = None
    tone: str | None = None
    usp: str | None = None
    target_audience: str | None = None
    website: str | None = None
    brand_guidelines: BrandGuidelines | dict[str, Any] | None = None
    latest_insights: list[str] | None = None


class BrandResponse(BaseModel):
    id: str
    tenant_id: str = ""
    name: str = ""
    description: str = ""
    industry: str = ""
    tone: str = ""
    usp: str = ""
    target_audience: str = ""
    website: str = ""
    memory: BrandMemory | dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
