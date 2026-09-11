# app/api/routes_campaign.py
from fastapi import APIRouter, HTTPException

from app.schemas.campaign import CampaignCreate
from app.services.campaign_service import CampaignService

router = APIRouter(prefix="/brands/{brand_id}/campaigns", tags=["Campaigns"])


@router.get("")
def get_all_campaigns(brand_id: str):
    """Get all campaigns for the brand."""
    service = CampaignService()
    return service.get_all_campaigns(brand_id=brand_id)


@router.get("/{campaign_id}")
def get_campaign_by_id(brand_id: str, campaign_id: str):
    """Get a single campaign by ID."""
    service = CampaignService()
    campaign = service.get_campaign_by_id(brand_id=brand_id, campaign_id=campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.get("brand_id") != brand_id:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.post("/")
def create_campaign(brand_id: str, payload: CampaignCreate):
    """Create a campaign for the brand (brand_id in path overrides body)."""
    service = CampaignService()
    payload.brand_id = brand_id
    return service.create_campaign(payload)


@router.delete("/{campaign_id}", status_code=204)
def delete_campaign_by_id(brand_id: str, campaign_id: str):
    """Delete a campaign by ID."""
    service = CampaignService()
    campaign = service.get_campaign_by_id(campaign_id)
    if campaign is None or campaign.get("brand_id") != brand_id:
        raise HTTPException(status_code=404, detail="Campaign not found")
    service.delete_campaign_by_id(campaign_id)
    return None