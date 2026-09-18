# app/graph/builder.py
"""The autonomous campaign graph.

    orchestrate -> [research] -> strategy -> content -> seo -> qa
        |              ^                        ^                |
        | (light mode: skip research)           |                v
        +----------------------------------> revise <---- (critical issues, budget left)
                                                                  |
                                                  (clean) --------+--> publish -> analytics -> learn -> END
                                                                  |
                                           (still failing, budget spent) --> arbitrate --> publish | END

The loop back through `revise` is what makes this run unattended: a QA failure
feeds the specific issues back to the writer instead of parking the run in a
review queue. `arbitrate` is the floor - it guarantees the graph terminates
even if the writer never satisfies QA.

`light_mode` (set by orchestrate, based on which channels were planned) skips
the research node entirely and drops the tool-calling ReAct loop from
strategy/content - a short-form run (linkedin, email) doesn't need the same
grounding a blog post does, and paying for it anyway was most of why simple
runs were taking minutes instead of seconds.
"""
from __future__ import annotations

import logging

from langgraph.graph import END, StateGraph

from app.graph.nodes import (
    analytics_node,
    arbitrate_node,
    content_node,
    learn_node,
    orchestrate_node,
    publish_node,
    qa_node,
    research_node,
    revise_node,
    seo_node,
    strategy_node,
)
from app.graph.state import RunState

logger = logging.getLogger("graph.builder")


def _after_qa(state: RunState) -> str:
    qa = state.get("qa_report") or {}
    critical = [i for i in (qa.get("issues") or []) if i.get("severity") == "critical"]

    if qa.get("passed") and not critical:
        logger.info("qa router | clean -> publish")
        return "publish"

    used = state.get("revisions", 0)
    allowed = state.get("max_revisions", 2)
    if used < allowed:
        logger.info("qa router | %d critical | revision %d/%d -> revise", len(critical), used + 1, allowed)
        return "revise"

    logger.warning("qa router | %d critical | revision budget spent -> arbitrate", len(critical))
    return "arbitrate"


def _after_arbitrate(state: RunState) -> str:
    return END if state.get("status") == "abandoned" else "publish"


def _after_orchestrate(state: RunState) -> str:
    if state.get("light_mode"):
        logger.info("orchestrate router | light mode -> strategy (skipping research)")
        return "strategy"
    return "research"


def build_campaign_graph():
    graph = StateGraph(RunState)

    graph.add_node("orchestrate", orchestrate_node)
    graph.add_node("research", research_node)
    graph.add_node("strategy", strategy_node)
    graph.add_node("content", content_node)
    graph.add_node("seo", seo_node)
    graph.add_node("qa", qa_node)
    graph.add_node("revise", revise_node)
    graph.add_node("arbitrate", arbitrate_node)
    graph.add_node("publish", publish_node)
    graph.add_node("analytics", analytics_node)
    graph.add_node("learn", learn_node)

    graph.set_entry_point("orchestrate")
    graph.add_conditional_edges(
        "orchestrate", _after_orchestrate, {"research": "research", "strategy": "strategy"}
    )
    graph.add_edge("research", "strategy")
    graph.add_edge("strategy", "content")
    graph.add_edge("content", "seo")
    graph.add_edge("seo", "qa")

    graph.add_conditional_edges(
        "qa",
        _after_qa,
        {"publish": "publish", "revise": "revise", "arbitrate": "arbitrate"},
    )
    # Revision loop: back to the writer with QA's issues attached, then re-reviewed.
    graph.add_edge("revise", "content")
    graph.add_conditional_edges("arbitrate", _after_arbitrate, {"publish": "publish", END: END})

    graph.add_edge("publish", "analytics")
    graph.add_edge("analytics", "learn")
    graph.set_finish_point("learn")

    return graph.compile()


_compiled = None


def get_campaign_graph():
    """Compiled once per process - the graph is stateless and tenant-agnostic."""
    global _compiled
    if _compiled is None:
        _compiled = build_campaign_graph()
    return _compiled
