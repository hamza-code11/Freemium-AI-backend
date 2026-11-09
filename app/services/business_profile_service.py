# app/services/business_profile_service.py

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.business_profile_repository import BusinessProfileRepository


class BusinessProfileService:

    # 🔥 NAYA FUNCTION
    @staticmethod
    def create_business_profile(db: Session, user_id: int, data: dict):
        try:
            # User ID ko data me add karein
            data["user_id"] = user_id
            profile = BusinessProfileRepository.create(db, data)
            db.commit()
            db.refresh(profile)
            return profile
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def update_business_profile(
        db: Session,
        user_id: int,
        business_id: int,
        data: dict
    ):
        # ... (purana code same rahega)
        if not data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided to update"
            )

        profile = BusinessProfileRepository.get_by_id_for_user(
            db, business_id, user_id
        )

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business profile not found"
            )

        try:
            BusinessProfileRepository.update(db, profile, data)
            db.commit()
            db.refresh(profile)
            return profile

        except Exception:
            db.rollback()
            raise