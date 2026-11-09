from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.core.database import Base
from sqlalchemy.orm import relationship


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    image = Column(String(255), nullable=True)
    role = Column(String(50), nullable=False, default="user", server_default="user")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


    business_profiles = relationship(
        "BusinessProfile",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    business_profiles = relationship(
        "BusinessProfile",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    content_generations = relationship(
        "ContentGeneration",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    campaigns = relationship("Campaign", back_populates="user", cascade="all, delete-orphan")

    growth_recommendations = relationship(
        "GrowthRecommendation",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # User class ke andar
    support_tickets = relationship("SupportTicket", back_populates="user", cascade="all, delete-orphan")
    