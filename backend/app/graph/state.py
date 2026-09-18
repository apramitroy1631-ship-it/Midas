# app/graph/state.py
from __future__ import annotations

from typing import Any, TypedDict


class RunState(TypedDict, total=False):
    """State carried through one autonomous campaign run.

    Nodes return partial dicts; LangGraph merges them in. `revisions` is the
    only counter the routing depends on, and only the content node increments it.
    """

    # identity / scope
    run_id: str
    tenant_id: str
    brand_id: str
    trigger: str

    # inputs
    brand_context: dict[str, Any]
    policy: dict[str, Any]
    model_overrides: dict[str, Any]
    goal_input: str | None
    audience_input: str | None
    channel_override: list[str] | None
    budget: float

    # agent outputs
    plan: dict[str, Any] | None
    research: dict[str, Any] | None
    strategy: dict[str, Any] | None
    content: dict[str, Any] | None
    seo: dict[str, Any] | None
    qa_report: dict[str, Any] | None
    analytics: dict[str, Any] | None
    learning: dict[str, Any] | None

    # self-correction control
    revisions: int
    max_revisions: int
    dropped_channels: list[str]

    # True when every planned channel is "light" (e.g. linkedin, email) and
    # none need deep research (e.g. blog) - skips the research step and the
    # tool-calling ReAct loop in strategy/content for a much faster run.
    light_mode: bool

    # outcome
    status: str
    published_asset_ids: list[str]
    error: str | None
