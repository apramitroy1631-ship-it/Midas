# tests/conftest.py
"""Shared fixtures.

Tests that touch MongoDB point at a dedicated `buildx_test` database (never
`buildx`) and drop it after the session, so running the suite never disturbs
real tenant data and never needs a special "test mode" flag in application code.
"""
from __future__ import annotations

import uuid

import pytest

from app.core.settings import settings

# Redirect before any app module that reads settings.mongodb_db_name at import
# time gets a chance to cache the wrong value.
settings.mongodb_db_name = "buildx_test"

from app.db.mongo import get_client  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _test_database():
    yield
    get_client().drop_database("buildx_test")


def _fresh_tenant_id() -> str:
    return "test-tenant-" + uuid.uuid4().hex[:8]


@pytest.fixture
def tenant_a() -> str:
    """A fresh tenant id, unbound — tests enter its scope explicitly via
    `with tenant_scope(tenant_a):` rather than inheriting an ambient one, so
    two of these fixtures in the same test can never silently shadow
    each other."""
    return _fresh_tenant_id()


@pytest.fixture
def tenant_b() -> str:
    return _fresh_tenant_id()
