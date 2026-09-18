# app/services/regenerate.py
"""Targeted "I'm not happy with this, fix it" regeneration for one asset.

Deliberately NOT a new run: it reuses the plan/research/strategy already
produced for the original run and re-invokes only the Content agent, scoped
to the one channel being fixed, with the operator's feedback as a required
instruction. No orchestrate/research/strategy/QA - a fraction of the cost and
time of a full pipeline run, because the operator reviewing the result IS the
quality gate here.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from app.agents.content import ContentAgent
from app.db.scoped import assets as assets_coll
from app.db.scoped import audit as audit_coll
from app.graph.runner import _brand_context, load_brand
from app.tenancy.context import tenant_scope

logger = logging.getLogger("regenerate")


def regenerate_asset(
    *,
    asset: dict[str, Any],
    run: dict[str, Any],
    tenant: dict[str, Any],
    feedback: str,
) -> dict[str, Any]:
    with tenant_scope(tenant["id"]):
        brand = load_brand(asset["brand_id"])
        policy = tenant.get("policy") or {}
        channel = asset.get("channel", "")

        result = ContentAgent(tenant.get("model_overrides")).run(
            brand_context=_brand_context(brand),
            plan=run.get("plan") or {},
            research=run.get("research") or {},
            strategy=run.get("strategy") or {},
            policy=policy,
            previous_content={
                "assets": [
                    {
                        "headline": asset.get("headline", ""),
                        "body": asset.get("body", ""),
                        "call_to_action": asset.get("call_to_action", ""),
                        "channel": channel,
                    }
                ]
            },
            operator_feedback=feedback,
            only_channel=channel,
            use_tools=False,  # brand context is already inline; keep this fast, not a full run
        )

        assets = result.model_dump().get("assets") or []
        new_asset = assets[0] if assets else {}

        assets_coll.update(
            {"_id": asset["_id"]},
            {
                "headline": new_asset.get("headline", asset.get("headline", "")),
                "body": new_asset.get("body", asset.get("body", "")),
                "call_to_action": new_asset.get("call_to_action", asset.get("call_to_action", "")),
            },
        )

        audit_coll.insert(
            {
                "_id": str(uuid.uuid4()),
                "run_id": asset.get("run_id"),
                "brand_id": asset.get("brand_id"),
                "action": "asset.regenerated",
                "actor": "operator",
                "trigger": "manual",
                "detail": {"asset_id": asset["_id"], "channel": channel, "feedback": feedback},
            }
        )
        logger.info("regenerate | asset=%s | channel=%s", asset["_id"], channel)

        return assets_coll.find_one({"_id": asset["_id"]})
