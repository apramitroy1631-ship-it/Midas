# app/schemas/brand.py
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class BrandGuidelines(BaseModel):
    visual_style: str = ""
    preferred_channels: list[str] = Field(default_factory=list)
    content_restrictions: list[str] = Field(default_factory=list)


class BrandMemory(BaseModel):
    past_campaigns: list[str] = Field(default_factory=list)
    latest_insights: list[str] = Field(default_factory=list)
    brand_guidelines: BrandGuidelines | dict[str, Any] = Field(default_factory=dict)


# --- Create: only these parameters ---
class BrandCreate(BaseModel):
    """POST /brands — only these fields accepted."""

    name: str = ""
    description: str = ""
    industry: str = ""
    tone: str = ""
    usp: str = ""
    target_audience: str = ""
    brand_guidelines: BrandGuidelines | dict[str, Any] = Field(default_factory=dict)
    latest_insights: list[str] = Field(default_factory=list)


# --- Update: same fields, all optional ---
class BrandUpdate(BaseModel):
    """PUT /brands/{id} — partial update."""

    name: str | None = None
    description: str | None = None
    industry: str | None = None
    tone: str | None = None
    usp: str | None = None
    target_audience: str | None = None
    brand_guidelines: BrandGuidelines | dict[str, Any] | None = None
    latest_insights: list[str] | None = None


# --- List item (id + name only) ---
class BrandSummary(BaseModel):
    """Id and name for GET all brands."""

    id: str
    name: str = ""


# --- Full brand document (stored in DB, returned by GET) ---
class BrandResponse(BaseModel):
    """Full brand object: GET /brands/{id} and stored in DB."""

    id: str
    name: str = ""
    description: str = ""
    industry: str = ""
    tone: str = ""
    usp: str = ""
    target_audience: str = ""
    memory: BrandMemory | dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
