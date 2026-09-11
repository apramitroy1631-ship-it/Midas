# tests/test_tenancy_context.py
"""The ambient tenant binding that every scoped query relies on.

If this contract breaks, every isolation guarantee in the system breaks with
it, so it gets tested in isolation from Mongo entirely.
"""
import pytest

from app.tenancy.context import (
    TenantScopeError,
    current_tenant,
    current_tenant_or_none,
    tenant_scope,
)


def test_no_scope_raises():
    with pytest.raises(TenantScopeError):
        current_tenant()


def test_no_scope_returns_none_for_the_soft_variant():
    assert current_tenant_or_none() is None


def test_scope_binds_and_releases():
    assert current_tenant_or_none() is None
    with tenant_scope("acme"):
        assert current_tenant() == "acme"
    assert current_tenant_or_none() is None


def test_nested_scopes_restore_the_outer_binding():
    with tenant_scope("outer"):
        with tenant_scope("inner"):
            assert current_tenant() == "inner"
        assert current_tenant() == "outer"


def test_scope_releases_even_if_the_block_raises():
    with pytest.raises(ValueError):
        with tenant_scope("acme"):
            raise ValueError("boom")
    assert current_tenant_or_none() is None
