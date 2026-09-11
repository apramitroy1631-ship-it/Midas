# app/schemas/campaign.py
from pydantic import BaseModel

class CampaignCreate(BaseModel):
    brand_id: str
    goal: str
    target_audience: str
    budget: float

class CampaignResponse(BaseModel):
    id: str
    status: str