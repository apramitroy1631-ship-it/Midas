# app/api/routes_brand.py
from fastapi import APIRouter, Body, HTTPException

from app.schemas.brand import BrandCreate, BrandResponse, BrandSummary, BrandUpdate
from app.services.brand_service import BrandService

router = APIRouter(prefix="/brands", tags=["Brands"])


@router.get("", response_model=list[BrandSummary])
def list_brands():
    """Get all brands: id and name only."""
    service = BrandService()
    return service.list_all()


@router.post("", response_model=BrandResponse)
def create_brand(payload: BrandCreate = Body(default=BrandCreate())):
    """Create & persist brand + memory. Body can be empty."""
    service = BrandService()
    return service.create(payload)


@router.get("/{brand_id}", response_model=BrandResponse)
def get_brand(brand_id: str):
    """Return brand context + memory."""
    service = BrandService()
    out = service.get_by_id(brand_id)
    if out is None:
        raise HTTPException(status_code=404, detail="Brand not found")
    return out


@router.put("/{brand_id}", response_model=BrandResponse)
def update_brand(brand_id: str, payload: BrandUpdate = Body(default=BrandUpdate())):
    """Update brand + memory. Body can be empty."""
    service = BrandService()
    out = service.update(brand_id, payload)
    if out is None:
        raise HTTPException(status_code=404, detail="Brand not found")
    return out


@router.delete("/{brand_id}", status_code=204)
def delete_brand(brand_id: str):
    """Remove brand + memory."""
    service = BrandService()
    ok = service.delete(brand_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Brand not found")
    return None
