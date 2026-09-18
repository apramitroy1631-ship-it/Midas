# app/graph/runner.py
"""Executes a campaign run and streams it.

LangGraph's `.stream()` is synchronous and every node inside it makes blocking
network calls, so it runs on a worker thread and pushes events back to the
event loop through a queue. The thread gets a *copy* of the current context,
which is how the tenant binding survives into the graph and keeps every write
inside the right tenant.
"""
from __future__ import annotations

import asyncio
import contextvars
import logging
import threading
import time
import uuid
from typing import Any, AsyncIterator, Callable

from app.db import tenants as tenant_repo
from app.db.scoped import audit as audit_coll
from app.db.scoped import brands as brands_coll
from app.db.scoped import runs as runs_coll
from app.db.scoped import utcnow
from app.graph.builder import get_campaign_graph
from app.graph.state import RunState
from app.services.llm.usage import metered
from app.tenancy.context import current_tenant, tenant_scope

logger = logging.getLogger("graph.runner")

_SENTINEL = object()
_RECURSION_LIMIT = 60

STEP_LABELS: dict[str, str] = {
    "orchestrate": "Campaign Director",
    "research": "Research Agent",
    "strategy": "Strategy Agent",
    "content": "Content Agent",
    "seo": "SEO Agent",
    "qa": "QA Reviewer",
    "revise": "Revision Cycle",
    "arbitrate": "Autonomous Arbitration",
    "publish": "Publisher",
    "analytics": "Analytics Agent",
    "learn": "Memory Update",
}

# Which state keys each node is responsible for — used to send the UI just the
# delta it needs rather than the whole accumulated state on every event.
STEP_OUTPUT_KEY: dict[str, str] = {
    "orchestrate": "plan",
    "research": "research",
    "strategy": "strategy",
    "content": "content",
    "seo": "seo",
    "qa": "qa_report",
    "analytics": "analytics",
    "learn": "learning",
}


class RunError(Exception):
    pass


def _initial_state(
    *,
    run_id: str,
    tenant: dict[str, Any],
    brand: dict[str, Any],
    goal: str | None,
    audience: str | None,
    channels: list[str] | None = None,
    budget: float,
    trigger: str,
    max_revisions: int,
) -> RunState:
    return {
        "run_id": run_id,
        "tenant_id": tenant["id"],
        "brand_id": str(brand["_id"]),
        "trigger": trigger,
        "brand_context": _brand_context(brand),
        "policy": tenant.get("policy") or {},
        "model_overrides": tenant.get("model_overrides") or {},
        "goal_input": goal or None,
        "audience_input": audience or None,
        "channel_override": [c.strip().lower() for c in channels if c.strip()] if channels else None,
        "budget": float(budget),
        "plan": None,
        "research": None,
        "strategy": None,
        "content": None,
        "seo": None,
        "qa_report": None,
        "analytics": None,
        "learning": None,
        "revisions": 0,
        "max_revisions": max_revisions,
        "dropped_channels": [],
        "status": "queued",
        "published_asset_ids": [],
        "error": None,
    }


def _brand_context(brand: dict[str, Any]) -> dict[str, Any]:
    ctx = {k: v for k, v in brand.items() if k not in ("_id", "tenant_id")}
    ctx["id"] = str(brand["_id"])
    return ctx


def load_brand(brand_id: str) -> dict[str, Any]:
    brand = brands_coll.find_one({"_id": brand_id})
    if brand is None:
        raise RunError("Brand not found in this tenant.")
    return brand


def start_run_record(state: RunState, brand: dict[str, Any]) -> None:
    runs_coll.insert(
        {
            "_id": state["run_id"],
            "brand_id": state["brand_id"],
            "brand_name": brand.get("name", ""),
            "status": "running",
            "trigger": state["trigger"],
            "goal": state.get("goal_input") or "",
            "goal_origin": "operator" if state.get("goal_input") else "self-directed",
            "budget": state["budget"],
            "revisions": 0,
            "events": [],
        }
    )


def _finalise(
    state: dict[str, Any],
    *,
    run_id: str,
    tenant_id: str,
    events: list[dict[str, Any]],
    usage: dict[str, Any],
    duration_ms: int,
    error: str | None = None,
) -> dict[str, Any]:
    plan = state.get("plan") or {}
    qa = state.get("qa_report") or {}
    status = "failed" if error else state.get("status", "completed")

    record = {
        "status": status,
        "goal": plan.get("goal") or state.get("goal_input") or "",
        "goal_origin": plan.get("goal_origin", "operator" if state.get("goal_input") else "self-directed"),
        "plan": plan or None,
        "research": state.get("research"),
        "strategy": state.get("strategy"),
        "content": state.get("content"),
        "seo": state.get("seo"),
        "qa_report": qa or None,
        "analytics": state.get("analytics"),
        "learning": state.get("learning"),
        "revisions": state.get("revisions", 0),
        "dropped_channels": state.get("dropped_channels", []),
        "qa_passed": qa.get("passed"),
        "brand_safety_score": qa.get("brand_safety_score"),
        "goal_alignment_score": qa.get("goal_alignment_score"),
        "asset_count": len(state.get("published_asset_ids") or []),
        "usage": usage,
        "duration_ms": duration_ms,
        "events": events,
        "error": error or state.get("error"),
    }
    runs_coll.update({"_id": run_id}, record)

    audit_coll.insert(
        {
            "_id": str(uuid.uuid4()),
            "run_id": run_id,
            "brand_id": state.get("brand_id"),
            "action": "run." + status,
            "actor": "system:autonomous",
            "trigger": state.get("trigger"),
            "detail": {
                "goal": record["goal"],
                "goal_origin": record["goal_origin"],
                "revisions": record["revisions"],
                "assets": record["asset_count"],
                "dropped_channels": record["dropped_channels"],
                "qa_passed": record["qa_passed"],
                "cost_usd": usage.get("cost_usd"),
            },
        }
    )
    tenant_repo.record_run(tenant_id, float(usage.get("cost_usd") or 0.0))
    return record


def _run_graph_into_queue(
    state: RunState,
    put: Callable[[Any], None],
) -> None:
    """Worker-thread body: drive the graph and push each node result out."""
    graph = get_campaign_graph()
    started = time.time()
    accumulated: dict[str, Any] = dict(state)
    events: list[dict[str, Any]] = []
    error: str | None = None

    with metered() as meter:
        try:
            for step in graph.stream(state, config={"recursion_limit": _RECURSION_LIMIT}):
                for node_name, delta in step.items():
                    if not delta:
                        continue
                    accumulated.update(delta)
                    key = STEP_OUTPUT_KEY.get(node_name)
                    event = {
                        "node": node_name,
                        "label": STEP_LABELS.get(node_name, node_name),
                        "status": accumulated.get("status"),
                        "revision": accumulated.get("revisions", 0),
                        "output": delta.get(key) if key else {
                            k: v for k, v in delta.items() if k != "status"
                        },
                        "at": utcnow(),
                        "elapsed_ms": int((time.time() - started) * 1000),
                    }
                    events.append(event)
                    put(("step", event))
        except Exception as exc:  # a run must never take the server down
            logger.exception("run failed | run=%s", state.get("run_id"))
            error = str(exc)
            put(("error", {"message": error}))

        usage = meter.snapshot()

    duration_ms = int((time.time() - started) * 1000)
    record = _finalise(
        accumulated,
        run_id=state["run_id"],
        tenant_id=state["tenant_id"],
        events=events,
        usage=usage,
        duration_ms=duration_ms,
        error=error,
    )
    put(("done", {"run_id": state["run_id"], **record}))
    put(_SENTINEL)


async def stream_run(
    *,
    brand_id: str,
    tenant: dict[str, Any],
    goal: str | None,
    audience: str | None,
    channels: list[str] | None = None,
    budget: float,
    trigger: str = "manual",
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """Yield (event_name, payload) tuples for the lifetime of one run."""
    brand = load_brand(brand_id)
    policy = tenant.get("policy") or {}
    run_id = str(uuid.uuid4())

    state = _initial_state(
        run_id=run_id,
        tenant=tenant,
        brand=brand,
        goal=goal,
        audience=audience,
        channels=channels,
        budget=budget,
        trigger=trigger,
        max_revisions=int(policy.get("max_revision_cycles", 2)),
    )
    start_run_record(state, brand)

    yield (
        "start",
        {
            "run_id": run_id,
            "brand_id": state["brand_id"],
            "brand_name": brand.get("name", ""),
            "autonomy": policy.get("autonomy", "autonomous"),
            "max_revisions": state["max_revisions"],
            "goal_origin": "operator" if goal else "self-directed",
        },
    )

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def put(item: Any) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, item)

    ctx = contextvars.copy_context()  # carries the tenant binding into the thread
    thread = threading.Thread(
        target=lambda: ctx.run(_run_graph_into_queue, state, put),
        name="run-" + run_id[:8],
        daemon=True,
    )
    thread.start()

    while True:
        item = await queue.get()
        if item is _SENTINEL:
            break
        yield item  # type: ignore[misc]


def run_sync(
    *,
    brand_id: str,
    tenant: dict[str, Any],
    goal: str | None = None,
    audience: str | None = None,
    channels: list[str] | None = None,
    budget: float = 5000.0,
    trigger: str = "autopilot",
) -> dict[str, Any]:
    """Blocking variant for the background scheduler, which has no client to stream to."""
    with tenant_scope(tenant["id"]):
        brand = load_brand(brand_id)
        policy = tenant.get("policy") or {}
        run_id = str(uuid.uuid4())
        state = _initial_state(
            run_id=run_id,
            tenant=tenant,
            brand=brand,
            goal=goal,
            audience=audience,
            channels=channels,
            budget=budget,
            trigger=trigger,
            max_revisions=int(policy.get("max_revision_cycles", 2)),
        )
        start_run_record(state, brand)

        collected: list[Any] = []
        _run_graph_into_queue(state, collected.append)

        for item in collected:
            if item is not _SENTINEL and item[0] == "done":
                return {"run_id": run_id, **item[1]}
        return {"run_id": run_id, "status": "unknown"}


def assert_scope() -> str:
    """Fail loudly rather than write across tenants if scope was somehow lost."""
    return current_tenant()
