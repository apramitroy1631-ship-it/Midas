# app/tools/memory_tools.py
"""Internal tools: the agents' read access to their own tenant's history.

These go through `ScopedCollection`, so an agent running for tenant A cannot
retrieve tenant B's brand memory even if the model asks for it by id.
"""
from __future__ import annotations

import json
import logging

from langchain_core.tools import tool

from app.db.scoped import assets as assets_coll
from app.db.scoped import brands as brands_coll
from app.db.scoped import runs as runs_coll

logger = logging.getLogger("tools.memory")


@tool
def get_brand_memory(brand_id: str) -> str:
    """Retrieve accumulated memory for a brand: past insights, winning angles, and exhausted angles.

    Read this before planning so you do not repeat an angle the brand has already
    used up, and so you build on what previously scored well.

    Args:
        brand_id: The brand's id.
    """
    doc = brands_coll.find_one({"_id": brand_id})
    if not doc:
        return json.dumps({"error": "Brand not found in this tenant.", "brand_id": brand_id})
    memory = doc.get("memory") or {}
    logger.info("get_brand_memory | brand=%s | insights=%d", brand_id, len(memory.get("latest_insights", [])))
    return json.dumps(
        {
            "brand": doc.get("name", ""),
            "latest_insights": memory.get("latest_insights", [])[-12:],
            "winning_angles": memory.get("winning_angles", [])[-12:],
            "exhausted_angles": memory.get("exhausted_angles", [])[-20:],
            "past_campaigns": memory.get("past_campaigns", [])[-10:],
        }
    )


@tool
def get_past_campaigns(brand_id: str, limit: int = 5) -> str:
    """Retrieve this brand's most recent completed campaign runs with their QA scores.

    Use to see what has actually been tried, how it scored, and what to avoid
    repeating. Returns goal, channels, QA scores, and outcome only - not full copy.

    Args:
        brand_id: The brand's id.
        limit: How many recent runs to return. Default 5.
    """
    docs = runs_coll.find(
        {"brand_id": brand_id, "status": {"$in": ["completed", "published", "review_pending"]}},
        sort=[("created_at", -1)],
        limit=max(1, min(limit, 10)),
    )
    out = [
        {
            "goal": d.get("goal", ""),
            "channels": (d.get("strategy") or {}).get("channels", []),
            "brand_safety_score": (d.get("qa_report") or {}).get("brand_safety_score"),
            "goal_alignment_score": (d.get("qa_report") or {}).get("goal_alignment_score"),
            "status": d.get("status"),
            "created_at": d.get("created_at"),
        }
        for d in docs
    ]
    logger.info("get_past_campaigns | brand=%s | found=%d", brand_id, len(out))
    return json.dumps({"brand_id": brand_id, "campaigns": out})


@tool
def get_brand_guidelines(brand_id: str) -> str:
    """Retrieve the brand's voice, USP, and hard content restrictions.

    Always read this before writing or reviewing copy. `content_restrictions`
    are non-negotiable: violating one is a critical QA failure.

    Args:
        brand_id: The brand's id.
    """
    doc = brands_coll.find_one({"_id": brand_id})
    if not doc:
        return json.dumps({"error": "Brand not found in this tenant.", "brand_id": brand_id})
    guidelines = (doc.get("memory") or {}).get("brand_guidelines") or {}
    return json.dumps(
        {
            "brand": doc.get("name", ""),
            "tone": doc.get("tone", ""),
            "usp": doc.get("usp", ""),
            "description": doc.get("description", ""),
            "target_audience": doc.get("target_audience", ""),
            "visual_style": guidelines.get("visual_style", ""),
            "preferred_channels": guidelines.get("preferred_channels", []),
            "content_restrictions": guidelines.get("content_restrictions", []),
        }
    )


@tool
def get_published_assets(brand_id: str, limit: int = 8) -> str:
    """Retrieve headlines of recently published assets for this brand.

    Use to avoid writing copy that duplicates something already live.

    Args:
        brand_id: The brand's id.
        limit: How many recent assets to return. Default 8.
    """
    docs = assets_coll.find(
        {"brand_id": brand_id},
        sort=[("created_at", -1)],
        limit=max(1, min(limit, 25)),
    )
    out = [{"channel": d.get("channel"), "headline": d.get("headline"), "created_at": d.get("created_at")} for d in docs]
    return json.dumps({"brand_id": brand_id, "recent_assets": out})
