from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import DATABASE_URL


# Database Connection
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)


# Database Session
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# Base Model
class Base(DeclarativeBase):
    pass


# Database Dependency
def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()