# app/models/content_generation.py

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class ContentGeneration(Base):
    __tablename__ = "content_generations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Form Data (User Input)
    platform = Column(String(50), nullable=False)
    content_type = Column(String(50), nullable=False)
    topic = Column(String(200), nullable=False)
    target_audience = Column(JSON, nullable=True, default=list)
    tone = Column(String(50), nullable=False)
    language = Column(String(50), nullable=False)
    notes = Column(Text, nullable=True)

    # AI Output
    generated_content = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationship
    user = relationship("User", back_populates="content_generations")

    