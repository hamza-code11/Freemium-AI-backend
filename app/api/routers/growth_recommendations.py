# app/api/routers/growth_recommendations.py

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_access_token
from app.schemas.growth_recommendation import (
    GrowthRecommendationRequest,
    GrowthRecommendationResponse,
)
from app.services.growth_recommendation_service import GrowthRecommendationService

router = APIRouter(
    prefix="/api/growth-recommendations",
    tags=["AI Growth Recommendations"],
)


@router.post(
    "/generate",
    response_model=GrowthRecommendationResponse,
    status_code=status.HTTP_200_OK,
)
def generate_growth_recommendations(
    data: GrowthRecommendationRequest,
    user_id: int = Depends(verify_access_token),
    db: Session = Depends(get_db),
):
    return GrowthRecommendationService.generate_recommendations(
        db=db,
        user_id=user_id,
        payload=data,
    )
