from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    func
)
from uuid import uuid4

from app.core.database import Base


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4())
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    refresh_token_hash = Column(
        String(64),
        nullable=False,
        unique=True
    )

    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )

    revoked_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    last_used_at = Column(
        DateTime(timezone=True),
        nullable=True
    )