# app/api/routes_brands.py
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.db.scoped import brands as brands_coll
from app.schemas.brand import BrandCreate, BrandResponse, BrandUpdate
from app.tenancy.auth import require_tenant

router = APIRouter(prefix="/v1/brands", tags=["Brands"], dependencies=[Depends(require_tenant)])


def _to_response(doc: dict[str, Any]) -> BrandResponse:
    out = dict(doc)
    out["id"] = str(doc["_id"])
    out.pop("_id", None)
    return BrandResponse(**out)


@router.get("", response_model=list[BrandResponse])
def list_brands() -> Any:
    return [_to_response(d) for d in brands_coll.find(sort=[("created_at", 1)])]


@router.post("", response_model=BrandResponse, status_code=201)
def create_brand(payload: BrandCreate) -> Any:
    data = payload.model_dump()
    guidelines = data.pop("brand_guidelines", {}) or {}
    insights = data.pop("latest_insights", []) or []
    doc = brands_coll.insert(
        {
            "_id": str(uuid.uuid4()),
            **data,
            "memory": {
                "past_campaigns": [],
                "latest_insights": insights,
                "winning_angles": [],
                "exhausted_angles": [],
                "brand_guidelines": guidelines,
            },
        }
    )
    return _to_response(doc)


@router.get("/{brand_id}", response_model=BrandResponse)
def get_brand(brand_id: str) -> Any:
    doc = brands_coll.find_one({"_id": brand_id})
    if doc is None:
        raise HTTPException(status_code=404, detail="Brand not found.")
    return _to_response(doc)


@router.patch("/{brand_id}", response_model=BrandResponse)
def update_brand(brand_id: str, payload: BrandUpdate) -> Any:
    existing = brands_coll.find_one({"_id": brand_id})
    if existing is None:
        raise HTTPException(status_code=404, detail="Brand not found.")

    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    guidelines = changes.pop("brand_guidelines", None)
    insights = changes.pop("latest_insights", None)

    if guidelines is not None or insights is not None:
        memory = dict(existing.get("memory") or {})
        if guidelines is not None:
            memory["brand_guidelines"] = guidelines
        if insights is not None:
            memory["latest_insights"] = insights
        changes["memory"] = memory

    brands_coll.update({"_id": brand_id}, changes)
    return _to_response(brands_coll.find_one({"_id": brand_id}))


@router.delete("/{brand_id}", status_code=204)
def delete_brand(brand_id: str) -> None:
    if not brands_coll.delete({"_id": brand_id}):
        raise HTTPException(status_code=404, detail="Brand not found.")
