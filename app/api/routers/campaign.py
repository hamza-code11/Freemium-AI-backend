# app/api/routers/campaign.py

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_access_token
from app.services.campaign_service import CampaignService

router = APIRouter(
    prefix="/api/campaigns",
    tags=["AI Campaign Planner"]
)


class CampaignGenerateRequest(BaseModel):
    campaign_name: str = Field(..., min_length=2, max_length=150)
    objective: str
    product_service: str
    target_audience: List[str] = []
    channels: List[str] = []
    budget: float = 0
    currency: str = "USD"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    tone: str
    notes: Optional[str] = None
    business_id: Optional[int] = None


@router.post("/generate", status_code=status.HTTP_200_OK)
def generate_campaign(
    data: CampaignGenerateRequest,
    user_id: int = Depends(verify_access_token),
    db: Session = Depends(get_db)
):
    # Date string ko datetime me convert karein (agar diya hai)
    start_date = datetime.fromisoformat(data.start_date) if data.start_date else None
    end_date = datetime.fromisoformat(data.end_date) if data.end_date else None
    
    campaign_dict = data.model_dump()
    campaign_dict["start_date"] = start_date
    campaign_dict["end_date"] = end_date

    return CampaignService.generate_campaign_plan(
        db=db,
        user_id=user_id,
        campaign_data=campaign_dict
    )