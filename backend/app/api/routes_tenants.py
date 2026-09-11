# app/api/routes_tenants.py
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.db import tenants as tenant_repo
from app.schemas.tenant import (
    TenantCreate,
    TenantCreated,
    TenantResponse,
    TenantUpdate,
)
from app.tenancy.auth import require_admin, require_tenant

admin_router = APIRouter(prefix="/v1/admin/tenants", tags=["Admin"], dependencies=[Depends(require_admin)])
router = APIRouter(prefix="/v1", tags=["Tenant"])


@admin_router.post("", response_model=TenantCreated, status_code=201)
def create_tenant(payload: TenantCreate) -> Any:
    """Provision a tenant. The returned api_key is shown once and never again."""
    doc, raw_key = tenant_repo.create(payload.model_dump())
    return TenantCreated(**doc, api_key=raw_key)


@admin_router.get("", response_model=list[TenantResponse])
def list_tenants() -> Any:
    return [TenantResponse(**t) for t in tenant_repo.list_all()]


@admin_router.patch("/{tenant_id}", response_model=TenantResponse)
def admin_update_tenant(tenant_id: str, payload: TenantUpdate) -> Any:
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    doc = tenant_repo.update(tenant_id, changes)
    if doc is None:
        raise HTTPException(status_code=404, detail="Tenant not found.")
    return TenantResponse(**doc)


@router.get("/me", response_model=TenantResponse)
def whoami(tenant: dict = Depends(require_tenant)) -> Any:
    """Who this API key belongs to, plus its live policy, limits, and usage."""
    fresh = tenant_repo.get(tenant["id"])
    return TenantResponse(**(fresh or tenant))


@router.patch("/me", response_model=TenantResponse)
def update_me(payload: TenantUpdate, tenant: dict = Depends(require_tenant)) -> Any:
    """A tenant may tune its own policy, autopilot, and model routing.

    Limits are deliberately not editable here - only an admin can raise a quota.
    """
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    changes.pop("limits", None)
    doc = tenant_repo.update(tenant["id"], changes)
    if doc is None:
        raise HTTPException(status_code=404, detail="Tenant not found.")
    return TenantResponse(**doc)
