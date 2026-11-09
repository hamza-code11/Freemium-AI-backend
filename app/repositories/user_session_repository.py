
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.user_session import UserSession


class UserSessionRepository:

    @staticmethod
    def create(db: Session, session_data: dict) -> UserSession:
        user_session = UserSession(**session_data)
        db.add(user_session)
        db.flush()
        return user_session

    @staticmethod
    def get_by_id(
        db: Session,
        session_id: str,
        lock: bool = False
    ) -> UserSession | None:
        query = db.query(UserSession).filter(
            UserSession.id == session_id
        )

        if lock:
            query = query.with_for_update()

        return query.first()

    @staticmethod
    def rotate(
        db: Session,
        user_session: UserSession,
        token_hash: str,
        expires_at: datetime
    ) -> UserSession:
        user_session.refresh_token_hash = token_hash
        user_session.expires_at = expires_at
        user_session.last_used_at = datetime.now(timezone.utc)

        db.flush()
        return user_session


    @staticmethod
    def revoke(
        db: Session,
        user_session: UserSession
    ) -> None:
        user_session.revoked_at = datetime.now(timezone.utc)
        db.flush()



    @staticmethod
    def revoke_all_for_user(db: Session, user_id: int) -> int:
        revoked_at = datetime.now(timezone.utc)

        count = (
            db.query(UserSession)
            .filter(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None)
            )
            .update(
                {"revoked_at": revoked_at},
                synchronize_session=False
            )
        )

        db.flush()
        return count


