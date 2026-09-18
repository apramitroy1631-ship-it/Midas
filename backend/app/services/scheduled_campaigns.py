# app/services/scheduled_campaigns.py
"""Per-campaign scheduling, separate from the tenant-wide autopilot interval.

A campaign created with a date range + weekday pattern in New Campaign sits idle
until one of its chosen weekdays falls inside that range - only then does it run,
once, for that day. This exists specifically to stop unscheduled/ad-hoc pipeline
runs from firing outside what an operator explicitly asked for.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Any

from app.core.settings import settings
from app.db import tenants as tenant_repo
from app.db.mongo import raw
from app.graph.runner import run_sync

logger = logging.getLogger("scheduled_campaigns")


def _due_today(schedule: dict[str, Any], today: date) -> bool:
    if not schedule.get("active", True):
        return False
    start = date.fromisoformat(schedule["start_date"])
    end = date.fromisoformat(schedule["end_date"])
    if not (start <= today <= end):
        return False
    if today.weekday() not in (schedule.get("weekdays") or []):
        return False
    return schedule.get("last_run_date") != today.isoformat()


def sweep_once() -> int:
    """Run every schedule (across all tenants) that's due today and hasn't run yet.

    Runs synchronously per campaign - this rides the same executor thread the
    autopilot sweep uses, and is likewise a handful of tenants at most.
    """
    coll = raw("scheduled_campaigns")
    today = date.today()
    due = [s for s in coll.find({"active": True}) if _due_today(s, today)]
    if not due:
        return 0

    logger.info("scheduled-campaigns | sweep | due=%d", len(due))
    for schedule in due:
        tenant = tenant_repo.get(schedule["tenant_id"])
        if not tenant or tenant.get("status") != "active":
            continue
        blocked = tenant_repo.quota_exceeded(tenant)
        if blocked:
            logger.info("scheduled-campaigns | skip | id=%s | %s", schedule["_id"], blocked)
            continue
        try:
            result = run_sync(
                brand_id=schedule["brand_id"],
                tenant=tenant,
                goal=schedule.get("goal"),
                audience=schedule.get("target_audience"),
                channels=schedule.get("channels"),
                budget=float(schedule.get("budget") or 0),
                trigger="scheduled",
            )
            logger.info(
                "scheduled-campaigns | ran | id=%s | run=%s | status=%s",
                schedule["_id"], result.get("run_id"), result.get("status"),
            )
        except Exception:
            logger.exception("scheduled-campaigns | run failed | id=%s", schedule["_id"])
        finally:
            coll.update_one({"_id": schedule["_id"]}, {"$set": {"last_run_date": today.isoformat()}})
    return len(due)


async def scheduler_loop() -> None:
    logger.info("scheduled-campaigns | scheduler started | sweep=%ss", settings.autopilot_sweep_seconds)
    while True:
        try:
            await asyncio.to_thread(sweep_once)
        except asyncio.CancelledError:
            logger.info("scheduled-campaigns | scheduler stopped")
            raise
        except Exception:
            logger.exception("scheduled-campaigns | sweep failed")
        await asyncio.sleep(settings.autopilot_sweep_seconds)
