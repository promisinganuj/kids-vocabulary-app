"""
Database Engine & Session Factory (PostgreSQL)

Configures SQLAlchemy engine for PostgreSQL with connection pooling.
All configuration flows through settings.DATABASE_URL.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from models import Base
from settings import settings


def _build_engine():
    """Create the SQLAlchemy engine for PostgreSQL."""
    url = settings.DATABASE_URL

    engine = create_engine(
        url,
        pool_size=5,
        max_overflow=15,      # up to 20 total connections
        pool_pre_ping=True,   # verify connections before use
        pool_recycle=1800,    # recycle connections after 30 min
        echo=settings.DEBUG and settings.is_development,
    )

    return engine


engine = _build_engine()

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Session:
    """Yield a database session (FastAPI dependency compatible)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_tables():
    """Create all tables from ORM models."""
    Base.metadata.create_all(bind=engine)
