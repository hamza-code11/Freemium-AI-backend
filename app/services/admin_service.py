from datetime import datetime, timedelta, timezone
from pathlib import Path
import hmac
import io
from uuid import uuid4

from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token
from app.models.admin import Admin
from app.repositories.admin_repository import AdminRepository
from app.services.password_reset_service import PasswordResetService

GENERIC_MSG = {"message": "If the email is registered, an OTP has been sent."}
INVALID_OTP = "Invalid or expired OTP"
_DUMMY_HASH = hash_password("dummy-password")


def _aware(dt):
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class AdminService:

    @staticmethod
    def login(db: Session, email: str, password: str):
        email = email.strip().lower()
        admin = AdminRepository.get_by_email(db, email)

        if not admin:
            verify_password(password, _DUMMY_HASH)
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not verify_password(password, admin.password):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        token = create_access_token(
            data={"sub": f"admin:{admin.id}", "role": "admin"}
        )

        return {"access_token": token, "token_type": "bearer"}

    @staticmethod
    def forgot_password(db: Session, email: str, background_tasks):
        email = email.strip().lower()
        admin = AdminRepository.get_by_email(db, email)

        if not admin:
            return GENERIC_MSG

        # 60 second cooldown (OTP 5 min ka hai, to 4 min se zyada bacha ho = abhi bheja gaya)
        expires = _aware(admin.reset_otp_expires_at)
        now = datetime.now(timezone.utc)
        if expires and (expires - now) > timedelta(minutes=4):
            return GENERIC_MSG

        otp = PasswordResetService.generate_otp()
        admin.reset_otp_hash = PasswordResetService.hash_otp(otp)
        admin.reset_otp_expires_at = now + timedelta(minutes=5)
        admin.reset_otp_attempts = 0
        db.commit()

        background_tasks.add_task(
            PasswordResetService._send_otp_safe, admin.email, otp
        )

        return GENERIC_MSG

    @staticmethod
    def reset_password(db: Session, email: str, otp: str, new_password: str):
        email = email.strip().lower()

        try:
            admin = AdminRepository.get_by_email(db, email, lock=True)

            if not admin or not admin.reset_otp_hash:
                raise HTTPException(status_code=400, detail=INVALID_OTP)

            now = datetime.now(timezone.utc)
            expires = _aware(admin.reset_otp_expires_at)

            if not expires or now >= expires or admin.reset_otp_attempts >= 5:
                admin.reset_otp_hash = None
                admin.reset_otp_expires_at = None
                db.commit()
                raise HTTPException(status_code=400, detail=INVALID_OTP)

            if not hmac.compare_digest(
                PasswordResetService.hash_otp(otp), admin.reset_otp_hash
            ):
                admin.reset_otp_attempts += 1
                db.commit()
                raise HTTPException(status_code=400, detail=INVALID_OTP)

            admin.password = hash_password(new_password)
            admin.reset_otp_hash = None
            admin.reset_otp_expires_at = None
            admin.reset_otp_attempts = 0
            db.commit()

            return {"message": "Password reset successfully. Please login again."}

        except HTTPException:
            raise
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def change_password(db: Session, admin: Admin, current_password: str, new_password: str):
        if not verify_password(current_password, admin.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )

        try:
            admin.password = hash_password(new_password)
            db.commit()
            return {"message": "Password changed successfully"}
        except Exception:
            db.rollback()
            raise

    @staticmethod
    async def update_profile(
        db: Session,
        admin: Admin,
        name: str | None,
        image: UploadFile | None
    ):
        from PIL import Image

        MAX_SIZE = 2 * 1024 * 1024
        allowed = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
        upload_dir = Path(__file__).resolve().parents[2] / "uploads" / "admins"
        old_image = admin.image
        new_filename = None

        if image is not None:
            content = await image.read(MAX_SIZE + 1)

            if len(content) > MAX_SIZE:
                raise HTTPException(status_code=400, detail="Image size must not exceed 2MB")

            try:
                img = Image.open(io.BytesIO(content))
                img.verify()
                fmt = img.format
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid image file")

            if fmt not in allowed:
                raise HTTPException(status_code=400, detail="Only JPG, PNG and WEBP images are allowed")

            upload_dir.mkdir(parents=True, exist_ok=True)
            new_filename = f"{uuid4().hex}{allowed[fmt]}"
            (upload_dir / new_filename).write_bytes(content)

        try:
            if name is not None:
                admin.name = name.strip()
            if new_filename:
                admin.image = new_filename
            db.commit()
            db.refresh(admin)
        except Exception:
            db.rollback()
            raise

        if new_filename and old_image:
            try:
                (upload_dir / old_image).unlink(missing_ok=True)
            except OSError:
                pass

        return admin

    