from sqlalchemy.orm import Session, joinedload
from app.models.user import User
from datetime import datetime, timezone


class UserRepository:

    @staticmethod
    def get_by_email(db: Session, email: str):
        return db.query(User).filter(User.email == email).first()



    @staticmethod
    def create(db: Session, user_data: dict, commit: bool = True):
        user = User(**user_data)

        db.add(user)

        if commit:
            db.commit()
            db.refresh(user)
        else:
            db.flush()  # id mil jaye, commit baad mein

        return user



    @staticmethod
    def update_profile(
        db: Session,
        user: User,
        name: str | None = None,
        image: str | None = None
    ) -> User:
        if name is not None:
            user.name = name

        if image is not None:
            user.image = image

        db.commit()
        db.refresh(user)

        return user



    @staticmethod
    def get_by_id(db: Session, user_id: int):
        return (
            db.query(User)
            .options(joinedload(User.business_profiles))
            .filter(User.id == user_id)
            .first()
        )

    