from sqlalchemy import Column, Integer, String, Text

from app.core.database import Base


class Product(Base):

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    name = Column(String(255), nullable=False)

    description = Column(Text, nullable=True)

    image = Column(String(500), nullable=True)