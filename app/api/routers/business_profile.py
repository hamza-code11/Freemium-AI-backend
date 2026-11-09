# app/api/routers/business_profile.py

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_access_token
from app.schemas.user import BusinessProfileUpdate, BusinessProfileResponse, BusinessProfileCreate
from app.services.business_profile_service import BusinessProfileService

router = APIRouter(
    prefix="/api/business-profiles",
    tags=["Business Profile"]
)

# 🔥 NAYA ROUTE (Create New Business)
@router.post("/", response_model=BusinessProfileResponse, status_code=status.HTTP_201_CREATED)
def create_business_profile(
    data: BusinessProfileCreate,
    user_id: int = Depends(verify_access_token),
    db: Session = Depends(get_db)
):
    return BusinessProfileService.create_business_profile(
        db=db,
        user_id=user_id,
        data=data.model_dump()
    )

# Purana Update Route (Waisa hi rahega)
@router.patch("/{business_id}", response_model=BusinessProfileResponse)
def update_business_profile(
    business_id: int,
    data: BusinessProfileUpdate,
    user_id: int = Depends(verify_access_token),
    db: Session = Depends(get_db)
):
    return BusinessProfileService.update_business_profile(
        db=db,
        user_id=user_id,
        business_id=business_id,
        data=data.model_dump(exclude_unset=True)
    )