# app/graph/nodes.py
"""Graph nodes.

Each node is a thin adapter: pull what the agent needs out of state, run it,
put the typed result back. The only nodes with real logic of their own are
`arbitrate` (what to do when the agents cannot produce clean content) and
`publish` (which writes tenant-scoped records).
"""
from __future__ import annotations

import logging
import uuid

from app.agents.analytics import AnalyticsAgent
from app.agents.content import ContentAgent
from app.agents.learning import LearningAgent
from app.agents.orchestrator import OrchestratorAgent
from app.agents.qa import QAAgent
from app.agents.research import ResearchAgent
from app.agents.seo import SEOAgent
from app.agents.strategy import StrategyAgent
from app.db.scoped import assets as assets_coll
from app.db.scoped import brands as brands_coll
from app.graph.state import RunState

logger = logging.getLogger("graph.nodes")


def _overrides(state: RunState) -> dict:
    return state.get("model_overrides") or {}


# ---------------------------------------------------------------------------
# Specialist nodes
# ---------------------------------------------------------------------------


def orchestrate_node(state: RunState) -> dict:
    plan = OrchestratorAgent(_overrides(state)).run(
        brand_context=state["brand_context"],
        goal=state.get("goal_input"),
        target_audience=state.get("audience_input"),
        budget=state.get("budget", 0.0),
        policy=state.get("policy", {}),
    )
    return {"plan": plan.model_dump(), "status": "planning"}


def research_node(state: RunState) -> dict:
    result = ResearchAgent(_overrides(state)).run(
        brand_context=state["brand_context"],
        plan=state.get("plan") or {},
        budget=state.get("budget", 0.0),
    )
    return {"research": result.model_dump(), "status": "researching"}


def strategy_node(state: RunState) -> dict:
    result = StrategyAgent(_overrides(state)).run(
        brand_context=state["brand_context"],
        plan=state.get("plan") or {},
        research=state.get("research") or {},
        budget=state.get("budget", 0.0),
    )
    return {"strategy": result.model_dump(), "status": "strategising"}


def content_node(state: RunState) -> dict:
    revision = state.get("revisions", 0)
    result = ContentAgent(_overrides(state)).run(
        brand_context=state["brand_context"],
        plan=state.get("plan") or {},
        research=state.get("research") or {},
        strategy=state.get("strategy") or {},
        policy=state.get("policy") or {},
        previous_content=state.get("content"),
        qa_report=state.get("qa_report"),
        revision=revision,
    )
    return {"content": result.model_dump(), "status": "writing"}


def seo_node(state: RunState) -> dict:
    result = SEOAgent(_overrides(state)).run(
        brand_context=state["brand_context"],
        plan=state.get("plan") or {},
        content=state.get("content") or {},
    )
    return {"seo": result.model_dump(), "status": "optimising"}


def qa_node(state: RunState) -> dict:
    result = QAAgent(_overrides(state)).run(
        brand_context=state["brand_context"],
        plan=state.get("plan") or {},
        strategy=state.get("strategy") or {},
        content=state.get("content") or {},
        research=state.get("research") or {},
        policy=state.get("policy") or {},
        revision=state.get("revisions", 0),
    )
    return {"qa_report": result.model_dump(), "status": "reviewing"}


def revise_node(state: RunState) -> dict:
    """Bookkeeping between a QA failure and the next content pass.

    Kept separate from `content_node` so the revision shows up as its own step
    in the run timeline instead of silently re-firing the writer.
    """
    revision = state.get("revisions", 0) + 1
    critical = [
        i for i in ((state.get("qa_report") or {}).get("issues") or []) if i.get("severity") == "critical"
    ]
    logger.info("revise | cycle=%d | critical_issues=%d", revision, len(critical))
    return {"revisions": revision, "status": "revising"}


def arbitrate_node(state: RunState) -> dict:
    """Reached when the agents have burned their revision budget and QA still fails.

    With no human to escalate to, the system degrades rather than stalls: assets
    that individually cleared QA still ship, assets with critical issues are
    dropped, and if nothing survives the run is abandoned. The decision is
    recorded so the outcome is auditable after the fact.
    """
    qa = state.get("qa_report") or {}
    content = state.get("content") or {}
    critical_channels = {
        (i.get("channel") or "").strip().lower()
        for i in (qa.get("issues") or [])
        if i.get("severity") == "critical"
    }

    surviving = [
        a for a in (content.get("assets") or []) if (a.get("channel") or "").strip().lower() not in critical_channels
    ]
    dropped = sorted(critical_channels)

    if not surviving:
        logger.warning("arbitrate | no assets survived QA | run=%s", state.get("run_id"))
        return {
            "status": "abandoned",
            "dropped_channels": dropped,
            "error": "All assets failed QA after " + str(state.get("revisions", 0)) + " revision cycles.",
        }

    logger.info("arbitrate | partial publish | keeping=%d | dropping=%s", len(surviving), dropped)
    return {
        "content": {**content, "assets": surviving},
        "dropped_channels": dropped,
        "status": "partial",
    }


# ---------------------------------------------------------------------------
# Terminal nodes
# ---------------------------------------------------------------------------


def publish_node(state: RunState) -> dict:
    """Write each asset into the tenant's content library.

    Honours the tenant's autonomy policy: an `autonomous` tenant publishes,
    a `review_required` tenant parks the same assets as pending_review. The
    agent pipeline above is identical either way.
    """
    policy = state.get("policy") or {}
    autonomous = policy.get("autonomy", "autonomous") == "autonomous" and policy.get("auto_publish", True)
    asset_status = "published" if autonomous else "pending_review"

    content = state.get("content") or {}
    seo_by_channel = {
        (s.get("channel") or "").strip().lower(): s for s in ((state.get("seo") or {}).get("per_asset") or [])
    }
    qa = state.get("qa_report") or {}
    plan = state.get("plan") or {}

    ids: list[str] = []
    for asset in content.get("assets") or []:
        asset_id = str(uuid.uuid4())
        channel = (asset.get("channel") or "").strip()
        assets_coll.insert(
            {
                "_id": asset_id,
                "run_id": state.get("run_id"),
                "brand_id": state.get("brand_id"),
                "brand_name": (state.get("brand_context") or {}).get("name", ""),
                "channel": channel,
                "headline": asset.get("headline", ""),
                "body": asset.get("body", ""),
                "call_to_action": asset.get("call_to_action", ""),
                "status": asset_status,
                "seo": seo_by_channel.get(channel.lower()),
                "goal": plan.get("goal", ""),
                "brand_safety_score": qa.get("brand_safety_score"),
                "goal_alignment_score": qa.get("goal_alignment_score"),
            }
        )
        ids.append(asset_id)

    run_status = "published" if autonomous else "review_pending"
    if state.get("status") == "partial":
        run_status = "published_partial" if autonomous else "review_pending"

    logger.info("publish | run=%s | assets=%d | status=%s", state.get("run_id"), len(ids), run_status)
    return {"published_asset_ids": ids, "status": run_status}


def analytics_node(state: RunState) -> dict:
    result = AnalyticsAgent(_overrides(state)).run(
        plan=state.get("plan") or {},
        strategy=state.get("strategy") or {},
        budget=state.get("budget", 0.0),
    )
    return {"analytics": result.model_dump()}


def learn_node(state: RunState) -> dict:
    """Fold this run's lessons back into brand memory for the next planner."""
    result = LearningAgent(_overrides(state)).run(
        brand_context=state["brand_context"],
        plan=state.get("plan") or {},
        strategy=state.get("strategy") or {},
        content=state.get("content") or {},
        qa_report=state.get("qa_report") or {},
        analytics=state.get("analytics") or {},
        revisions=state.get("revisions", 0),
    )
    learning = result.model_dump()

    brand = brands_coll.find_one({"_id": state.get("brand_id")})
    if brand:
        memory = dict(brand.get("memory") or {})
        plan = state.get("plan") or {}

        def _extend(field: str, values: list[str], cap: int) -> None:
            existing = list(memory.get(field) or [])
            for value in values:
                if value not in existing:
                    existing.append(value)
            memory[field] = existing[-cap:]

        _extend("latest_insights", learning.get("insights") or [], 40)
        _extend("winning_angles", learning.get("winning_angles") or [], 30)
        _extend("exhausted_angles", learning.get("exhausted_angles") or [], 40)
        _extend("past_campaigns", [plan.get("goal", "")] if plan.get("goal") else [], 50)

        brands_coll.update({"_id": state.get("brand_id")}, {"memory": memory})
        logger.info("learn | brand memory updated | brand=%s", state.get("brand_id"))

    return {"learning": learning}
