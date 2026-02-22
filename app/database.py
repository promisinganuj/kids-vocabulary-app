"""
Database Engine & Session Factory

Configures SQLAlchemy engine based on DATABASE_URL from settings.
Supports both SQLite (development) and PostgreSQL (production).
Provides connection pooling for production workloads.
"""

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from models import Base
from settings import settings


def _build_engine():
    """Create the SQLAlchemy engine based on DATABASE_URL."""
    url = settings.DATABASE_URL

    is_sqlite = url.startswith("sqlite")

    connect_args = {}
    pool_kwargs = {}

    if is_sqlite:
        # SQLite: use check_same_thread=False for multi-thread FastAPI
        connect_args["check_same_thread"] = False
        # NullPool is default for SQLite; use StaticPool for in-memory DBs
        pool_kwargs["pool_pre_ping"] = True
    else:
        # PostgreSQL: configure connection pooling
        pool_kwargs.update(
            pool_size=5,
            max_overflow=15,      # up to 20 total connections
            pool_pre_ping=True,   # verify connections before use
            pool_recycle=1800,    # recycle connections after 30 min
        )

    engine = create_engine(
        url,
        connect_args=connect_args,
        echo=settings.DEBUG and settings.is_development,
        **pool_kwargs,
    )

    # SQLite-specific PRAGMA settings (applied per connection)
    if is_sqlite:
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA busy_timeout = 30000")
            cursor.execute("PRAGMA journal_mode = WAL")
            cursor.execute("PRAGMA synchronous = NORMAL")
            cursor.execute("PRAGMA cache_size = -64000")
            cursor.close()

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
    """Create all tables from ORM models (development / first-run only)."""
    Base.metadata.create_all(bind=engine)


@property
def is_sqlite() -> bool:
    """Check if we're running on SQLite."""
    return settings.DATABASE_URL.startswith("sqlite")
