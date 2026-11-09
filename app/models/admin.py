from sqlalchemy import Column, Integer, String, DateTime, func

from app.core.database import Base


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    image = Column(String(255), nullable=True)

    # forgot password OTP
    reset_otp_hash = Column(String(64), nullable=True)
    reset_otp_expires_at = Column(DateTime(timezone=True), nullable=True)
    reset_otp_attempts = Column(Integer, nullable=False, default=0, server_default="0")

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    