import hmac
from pathlib import Path
from uuid import uuid4, UUID
from datetime import datetime, timedelta, timezone

from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.config import REFRESH_TOKEN_EXPIRE_DAYS
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.repositories.user_session_repository import UserSessionRepository
from app.repositories.business_profile_repository import BusinessProfileRepository


class UserService:

    @staticmethod
    def register_user(db: Session, user_data: dict):
        business_data = user_data.pop("business")

        user_data["email"] = user_data["email"].strip().lower()

        existing_user = UserRepository.get_by_email(db, user_data["email"])

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )

        user_data["password"] = hash_password(user_data["password"])

        try:
            # User + Business Profile ek hi transaction mein
            user = UserRepository.create(db, user_data, commit=False)

            BusinessProfileRepository.create(
                db,
                {**business_data, "user_id": user.id}
            )

            db.commit()
            db.refresh(user)

            return user

        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )

        except Exception:
            db.rollback()
            raise



    @staticmethod
    def login_user(db: Session, email: str, password: str):
        email = email.strip().lower()
        user = UserRepository.get_by_email(db, email)

        # Timing attack se bachne ke liye dummy verify
        DUMMY_HASH = "$2b$12$C6UzMDM.H6dfI/f/IKcEeO5pQe1M0cY5i8m0Qe3lQ1F8y3b5rGq6W"
        if not user:
            verify_password(password, DUMMY_HASH)
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not verify_password(password, user.password):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not user or not verify_password(password, user.password):
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        session_id, refresh_token, token_hash = create_refresh_token()

        expires_at = datetime.now(timezone.utc) + timedelta(
            days=REFRESH_TOKEN_EXPIRE_DAYS
        )

        try:
            UserSessionRepository.create(
                db,
                {
                    "id": session_id,
                    "user_id": user.id,
                    "refresh_token_hash": token_hash,
                    "expires_at": expires_at,
                }
            )

            access_token = create_access_token(
                data={"sub": str(user.id)}
            )

            db.commit()

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": user
            }

        except Exception:
            db.rollback()
            raise



    @staticmethod
    def refresh_access_token(db: Session, refresh_token: str):

        try:
            session_id, secret = refresh_token.split(".", 1)
            session_id = str(UUID(session_id))
        except (ValueError, AttributeError):
            raise HTTPException(
                status_code=401,
                detail="Invalid refresh token"
            )

        try:
            user_session = UserSessionRepository.get_by_id(
                db,
                session_id,
                lock=True
            )

            if not user_session:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid refresh token"
                )

            now = datetime.now(timezone.utc)
            expires_at = user_session.expires_at

            # MySQL may return a naive datetime.
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            if user_session.revoked_at is not None:
                raise HTTPException(
                    status_code=401,
                    detail="Session has been revoked"
                )

            if expires_at <= now:
                user_session.revoked_at = now
                db.commit()

                raise HTTPException(
                    status_code=401,
                    detail="Refresh token expired. Please login again."
                )

            token_hash = hash_refresh_token(secret)

            if not hmac.compare_digest(
                token_hash,
                user_session.refresh_token_hash
            ):
                user_session.revoked_at = now
                db.commit()

                raise HTTPException(
                    status_code=401,
                    detail="Refresh token reuse detected. Please login again."
                )

            _, new_refresh_token, new_token_hash = create_refresh_token(
                session_id=session_id
            )

            new_expiry = now + timedelta(
                days=REFRESH_TOKEN_EXPIRE_DAYS
            )

            UserSessionRepository.rotate(
                db,
                user_session,
                new_token_hash,
                new_expiry
            )

            access_token = create_access_token(
                data={"sub": str(user_session.user_id)}
            )

            db.commit()

            return {
                "access_token": access_token,
                "refresh_token": new_refresh_token
            }

        except HTTPException:
            raise

        except Exception:
            db.rollback()
            raise


    @staticmethod
    def logout_user(db: Session, refresh_token: str | None) -> None:

        if not refresh_token:
            return

        try:
            session_id, secret = refresh_token.split(".", 1)
            session_id = str(UUID(session_id))
        except (ValueError, AttributeError):
            return

        try:
            user_session = UserSessionRepository.get_by_id(
                db,
                session_id,
                lock=True
            )

            if not user_session or user_session.revoked_at is not None:
                return

            token_hash = hash_refresh_token(secret)

            if not hmac.compare_digest(
                token_hash,
                user_session.refresh_token_hash
            ):
                return

            UserSessionRepository.revoke(db, user_session)
            db.commit()

        except Exception:
            db.rollback()
            raise




    @staticmethod
    def logout_all_devices(db: Session, user_id: int) -> int:
        try:
            revoked_count = UserSessionRepository.revoke_all_for_user(
                db=db,
                user_id=user_id
            )

            db.commit()
            return revoked_count

        except Exception:
            db.rollback()
            raise




    @staticmethod
    async def save_profile_image(image: UploadFile) -> str:
        from PIL import Image
        import io

        MAX_SIZE = 2 * 1024 * 1024
        allowed_formats = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}

        file_content = await image.read(MAX_SIZE + 1)

        if len(file_content) > MAX_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image size must not exceed 2MB"
            )

        try:
            img = Image.open(io.BytesIO(file_content))
            img.verify()
            img_format = img.format
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image file"
            )

        if img_format not in allowed_formats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only JPG, PNG and WEBP images are allowed"
            )

        filename = f"{uuid4().hex}{allowed_formats[img_format]}"

        upload_dir = Path(__file__).resolve().parents[2] / "uploads" / "users"
        upload_dir.mkdir(parents=True, exist_ok=True)

        (upload_dir / filename).write_bytes(file_content)

        return filename



    @staticmethod
    async def update_profile(
        db: Session,
        user: User,
        name: str | None = None,
        image: UploadFile | None = None
    ):
        image_filename = None
        old_image = user.image

        if image is not None:
            image_filename = await UserService.save_profile_image(image)

        updated_user = UserRepository.update_profile(
            db=db,
            user=user,
            name=name,
            image=image_filename
        )

        # Purani image delete karo
        if image_filename and old_image:
            old_path = (
                Path(__file__).resolve().parents[2] / "uploads" / "users" / old_image
            )
            try:
                if old_path.is_file():
                    old_path.unlink()
            except OSError:
                pass

        return updated_user


    @staticmethod
    def change_password(
        db: Session,
        user: User,
        current_password: str,
        new_password: str
    ):
        if not verify_password(current_password, user.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )

        try:
            user.password = hash_password(new_password)

            UserSessionRepository.revoke_all_for_user(
                db=db,
                user_id=user.id
            )

            db.commit()
            db.refresh(user)

            return {"message": "Password changed successfully. Please login again."}

        except Exception:
            db.rollback()
            raise


