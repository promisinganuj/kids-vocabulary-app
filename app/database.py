"""
Database Engine & Session Factory

Configures SQLAlchemy engine based on DATABASE_URL from settings.
Supports both SQLite (development) and PostgreSQL (production).
Provides connection pooling for production workloads.
"""

import os

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from models import Base
from settings import settings


def _is_network_filesystem(db_path: str) -> bool:
    """Detect if a path is on a network mount (Azure File Share / CIFS / NFS).

    On Linux, reads /proc/mounts to check if the directory containing the DB
    file is mounted via a network filesystem.  Returns False on any error or
    on non-Linux systems (safe default: assume local disk).
    """
    try:
        mount_point = os.path.dirname(os.path.abspath(db_path))
        if not os.path.exists("/proc/mounts"):
            return False
        with open("/proc/mounts") as mf:
            for line in mf:
                parts = line.split()
                if len(parts) >= 3 and mount_point.startswith(parts[1]):
                    if parts[2] in ("cifs", "nfs", "nfs4", "fuse.sshfs"):
                        return True
        return False
    except Exception:
        return False


def _build_engine():
    """Create the SQLAlchemy engine based on DATABASE_URL."""
    url = settings.DATABASE_URL

    is_sqlite = url.startswith("sqlite")

    connect_args = {}
    pool_kwargs = {}

    if is_sqlite:
        # SQLite: use check_same_thread=False for multi-thread FastAPI
        connect_args["check_same_thread"] = False
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
        # Detect network FS once at engine build time
        db_path = url.replace("sqlite:///", "")
        on_network_fs = _is_network_filesystem(db_path)
        if on_network_fs:
            print("\u26a0\ufe0f  SQLite DB is on a network filesystem -- using DELETE journal mode")

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            # Long busy_timeout -- essential for Azure File Shares (SMB latency)
            cursor.execute("PRAGMA busy_timeout = 60000")
            if on_network_fs:
                # Network FS: WAL mode is UNSAFE (relies on shared-memory mmap).
                # Use DELETE journal mode which works over SMB/NFS.
                try:
                    cursor.execute("PRAGMA journal_mode = DELETE")
                except Exception:
                    pass
                # FULL synchronous for data safety on unreliable locks
                cursor.execute("PRAGMA synchronous = FULL")
            else:
                # Local disk: WAL mode for best concurrency
                try:
                    cursor.execute("PRAGMA journal_mode = WAL")
                except Exception:
                    pass
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
    """Check if we\'re running on SQLite."""
    return settings.DATABASE_URL.startswith("sqlite")
