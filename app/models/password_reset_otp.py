from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    func
)

from app.core.database import Base


class PasswordResetOTP(Base):
    __tablename__ = "password_reset_otps"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    otp_hash = Column(
        String(64),
        nullable=False
    )

    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )

    attempts = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0"
    )

    is_used = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0"
    )

    reset_token_hash = Column(
    String(64),
    nullable=True,
    unique=True
    )

    reset_token_expires_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
