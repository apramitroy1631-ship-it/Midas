# app/tenancy/auth.py
"""API-key authentication and per-request tenant binding."""
from __future__ import annotations

from typing import Any

from fastapi import Depends, Header, HTTPException, Request

from app.core.settings import settings
from app.db import sessions as session_repo
from app.db import tenants as tenant_repo
from app.tenancy.context import set_tenant


async def require_tenant(request: Request, x_api_key: str = Header(default="")) -> dict[str, Any]:
    """Resolve the caller's tenant and bind it for the rest of the request.

    The X-API-Key header carries either kind of credential the console can
    hold: a tenant's own service key (bx_live_...), or a personal login
    session (sess_...) minted by POST /v1/auth/login. Same header, same
    downstream behaviour either way — everything past this point only cares
    which tenant it resolved to.

    The scope is intentionally not reset when this dependency returns: SSE
    generators keep running after the handler exits and still need it. Each
    request runs in its own context, so the binding dies with the request.
    """
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header.")

    if x_api_key.startswith(session_repo.PREFIX):
        tenant_id = session_repo.resolve_tenant_id(x_api_key)
        tenant = tenant_repo.get(tenant_id) if tenant_id else None
    else:
        tenant = tenant_repo.get_by_api_key(x_api_key)

    if tenant is None:
        raise HTTPException(status_code=401, detail="Invalid API key.")
    if tenant.get("status") != "active":
        raise HTTPException(status_code=403, detail="Tenant is " + str(tenant.get("status")) + ".")

    set_tenant(tenant["id"])
    request.state.tenant = tenant
    return tenant


async def require_admin(x_admin_key: str = Header(default="")) -> None:
    if not settings.admin_api_key or x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Admin-Key.")


TenantDep = Depends(require_tenant)
AdminDep = Depends(require_admin)
