# app/api/routes_autopilot.py
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends

from app.db import tenants as tenant_repo
from app.services import autopilot
from app.tenancy.auth import require_tenant

router = APIRouter(prefix="/v1/autopilot", tags=["Autopilot"], dependencies=[Depends(require_tenant)])


@router.get("")
def get_autopilot(tenant: dict = Depends(require_tenant)) -> Any:
    fresh = tenant_repo.get(tenant["id"]) or tenant
    config = fresh.get("autopilot") or {}
    return {
        **config,
        "due_now": autopilot.is_due(fresh),
        "quota_block": tenant_repo.quota_exceeded(fresh),
    }


@router.post("/tick")
async def tick(tenant: dict = Depends(require_tenant)) -> Any:
    """Force one autopilot cycle now, without waiting for the schedule.

    Runs the same code path the background scheduler uses, so what you see here
    is exactly what happens unattended.
    """
    fresh = tenant_repo.get(tenant["id"]) or tenant
    return await asyncio.to_thread(autopilot.tick_tenant, fresh)
