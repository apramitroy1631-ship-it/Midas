# app/api/routes_auth.py
"""Email/password login for people, layered on top of the tenant API key.

Registration is admin-only (X-Admin-Key, same credential used to provision a
tenant) rather than open self-signup: a public register endpoint on a
"no human in the loop" autonomous marketing system would let anyone who
found the URL create their own account and start running campaigns for the
company. The admin creates one login per teammate; everyone signs in with
their own email + password after that.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from app.db import sessions as session_repo
from app.db import tenants as tenant_repo
from app.db import users as user_repo
from app.tenancy.auth import require_admin, require_tenant_admin

router = APIRouter(prefix="/v1/auth", tags=["Auth"])


class RegisterPayload(BaseModel):
    email: str
    password: str = Field(min_length=8)
    phone: str | None = None


class LoginPayload(BaseModel):
    email: str
    password: str


class TeamInvitePayload(BaseModel):
    email: str
    password: str = Field(min_length=8)
    phone: str | None = None
    role: str = "member"


class RoleUpdatePayload(BaseModel):
    role: str


class ChangePasswordPayload(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


def _require_session_user(x_api_key: str) -> dict[str, Any]:
    """Resolves the specific person behind a login session - a raw tenant
    service key has no individual behind it, so it can't change "its" password."""
    if not x_api_key.startswith(session_repo.PREFIX):
        raise HTTPException(status_code=400, detail="Sign in with your own login, not the tenant API key.")
    user_id = session_repo.resolve_user_id(x_api_key)
    user = user_repo.get(user_id) if user_id else None
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session.")
    return user


@router.post("/register", status_code=201, dependencies=[Depends(require_admin)])
def register(payload: RegisterPayload) -> Any:
    """Platform-admin-only bootstrap: creates the first admin login for this
    deployment's tenant. Once that exists, further teammates go through
    POST /v1/auth/team instead - a tenant admin's own session, not this
    platform-wide key, does the rest from here on."""
    if user_repo.get_by_email(payload.email):
        raise HTTPException(status_code=409, detail="An account with that email already exists.")

    tenants = tenant_repo.list_all()
    if not tenants:
        raise HTTPException(status_code=400, detail="No tenant exists yet — seed one first.")

    return user_repo.create(tenants[0]["id"], payload.email, payload.password, payload.phone, role="admin")


@router.post("/login")
def login(payload: LoginPayload) -> Any:
    user = user_repo.get_by_email(payload.email)
    if not user or not user_repo.verify_password(user, payload.password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    tenant = tenant_repo.get(user["tenant_id"])
    if tenant is None or tenant.get("status") != "active":
        raise HTTPException(status_code=403, detail="Tenant is not active.")

    token = session_repo.create(user["tenant_id"], user["_id"])
    return {
        "session_token": token,
        "tenant_name": tenant["name"],
        "email": user["email"],
        "role": user.get("role", "member"),
    }


@router.post("/logout")
def logout(x_api_key: str = Header(default="")) -> Any:
    """Revokes the session server-side, not just forgetting it in the browser.

    A raw tenant service key has no session to revoke - it's a static
    credential, not something login issued - so this is a no-op for that
    case rather than an error; the frontend calls it unconditionally before
    clearing its own local storage either way.
    """
    if x_api_key.startswith(session_repo.PREFIX):
        session_repo.revoke(x_api_key)
    return {"ok": True}


@router.get("/team")
def list_team(tenant: dict = Depends(require_tenant_admin)) -> Any:
    return user_repo.list_for_tenant(tenant["id"])


@router.post("/team", status_code=201)
def invite_teammate(payload: TeamInvitePayload, tenant: dict = Depends(require_tenant_admin)) -> Any:
    if payload.role not in ("admin", "member"):
        raise HTTPException(status_code=400, detail="role must be 'admin' or 'member'.")
    if user_repo.get_by_email(payload.email):
        raise HTTPException(status_code=409, detail="An account with that email already exists.")
    return user_repo.create(tenant["id"], payload.email, payload.password, payload.phone, role=payload.role)


@router.patch("/team/{user_id}")
def update_teammate_role(
    user_id: str, payload: RoleUpdatePayload, tenant: dict = Depends(require_tenant_admin)
) -> Any:
    if payload.role not in ("admin", "member"):
        raise HTTPException(status_code=400, detail="role must be 'admin' or 'member'.")
    existing = user_repo.get(user_id)
    if not existing or existing.get("tenant_id") != tenant["id"]:
        raise HTTPException(status_code=404, detail="Teammate not found.")
    user_repo.set_role(user_id, payload.role)
    return user_repo.get_response(user_id)


@router.delete("/team/{user_id}", status_code=204)
def remove_teammate(user_id: str, tenant: dict = Depends(require_tenant_admin)) -> None:
    if not user_repo.delete(user_id, tenant["id"]):
        raise HTTPException(status_code=404, detail="Teammate not found.")


@router.post("/change-password")
def change_password(payload: ChangePasswordPayload, x_api_key: str = Header(default="")) -> Any:
    """Self-service: any logged-in teammate can change their own password,
    no admin involved. Requires their current password, not just a session,
    so a hijacked-but-unattended browser tab can't silently lock them out."""
    user = _require_session_user(x_api_key)
    if not user_repo.verify_password(user, payload.current_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")
    user_repo.set_password(user["_id"], payload.new_password)
    return {"ok": True}
