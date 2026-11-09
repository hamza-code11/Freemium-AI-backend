import certifi
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import DATABASE_URL


# SSL sirf cloud DB (TiDB) ke liye, local MySQL par nahi
connect_args = {}
if "tidbcloud.com" in DATABASE_URL:
    connect_args = {"ssl": {"ca": certifi.where()}}


# Database Connection
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=300,
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