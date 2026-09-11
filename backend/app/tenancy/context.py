# app/tenancy/context.py
"""Ambient tenant binding.

Every data access in this service runs inside a tenant scope. The scope is
held in a ContextVar rather than threaded through every function signature,
so that a repository can *enforce* isolation instead of trusting each caller
to remember a `tenant_id=` argument. Forgetting to bind raises; it never
silently reads across tenants.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

_current_tenant: ContextVar[str | None] = ContextVar("current_tenant", default=None)


class TenantScopeError(RuntimeError):
    """Raised when tenant-scoped data is touched outside a tenant scope."""


def set_tenant(tenant_id: str) -> object:
    return _current_tenant.set(tenant_id)


def reset_tenant(token: object) -> None:
    _current_tenant.reset(token)  # type: ignore[arg-type]


def current_tenant() -> str:
    tid = _current_tenant.get()
    if not tid:
        raise TenantScopeError(
            "No tenant bound to this context. Tenant-scoped data cannot be read "
            "or written without an active scope."
        )
    return tid


def current_tenant_or_none() -> str | None:
    return _current_tenant.get()


@contextmanager
def tenant_scope(tenant_id: str) -> Iterator[str]:
    """Bind a tenant for the duration of the block.

    Used by the background scheduler, which has no HTTP request to carry the
    tenant, and by any worker running on behalf of a tenant.
    """
    token = set_tenant(tenant_id)
    try:
        yield tenant_id
    finally:
        reset_tenant(token)
