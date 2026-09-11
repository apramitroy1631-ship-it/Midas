"""Seed two tenants with distinct brands.

Two tenants is the minimum that makes isolation demonstrable: after seeding you
can call the API with each key and confirm neither can see the other's brands,
runs, or assets. Prints both API keys - they are not retrievable afterwards.

    python seed.py
"""
from __future__ import annotations

import json
import uuid

from app.db import tenants as tenant_repo
from app.db.mongo import ensure_indexes, get_db
from app.db.scoped import brands as brands_coll
from app.tenancy.context import tenant_scope

TENANTS = [
    {
        "tenant": {
            "name": "Northwind Talent",
            "slug": "northwind",
            "policy": {
                "autonomy": "autonomous",
                "auto_publish": True,
                "max_revision_cycles": 2,
                "forbidden_claims": [
                    "guaranteed placement",
                    "guaranteed salary increase",
                ],
                "banned_phrases": ["dream job guaranteed"],
                "required_disclaimers": [],
            },
            "autopilot": {"enabled": False, "interval_minutes": 1440},
            "limits": {"monthly_run_quota": 200, "monthly_budget_usd": 250.0},
        },
        "brands": [
            {
                "name": "Northwind Careers",
                "description": "The careers and employer-brand arm of Northwind, a mid-market engineering consultancy.",
                "industry": "Talent / Employer Branding",
                "tone": "Direct, warm, zero corporate filler. Talks to engineers like engineers.",
                "usp": "Engineers here ship to production in week one, not month six.",
                "target_audience": "Backend and platform engineers with 3-8 years experience, currently at large enterprises and bored.",
                "website": "https://northwind.example.com/careers",
                "brand_guidelines": {
                    "visual_style": "Plain, high-contrast, screenshot-heavy. No stock photography of people laughing at laptops.",
                    "preferred_channels": ["linkedin", "blog", "email"],
                    "content_restrictions": [
                        "Never state or imply a specific salary figure",
                        "Never disparage a named competitor or former employer",
                        "No claims about placement rates without a cited source",
                    ],
                },
            }
        ],
    },
    {
        "tenant": {
            "name": "Vertex Robotics",
            "slug": "vertex",
            "policy": {
                "autonomy": "autonomous",
                "auto_publish": True,
                "max_revision_cycles": 2,
                "forbidden_claims": [
                    "eliminates all warehouse injuries",
                    "100% uptime",
                ],
                "banned_phrases": ["revolutionary", "game-changing"],
                "required_disclaimers": [
                    "Performance figures reflect deployed customer averages, not guarantees.",
                ],
            },
            "autopilot": {"enabled": False, "interval_minutes": 720},
            "limits": {"monthly_run_quota": 500, "monthly_budget_usd": 600.0},
        },
        "brands": [
            {
                "name": "Vertex Robotics",
                "description": "Autonomous mobile robots for mid-market warehouse operators.",
                "industry": "B2B SaaS / Warehouse Robotics",
                "tone": "Confident, plain-spoken, operationally specific. Numbers over adjectives.",
                "usp": "Cuts warehouse pick times by 40% without re-racking the floor.",
                "target_audience": "Operations directors at 200-2000 headcount logistics and 3PL companies.",
                "website": "https://vertexrobotics.example.com",
                "brand_guidelines": {
                    "visual_style": "Floor-level photography of real deployments. Charts with real axes.",
                    "preferred_channels": ["linkedin", "email", "blog"],
                    "content_restrictions": [
                        "No safety claims that are not backed by a cited deployment study",
                        "Never imply headcount reduction as the primary benefit",
                        "Do not name customers without written permission",
                    ],
                },
            }
        ],
    },
]


def main() -> None:
    ensure_indexes()
    db = get_db()

    existing = {t["slug"] for t in tenant_repo.list_all()}
    created: list[dict] = []

    for spec in TENANTS:
        slug = spec["tenant"]["slug"]
        if slug in existing:
            print("skip: tenant '" + slug + "' already exists")
            continue

        tenant, api_key = tenant_repo.create(spec["tenant"])
        with tenant_scope(tenant["id"]):
            for brand_spec in spec["brands"]:
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
        created.append({"name": tenant["name"], "slug": slug, "api_key": api_key})

    if not created:
        print("\nNothing to seed. Existing tenants: " + ", ".join(sorted(existing)))
        return

    print("\n" + "=" * 68)
    print("SEEDED. Save these keys - they are not retrievable again.")
    print("=" * 68)
    for t in created:
        print("\n  " + t["name"] + "  (" + t["slug"] + ")")
        print("  X-API-Key: " + t["api_key"])
    print("\n" + "=" * 68)
    print(json.dumps({t["slug"]: t["api_key"] for t in created}, indent=2))


if __name__ == "__main__":
    main()
