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

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.db import sessions as session_repo
from app.db import tenants as tenant_repo
from app.db import users as user_repo
from app.tenancy.auth import require_admin

router = APIRouter(prefix="/v1/auth", tags=["Auth"])


class RegisterPayload(BaseModel):
    email: str
    password: str = Field(min_length=8)
    phone: str | None = None


class LoginPayload(BaseModel):
    email: str
    password: str


@router.post("/register", status_code=201, dependencies=[Depends(require_admin)])
def register(payload: RegisterPayload) -> Any:
    """Admin-only: create one teammate's login for this deployment's tenant."""
    if user_repo.get_by_email(payload.email):
        raise HTTPException(status_code=409, detail="An account with that email already exists.")

    tenants = tenant_repo.list_all()
    if not tenants:
        raise HTTPException(status_code=400, detail="No tenant exists yet — seed one first.")

    return user_repo.create(tenants[0]["id"], payload.email, payload.password, payload.phone)


@router.post("/login")
def login(payload: LoginPayload) -> Any:
    user = user_repo.get_by_email(payload.email)
    if not user or not user_repo.verify_password(user, payload.password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    tenant = tenant_repo.get(user["tenant_id"])
    if tenant is None or tenant.get("status") != "active":
        raise HTTPException(status_code=403, detail="Tenant is not active.")

    token = session_repo.create(user["tenant_id"], user["_id"])
    return {"session_token": token, "tenant_name": tenant["name"], "email": user["email"]}
