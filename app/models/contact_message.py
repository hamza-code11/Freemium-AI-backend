from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.dialects.mysql import LONGTEXT
from app.core.database import Base

class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    subject = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)

    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(512), nullable=True)

    is_read = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    __table_args__ = (
        # 1. Normal composite index for fast sorting & filtering
        Index("ix_contact_messages_created_read", "created_at", "is_read"),
        
        # 2. FULLTEXT index for FAST searching
        Index(
            "ft_contact_search", 
            "name", "email", "subject", 
            mysql_prefix="FULLTEXT"
        ),
    )



