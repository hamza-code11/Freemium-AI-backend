# app/models/campaign.py

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    business_id = Column(Integer, ForeignKey("business_profiles.id", ondelete="SET NULL"), nullable=True)

    # Form Data
    campaign_name = Column(String(150), nullable=False)
    objective = Column(String(50), nullable=False)
    product_service = Column(Text, nullable=False)
    target_audience = Column(JSON, nullable=True, default=list) # List of strings
    channels = Column(JSON, nullable=True, default=list) # List of strings
    budget = Column(Integer, nullable=True)
    currency = Column(String(10), nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    tone = Column(String(50), nullable=False)
    notes = Column(Text, nullable=True)

    # AI Output (JSON)
    generated_plan = Column(JSON, nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="campaigns")
    business = relationship("BusinessProfile")
    