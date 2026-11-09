# app/models/growth_recommendation.py

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class GrowthRecommendation(Base):
    __tablename__ = "growth_recommendations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    business_id = Column(
        Integer,
        ForeignKey("business_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Input Context (User provided)
    business_goals = Column(Text, nullable=True)
    challenges = Column(Text, nullable=True)
    target_audience = Column(JSON, nullable=False, default=list)
    ai_instruction = Column(Text, nullable=True)

    # AI Response
    recommendations = Column(JSON, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    user = relationship("User", back_populates="growth_recommendations")
    business = relationship("BusinessProfile")