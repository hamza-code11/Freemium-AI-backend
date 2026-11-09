from sqlalchemy.orm import Session

from app.models.business_profile import BusinessProfile


class BusinessProfileRepository:

    @staticmethod
    def create(db: Session, data: dict) -> BusinessProfile:
        profile = BusinessProfile(**data)
        db.add(profile)
        db.flush()  # commit service karegi
        return profile

    @staticmethod
    def get_by_id_for_user(db: Session, business_id: int, user_id: int):
        return (
            db.query(BusinessProfile)
            .filter(
                BusinessProfile.id == business_id,
                BusinessProfile.user_id == user_id
            )
            .first()
        )

    @staticmethod
    def update(db: Session, profile: BusinessProfile, data: dict) -> BusinessProfile:
        for key, value in data.items():
            setattr(profile, key, value)
        db.flush()
        return profile
    