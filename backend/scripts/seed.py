"""Seed the one tenant this deployment actually runs for: CMART Solutions.

MIDAS is architected multi-tenant underneath (see app/db/scoped.py — the
isolation guarantee is real and stays in place, not removed), but this
specific deployment is operated for a single company, so this script seeds
exactly one tenant rather than a demo pair. If you ever need a second
tenant — an actual second client, or a staging sandbox — call
POST /v1/admin/tenants directly; the capability was never taken out, only
the "add another tenant" affordance in the console's own UI.

    python -m scripts.seed
"""
from __future__ import annotations

import json
import uuid

from app.db import tenants as tenant_repo
from app.db.mongo import ensure_indexes, get_db
from app.db.scoped import brands as brands_coll
from app.tenancy.context import tenant_scope

TENANT = {
    "tenant": {
        "name": "CMART Solutions Pvt Ltd",
        "slug": "cmart",
        "policy": {
            "autonomy": "autonomous",
            "auto_publish": True,
            "max_revision_cycles": 2,
            "forbidden_claims": [
                "guaranteed ROI",
                "zero downtime",
            ],
            "banned_phrases": ["revolutionary", "game-changing", "cutting-edge"],
            "required_disclaimers": [],
        },
        "autopilot": {"enabled": False, "interval_minutes": 1440},
        "limits": {"monthly_run_quota": 500, "monthly_budget_usd": 500.0},
    },
    "brands": [
        {
            "name": "CMART Solutions",
            "description": "ETRM & CTRM consulting for energy trading and commodity risk "
            "management desks — implementation, integration, and modernization of "
            "trading operations software.",
            "industry": "Energy Trading Software / ETRM-CTRM Consulting",
            "tone": "Confident, direct, modern. Speaks to trading and risk teams as "
            "domain experts, not as a generic enterprise-software buyer.",
            "usp": "Gets ETRM/CTRM systems live in weeks against an industry norm "
            "measured in quarters or years.",
            "target_audience": "Heads of trading operations, CTRM/ETRM buyers, and "
            "commodity risk managers at mid-market to enterprise energy trading firms.",
            "website": "https://cmartsolutions.com",
            "brand_guidelines": {
                "visual_style": "Dark ground, one restrained red accent, bold confident "
                "typography — no stock photography, no generic enterprise-software "
                "imagery.",
                "preferred_channels": ["linkedin", "blog", "email"],
                "content_restrictions": [
                    "No specific implementation timelines without a cited case study",
                    "Never name a client without written permission",
                    "No performance or ROI figures without a documented source",
                ],
            },
        }
    ],
}


def main() -> None:
    ensure_indexes()
    get_db()

    existing = {t["slug"] for t in tenant_repo.list_all()}
    slug = TENANT["tenant"]["slug"]

    if slug in existing:
        print("Nothing to seed — tenant '" + slug + "' already exists.")
        return

    tenant, api_key = tenant_repo.create(TENANT["tenant"])
    with tenant_scope(tenant["id"]):
        for brand_spec in TENANT["brands"]:
            data = dict(brand_spec)
            guidelines = data.pop("brand_guidelines", {})
            brands_coll.insert(
                {
                    "_id": str(uuid.uuid4()),
                    **data,
                    "memory": {
                        "past_campaigns": [],
                        "latest_insights": [],
                        "winning_angles": [],
                        "exhausted_angles": [],
                        "brand_guidelines": guidelines,
                    },
                }
            )

    print("\n" + "=" * 68)
    print("SEEDED. Save this key — it is not retrievable again.")
    print("=" * 68)
    print("\n  " + tenant["name"] + "  (" + slug + ")")
    print("  X-API-Key: " + api_key)
    print("\n" + "=" * 68)
    print(json.dumps({slug: api_key}, indent=2))


if __name__ == "__main__":
    main()
