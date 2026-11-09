from sqlalchemy.orm import Session
from app.models.password_reset_otp import PasswordResetOTP


class PasswordResetOTPRepository:

    @staticmethod
    def create(db: Session, otp_data: dict):
        otp = PasswordResetOTP(**otp_data)

        db.add(otp)
        db.commit()
        db.refresh(otp)

        return otp



    @staticmethod
    def get_latest_by_user_id(db: Session, user_id: int, lock: bool = False):
        query = (
            db.query(PasswordResetOTP)
            .filter(
                PasswordResetOTP.user_id == user_id,
                PasswordResetOTP.is_used == False
            )
            .order_by(PasswordResetOTP.created_at.desc(), PasswordResetOTP.id.desc())
        )

        if lock:
            query = query.with_for_update()

        return query.first()



    @staticmethod
    def get_by_reset_token_hash(db: Session, token_hash: str):
        return (
            db.query(PasswordResetOTP)
            .filter(
                PasswordResetOTP.reset_token_hash == token_hash
            )
            .with_for_update()
            .first()
        )




    @staticmethod
    def invalidate_all_for_user(db: Session, user_id: int):
        db.query(PasswordResetOTP).filter(
            PasswordResetOTP.user_id == user_id
        ).update(
            {
                "is_used": True,
                "reset_token_hash": None,
                "reset_token_expires_at": None,
            },
            synchronize_session=False
        )

        db.flush()


        