import secrets
import hmac
import hashlib

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import SECRET_KEY
from app.repositories.user_repository import UserRepository
from app.repositories.password_reset_otp_repository import PasswordResetOTPRepository
from app.services.email_service import EmailService
from app.models.password_reset_otp import PasswordResetOTP
from app.core.security import hash_password
from app.repositories.user_session_repository import UserSessionRepository

import logging

logger = logging.getLogger("uvicorn.error")


class PasswordResetService:

    @staticmethod
    def generate_otp() -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    @staticmethod
    def hash_otp(otp: str) -> str:
        return hmac.new(
            SECRET_KEY.encode(),
            otp.encode(),
            hashlib.sha256
        ).hexdigest()




    @staticmethod
    def request_password_reset(db: Session, email: str, background_tasks=None):
        email = email.strip().lower()
        generic = {"message": "If the email is registered, an OTP has been sent."}

        user = UserRepository.get_by_email(db, email)

        if not user:
            logger.warning("RESET: user not found for %s", email)
            return generic

        latest = (
            db.query(PasswordResetOTP)
            .filter(PasswordResetOTP.user_id == user.id)
            .order_by(PasswordResetOTP.created_at.desc())
            .first()
        )

        if latest and latest.created_at:
            created = latest.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            elapsed = (datetime.now(timezone.utc) - created).total_seconds()
            if 0 <= elapsed < 60:
                logger.warning("RESET: cooldown active for %s", email)
                return generic

        otp = PasswordResetService.generate_otp()
        otp_hash = PasswordResetService.hash_otp(otp)

        PasswordResetOTPRepository.invalidate_all_for_user(db, user.id)

        PasswordResetOTPRepository.create(
            db,
            {
                "user_id": user.id,
                "otp_hash": otp_hash,
                "created_at": datetime.now(timezone.utc),
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
                "attempts": 0,
                "is_used": False
            }
        )

        logger.warning("RESET: sending otp to %s", user.email)
        PasswordResetService._send_otp_safe(user.email, otp)
        logger.warning("RESET: send finished for %s", user.email)

        return generic


    @staticmethod
    def _send_otp_safe(email: str, otp: str):
        try:
            EmailService.send_password_reset_otp(email=email, otp=otp)
        except Exception:
            logger.exception("OTP email failed")





    @staticmethod
    def verify_reset_otp(
        db: Session,
        email: str,
        otp: str
    ):
        email = email.strip().lower()
        user = UserRepository.get_by_email(db, email)

        if not user:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired OTP"
            )

        reset_otp = PasswordResetOTPRepository.get_latest_by_user_id(
            db,
            user.id,
            lock=True
        )

        if not reset_otp:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired OTP"
            )

        now = datetime.now(timezone.utc)
        expires_at = reset_otp.expires_at

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if now >= expires_at:
            reset_otp.is_used = True
            db.commit()
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired OTP"
            )

        submitted_hash = PasswordResetService.hash_otp(otp)

        if not hmac.compare_digest(submitted_hash, reset_otp.otp_hash):
            reset_otp.attempts += 1

            if reset_otp.attempts >= 5:
                reset_otp.is_used = True

            db.commit()
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired OTP"
            )

        reset_token = secrets.token_urlsafe(32)

        reset_otp.reset_token_hash = PasswordResetService.hash_otp(reset_token)
        reset_otp.reset_token_expires_at = now + timedelta(minutes=10)
        reset_otp.is_used = True

        db.commit()

        return {
            "message": "OTP verified successfully",
            "reset_token": reset_token
        }


    @staticmethod
    def reset_password(
        db: Session,
        reset_token: str,
        new_password: str
    ):
        token_hash = PasswordResetService.hash_otp(reset_token)

        try:
            # Lock token row to prevent concurrent reuse
            reset_otp = PasswordResetOTPRepository.get_by_reset_token_hash(
                db,
                token_hash
            )

            if not reset_otp:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid or expired reset token"
                )

            now = datetime.now(timezone.utc)
            token_expires_at = reset_otp.reset_token_expires_at

            if token_expires_at is None:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid or expired reset token"
                )

            if token_expires_at.tzinfo is None:
                token_expires_at = token_expires_at.replace(
                    tzinfo=timezone.utc
                )

            if now >= token_expires_at:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid or expired reset token"
                )

            user = UserRepository.get_by_id(
                db,
                reset_otp.user_id
            )

            if not user:
                raise HTTPException(
                    status_code=404,
                    detail="User not found"
                )

            # Update password
            user.password = hash_password(new_password)

            # Invalidate reset token
            reset_otp.reset_token_hash = None
            reset_otp.reset_token_expires_at = None

            # Revoke all refresh sessions
            UserSessionRepository.revoke_all_for_user(
                db=db,
                user_id=user.id
            )

            db.commit()

            return {
                "message": "Password reset successfully. Please login again."
            }

        except Exception:
            db.rollback()
            raise


