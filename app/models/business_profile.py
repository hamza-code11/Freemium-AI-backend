from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from sqlalchemy import JSON, Column

from app.core.database import Base


class BusinessProfile(Base):
    __tablename__ = "business_profiles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    business_name = Column(String(150), nullable=False)
    business_type = Column(String(100), nullable=False)
    services = Column(Text, nullable=False)
    target_audience = Column(JSON, nullable=True, default=list)
    business_goals = Column(Text, nullable=True)
    business_description = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    user = relationship("User", back_populates="business_profiles")
    