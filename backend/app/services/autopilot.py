# app/services/autopilot.py
"""Unattended operation.

A single background sweep looks for tenants whose autopilot is due, and starts
a run for each. No goal is passed: the Campaign Director reads brand memory and
chooses one. This is the part of the system that runs when nobody is watching,
so it is deliberately conservative - one run per tenant per sweep, quota checked
first, and every failure caught so one bad tenant cannot stop the loop.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.settings import settings
from app.db import tenants as tenant_repo
from app.db.scoped import brands as brands_coll
from app.graph.runner import run_sync
from app.tenancy.context import tenant_scope

logger = logging.getLogger("autopilot")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds").replace("+00:00", "Z")


def is_due(tenant: dict[str, Any]) -> bool:
    autopilot = tenant.get("autopilot") or {}
    if not autopilot.get("enabled"):
        return False
    next_run = _parse(autopilot.get("next_run_at"))
    return next_run is None or next_run <= _now()


def _resolve_brand(tenant: dict[str, Any]) -> str | None:
    """Which brand this tenant's autopilot works on.

    An explicit brand_id wins; otherwise pick the brand that has gone longest
    without a run, so a tenant with several brands gets round-robin coverage.
    """
    autopilot = tenant.get("autopilot") or {}
    with tenant_scope(tenant["id"]):
        if autopilot.get("brand_id"):
            brand = brands_coll.find_one({"_id": autopilot["brand_id"]})
            return str(brand["_id"]) if brand else None

        brands = brands_coll.find(sort=[("updated_at", 1)], limit=1)
        return str(brands[0]["_id"]) if brands else None


def _schedule_next(tenant: dict[str, Any]) -> None:
    autopilot = dict(tenant.get("autopilot") or {})
    interval = int(autopilot.get("interval_minutes") or 1440)
    autopilot["last_run_at"] = _iso(_now())
    autopilot["next_run_at"] = _iso(_now() + timedelta(minutes=interval))
    tenant_repo.update(tenant["id"], {"autopilot": autopilot})


def tick_tenant(tenant: dict[str, Any]) -> dict[str, Any]:
    """Run one autopilot cycle for a tenant. Safe to call directly (the API does)."""
    blocked = tenant_repo.quota_exceeded(tenant)
    if blocked:
        logger.info("autopilot | skip | tenant=%s | %s", tenant.get("slug"), blocked)
        _schedule_next(tenant)
        return {"skipped": True, "reason": blocked}

    brand_id = _resolve_brand(tenant)
    if not brand_id:
        logger.info("autopilot | skip | tenant=%s | no brands configured", tenant.get("slug"))
        _schedule_next(tenant)
        return {"skipped": True, "reason": "No brands configured for this tenant."}

    logger.info("autopilot | run | tenant=%s | brand=%s", tenant.get("slug"), brand_id)
    try:
        result = run_sync(brand_id=brand_id, tenant=tenant, goal=None, trigger="autopilot")
    except Exception as exc:  # one tenant's failure must not stop the sweep
        logger.exception("autopilot | run failed | tenant=%s", tenant.get("slug"))
        _schedule_next(tenant)
        return {"skipped": False, "error": str(exc)}

    _schedule_next(tenant)
    return {"skipped": False, "run_id": result.get("run_id"), "status": result.get("status")}


async def sweep_once() -> int:
    """Start a run for every tenant that is due. Returns how many were started."""
    due = [t for t in tenant_repo.list_all() if t.get("status") == "active" and is_due(t)]
    if not due:
        return 0

    logger.info("autopilot | sweep | due=%d", len(due))
    for tenant in due:
        # run_sync blocks on LLM calls, so it goes to the default executor.
        await asyncio.to_thread(tick_tenant, tenant)
    return len(due)


async def scheduler_loop() -> None:
    logger.info(
        "autopilot | scheduler started | sweep=%ss", settings.autopilot_sweep_seconds
    )
    while True:
        try:
            await sweep_once()
        except asyncio.CancelledError:
            logger.info("autopilot | scheduler stopped")
            raise
        except Exception:
            logger.exception("autopilot | sweep failed")
        await asyncio.sleep(settings.autopilot_sweep_seconds)
