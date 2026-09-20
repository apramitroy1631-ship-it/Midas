# app/services/regenerate.py
"""Targeted "I'm not happy with this, fix it" regeneration for one asset.

Deliberately NOT a new run: it reuses the plan/research/strategy already
produced for the original run and re-invokes only the Content agent, scoped
to the one channel being fixed - a fraction of the cost and time of a full
pipeline run. Two things keep that fast path from being a blind one:

- Earlier feedback on the same asset is remembered and passed along, so a
  later "add the discount code" doesn't undo an earlier "make it shorter".
- The new draft goes through the same QA agent as a normal run (brand rules,
  banned phrases, unsupported claims). If it finds a blocking issue the draft
  gets exactly one automatic fix and is re-checked. It never loops, and it
  never blocks saving: the operator is still the final judge, so a draft that
  still fails is saved with the issues attached for them to see.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from app.agents.channel_specs import rewrite_target, word_count
from app.agents.content import ContentAgent
from app.agents.qa import QAAgent
from app.db.scoped import assets as assets_coll
from app.db.scoped import audit as audit_coll
from app.db.scoped import utcnow
from app.graph.runner import _brand_context, load_brand
from app.tenancy.context import tenant_scope

logger = logging.getLogger("regenerate")

_HISTORY_SENT = 4  # how many earlier rounds of feedback ride along with a new one
_HISTORY_KEPT = 20


def _critical(qa: dict[str, Any] | None) -> list[dict[str, Any]]:
    return [i for i in ((qa or {}).get("issues") or []) if i.get("severity") == "critical"]


def _fix_note(issues: list[dict[str, Any]]) -> str:
    lines = [f"- {i.get('issue', '')} (fix: {i.get('fix', '')})" for i in issues]
    return "\n\nA quality check found blocking problems in your draft. Fix these as well:\n" + "\n".join(lines)


def regenerate_asset(
    *,
    asset: dict[str, Any],
    run: dict[str, Any],
    tenant: dict[str, Any],
    feedback: str,
) -> dict[str, Any]:
    with tenant_scope(tenant["id"]):
        brand = load_brand(asset["brand_id"])
        brand_context = _brand_context(brand)
        policy = tenant.get("policy") or {}
        overrides = tenant.get("model_overrides")
        channel = asset.get("channel", "")

        history = list(asset.get("feedback_history") or [])
        earlier = [h["feedback"] for h in history[-_HISTORY_SENT:] if h.get("feedback")]

        # Size the rewrite in code so the model isn't left to guess how much to
        # change: hold length steady unless the feedback is actually about length.
        previous_words = word_count(asset.get("body", ""))
        length_target = rewrite_target(channel, previous_words, feedback)

        def write(previous: dict[str, Any], operator_feedback: str) -> dict[str, Any]:
            result = ContentAgent(overrides).run(
                brand_context=brand_context,
                plan=run.get("plan") or {},
                research=run.get("research") or {},
                strategy=run.get("strategy") or {},
                policy=policy,
                previous_content={
                    "assets": [
                        {
                            "headline": previous.get("headline", ""),
                            "body": previous.get("body", ""),
                            "call_to_action": previous.get("call_to_action", ""),
                            "channel": channel,
                        }
                    ]
                },
                operator_feedback=operator_feedback,
                earlier_feedback=earlier,
                only_channel=channel,
                length_target=length_target,
                previous_words=previous_words,
                use_tools=False,  # brand context is already inline; keep this fast, not a full run
            )
            assets = result.model_dump().get("assets") or []
            return assets[0] if assets else {}

        def check(draft: dict[str, Any]) -> dict[str, Any] | None:
            try:
                return QAAgent(overrides).run(
                    brand_context=brand_context,
                    plan=run.get("plan") or {},
                    strategy=run.get("strategy") or {},
                    content={"assets": [{**draft, "channel": channel}]},
                    research=run.get("research") or {},
                    policy=policy,
                ).model_dump()
            except Exception:  # noqa: BLE001 - the check must never lose the operator's rewrite
                logger.exception("regenerate | quality check failed to run | asset=%s", asset["_id"])
                return None

        draft = write(asset, feedback)
        qa = check(draft)

        auto_fixed = False
        blocking = _critical(qa)
        if blocking:
            logger.info("regenerate | qa found %d blocking issue(s), one fix pass | asset=%s", len(blocking), asset["_id"])
            draft = write(draft, feedback + _fix_note(blocking))
            qa = check(draft)
            auto_fixed = True

        remaining = _critical(qa)
        history.append({"feedback": feedback, "at": utcnow()})
        changes: dict[str, Any] = {
            "headline": draft.get("headline", asset.get("headline", "")),
            "body": draft.get("body", asset.get("body", "")),
            "call_to_action": draft.get("call_to_action", asset.get("call_to_action", "")),
            "feedback_history": history[-_HISTORY_KEPT:],
            # None = the check couldn't run; shown as "not checked", not as a pass.
            "qa_passed": None if qa is None else not remaining,
            "qa_auto_fixed": auto_fixed,
            "qa_issues": [
                {k: i.get(k) for k in ("severity", "issue", "fix")} for i in ((qa or {}).get("issues") or [])
            ][:6],
        }
        if qa:
            changes["brand_safety_score"] = qa.get("brand_safety_score")
            changes["goal_alignment_score"] = qa.get("goal_alignment_score")
        assets_coll.update({"_id": asset["_id"]}, changes)

        audit_coll.insert(
            {
                "_id": str(uuid.uuid4()),
                "run_id": asset.get("run_id"),
                "brand_id": asset.get("brand_id"),
                "action": "asset.regenerated",
                "actor": "operator",
                "trigger": "manual",
                "detail": {
                    "asset_id": asset["_id"],
                    "channel": channel,
                    "feedback": feedback,
                    "qa_passed": changes["qa_passed"],
                    "auto_fixed": auto_fixed,
                },
            }
        )
        logger.info(
            "regenerate | asset=%s | channel=%s | qa_passed=%s | auto_fixed=%s",
            asset["_id"], channel, changes["qa_passed"], auto_fixed,
        )

        return assets_coll.find_one({"_id": asset["_id"]})
