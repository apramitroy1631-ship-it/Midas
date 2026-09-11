# app/services/brand_service.py
import uuid

from fastapi import HTTPException

from app.db.repositories.brand_repo import create as repo_create
from app.db.repositories.brand_repo import delete as repo_delete
from app.db.repositories.brand_repo import get_by_id as repo_get_by_id
from app.db.repositories.brand_repo import list_all as repo_list_all
from app.db.repositories.brand_repo import update as repo_update
from app.schemas.brand import BrandCreate, BrandResponse, BrandSummary, BrandUpdate


def _create_to_repo_data(payload: BrandCreate, brand_id: str) -> dict:
    return {
        "id": brand_id,
        "name": payload.name,
        "description": payload.description,
        "industry": payload.industry,
        "tone": payload.tone,
        "usp": payload.usp,
        "target_audience": payload.target_audience,
        "brand_guidelines": payload.brand_guidelines,
        "latest_insights": payload.latest_insights,
    }


def _update_to_repo_data(payload: BrandUpdate) -> dict:
    data: dict = {}
    if payload.name is not None:
        data["name"] = payload.name
    if payload.description is not None:
        data["description"] = payload.description
    if payload.industry is not None:
        data["industry"] = payload.industry
    if payload.tone is not None:
        data["tone"] = payload.tone
    if payload.usp is not None:
        data["usp"] = payload.usp
    if payload.target_audience is not None:
        data["target_audience"] = payload.target_audience
    if payload.brand_guidelines is not None:
        data["brand_guidelines"] = payload.brand_guidelines
    if payload.latest_insights is not None:
        data["latest_insights"] = payload.latest_insights
    return data


class BrandService:
    def create(self, payload: BrandCreate) -> BrandResponse:
        """Create & persist brand with full document shape (create params only)."""
        brand_id = str(uuid.uuid4())
        data = _create_to_repo_data(payload, brand_id)
        doc = repo_create(data)
        return BrandResponse(**doc)

    def list_all(self) -> list[BrandSummary]:
        """Return all brands (id and name only)."""
        docs = repo_list_all()
        return [BrandSummary(**d) for d in docs]

    def get_by_id(self, brand_id: str) -> BrandResponse | None:
        """Return full brand object (context + memory + timestamps)."""
        doc = repo_get_by_id(brand_id)
        if doc is None:
            raise HTTPException(status_code=400, detail="Brand not present")
        return BrandResponse(**doc)

    

    def update(self, brand_id: str, payload: BrandUpdate) -> BrandResponse | None:
        """Update brand (partial)."""
        data = _update_to_repo_data(payload)
        if not data:
            doc = repo_get_by_id(brand_id)
            return BrandResponse(**doc) if doc else None
        doc = repo_update(brand_id, data)
        if doc is None:
            return None
        return BrandResponse(**doc)

    def delete(self, brand_id: str) -> bool:
        """Remove brand + memory."""
        return repo_delete(brand_id)
