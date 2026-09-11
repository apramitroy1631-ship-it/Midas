# tests/test_scoped_isolation.py
"""Automates the manual curl checks from the isolation walkthrough.

`ScopedCollection` is where multi-tenancy is actually enforced (see
app/db/scoped.py), not in the route handlers. These tests exercise it
directly against a live Mongo so a regression here fails the suite instead
of surfacing as a cross-tenant data leak.

Every test below enters each tenant's scope explicitly and only for the
statement that needs it — no ambient "ambient default tenant" fixture is
held open across a test body, because two such scopes active at once would
just have the second one silently win for the whole test.
"""
from app.db.scoped import ScopedCollection
from app.tenancy.context import tenant_scope

_things = ScopedCollection("_test_things")


def test_insert_stamps_the_active_tenant(tenant_a):
    with tenant_scope(tenant_a):
        doc = _things.insert({"_id": "widget-1", "label": "hello"})
    assert doc["tenant_id"] == tenant_a


def test_a_tenant_cannot_read_another_tenants_document(tenant_a, tenant_b):
    with tenant_scope(tenant_a):
        _things.insert({"_id": "widget-2", "label": "only for tenant_a"})

    with tenant_scope(tenant_b):
        assert _things.find_one({"_id": "widget-2"}) is None
        assert _things.find({"_id": "widget-2"}) == []

    with tenant_scope(tenant_a):
        assert _things.find_one({"_id": "widget-2"}) is not None


def test_list_never_crosses_tenants(tenant_a, tenant_b):
    with tenant_scope(tenant_a):
        _things.insert({"_id": "a-1", "label": "a"})
        _things.insert({"_id": "a-2", "label": "a"})

    with tenant_scope(tenant_b):
        _things.insert({"_id": "b-1", "label": "b"})
        assert _things.count() == 1

    with tenant_scope(tenant_a):
        assert _things.count() == 2


def test_a_supplied_tenant_id_in_the_query_cannot_widen_scope(tenant_a, tenant_b):
    """The defining property: a crafted filter cannot escape the active tenant."""
    with tenant_scope(tenant_b):
        _things.insert({"_id": "victim", "label": "belongs to tenant_b"})

    # tenant_a explicitly asks for tenant_b's id in the filter — must not see it.
    with tenant_scope(tenant_a):
        assert _things.find_one({"_id": "victim", "tenant_id": tenant_b}) is None


def test_update_cannot_move_a_document_to_another_tenant(tenant_a, tenant_b):
    with tenant_scope(tenant_a):
        _things.insert({"_id": "widget-3", "label": "original"})
        _things.update({"_id": "widget-3"}, {"tenant_id": tenant_b, "label": "hijacked"})
        doc = _things.find_one({"_id": "widget-3"})

    assert doc["tenant_id"] == tenant_a
    assert doc["label"] == "hijacked"  # the rest of the update still applies

    with tenant_scope(tenant_b):
        assert _things.find_one({"_id": "widget-3"}) is None


def test_delete_is_scoped(tenant_a, tenant_b):
    with tenant_scope(tenant_b):
        _things.insert({"_id": "widget-4", "label": "tenant_b's"})

    # tenant_a's delete of the same id is a no-op — it never matches.
    with tenant_scope(tenant_a):
        assert _things.delete({"_id": "widget-4"}) == 0

    with tenant_scope(tenant_b):
        assert _things.delete({"_id": "widget-4"}) == 1
