"""Alembic Environment Configuration.

Reads DATABASE_URL from the application settings and uses
the ORM models as the migration target metadata.
"""

import sys
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add the app directory to sys.path so we can import our modules
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models import Base  # noqa: E402
from settings import settings  # noqa: E402

# This is the Alembic Config object
config = context.config

# Override sqlalchemy.url with the value from application settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# The target metadata for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Generates SQL scripts without connecting to the database.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates an Engine and connects to the database to apply migrations.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
