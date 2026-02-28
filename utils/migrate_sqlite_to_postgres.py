#!/usr/bin/env python3
"""
Migrate data from SQLite to PostgreSQL.

Usage:
    python migrate_sqlite_to_postgres.py <sqlite_path> <postgres_url>

Example:
    python migrate_sqlite_to_postgres.py \
        ../app/data/vocabulary.db \
        postgresql://vocab_user:secret@localhost:5432/vocab_db

The script:
  1. Connects to both databases.
  2. Creates the PostgreSQL schema via Alembic (if not already present).
  3. Copies every row from each SQLite table into PostgreSQL in
     dependency-safe order (parents before children).
  4. Resets PostgreSQL sequences so auto-increment IDs continue correctly.
  5. Prints a summary of migrated row counts.

Requirements:
    pip install sqlalchemy psycopg2-binary alembic
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

# ---------------------------------------------------------------------------
# Ordered list of tables to migrate.  Parents come before children so that
# foreign-key constraints are satisfied.
# ---------------------------------------------------------------------------
ORDERED_TABLES: list[str] = [
    "users",
    "user_sessions",
    "password_reset_tokens",
    "base_vocabulary",
    "vocabulary",
    "word_likes",
    "study_sessions",
    "study_session_words",
    "user_preferences",
    "vocabulary_lists",
    "vocabulary_list_words",
    "user_achievements",
    "daily_stats",
    "ai_learning_sessions",
    "ai_learning_session_words",
    "ai_suggestion_feedback",
]

# Tables to skip during migration
SKIP_TABLES = {"alembic_version", "sqlite_sequence"}

# Column name mappings: {table: {sqlite_col: pg_col}}
# Handles cases where SQLite schema uses older/different column names.
COLUMN_RENAMES: dict[str, dict[str, str]] = {
    "ai_suggestion_feedback": {
        "suggested_word": "word",
        "difficulty_rating": "difficulty",
        "added_to_vocabulary": "added_to_vocab",
        "created_at": "feedback_at",
    },
}


def get_sqlite_tables(sqlite_conn: sqlite3.Connection) -> list[str]:
    """Return list of user tables in the SQLite database."""
    cur = sqlite_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    return [r[0] for r in cur.fetchall() if r[0] not in SKIP_TABLES]


def get_table_columns(sqlite_conn: sqlite3.Connection, table: str) -> list[str]:
    """Return column names for a SQLite table."""
    cur = sqlite_conn.execute(f"PRAGMA table_info({table})")
    return [r[1] for r in cur.fetchall()]


def migrate_table(
    sqlite_conn: sqlite3.Connection,
    pg_engine,
    table: str,
    batch_size: int = 500,
) -> int:
    """Copy all rows from a SQLite table to PostgreSQL.  Returns row count."""
    columns = get_table_columns(sqlite_conn, table)
    if not columns:
        return 0

    # Check if the table exists in PostgreSQL
    inspector = inspect(pg_engine)
    if table not in inspector.get_table_names():
        print(f"  WARNING: table '{table}' not found in PostgreSQL - skipping")
        return 0

    # Get PostgreSQL column names to find the intersection
    pg_col_info = inspector.get_columns(table)
    pg_columns = [c["name"] for c in pg_col_info]
    # Detect boolean columns so we can convert SQLite int 0/1 → Python bool
    boolean_columns = set()
    for c in pg_col_info:
        col_type = str(c["type"]).upper()
        if col_type in ("BOOLEAN", "BOOL"):
            boolean_columns.add(c["name"])
    # Apply column renames: map SQLite names → PG names
    rename_map = COLUMN_RENAMES.get(table, {})
    mapped_columns = []
    for c in columns:
        pg_name = rename_map.get(c, c)  # rename if mapped, else keep original
        if pg_name in pg_columns:
            mapped_columns.append((c, pg_name))  # (sqlite_name, pg_name)

    if not mapped_columns:
        print(f"  WARNING: no common columns for '{table}' - skipping")
        return 0

    sqlite_col_names = [m[0] for m in mapped_columns]
    pg_col_names = [m[1] for m in mapped_columns]

    skipped = set(columns) - set(sqlite_col_names)
    if skipped:
        print(f"  NOTE: skipping columns not in PG: {skipped}")
    renamed = {s: p for s, p in mapped_columns if s != p}
    if renamed:
        print(f"  NOTE: renaming columns: {renamed}")

    # Read all rows from SQLite (using original SQLite column names)
    col_list = ", ".join(sqlite_col_names)
    cur = sqlite_conn.execute(f"SELECT {col_list} FROM {table}")
    rows = cur.fetchall()
    if not rows:
        return 0

    # Build INSERT statement with PG column names
    pg_col_list = ", ".join(pg_col_names)
    placeholders = ", ".join(f":{c}" for c in pg_col_names)
    insert_sql = text(
        f'INSERT INTO "{table}" ({pg_col_list}) VALUES ({placeholders})'
    )

    # Insert in batches
    total = 0
    with pg_engine.begin() as conn:
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            params = []
            for row in batch:
                # Map values from SQLite col names to PG col names
                d = dict(zip(pg_col_names, row))
                for bc in boolean_columns:
                    if bc in d and d[bc] is not None:
                        d[bc] = bool(d[bc])
                params.append(d)
            conn.execute(insert_sql, params)
            total += len(batch)

    return total


def reset_sequences(pg_engine, tables: list[str]) -> None:
    """Reset PostgreSQL sequences so the next auto-increment ID is correct."""
    inspector = inspect(pg_engine)
    with pg_engine.begin() as conn:
        for table in tables:
            if table not in inspector.get_table_names():
                continue
            columns = {c["name"] for c in inspector.get_columns(table)}
            if "id" not in columns:
                continue
            seq_name = f"{table}_id_seq"
            try:
                conn.execute(
                    text(
                        f"SELECT setval('{seq_name}', "
                        f'COALESCE((SELECT MAX(id) FROM "{table}"), 0) + 1, false)'
                    )
                )
            except Exception as e:
                print(f"  NOTE: could not reset sequence for '{table}': {e}")


def run_alembic_upgrade(postgres_url: str, app_dir: str) -> None:
    """Run alembic upgrade head against the PostgreSQL database."""
    import os
    import subprocess

    env = os.environ.copy()
    env["DATABASE_URL"] = postgres_url
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=app_dir,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Alembic upgrade failed:\n{result.stderr}")
        sys.exit(1)
    print(f"  Alembic: {result.stdout.strip()}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate data from SQLite to PostgreSQL"
    )
    parser.add_argument("sqlite_path", help="Path to the SQLite database file")
    parser.add_argument(
        "postgres_url",
        help="PostgreSQL connection URL (e.g. postgresql://user:pass@host:5432/db)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Number of rows per INSERT batch (default: 500)",
    )
    parser.add_argument(
        "--skip-alembic",
        action="store_true",
        help="Skip running 'alembic upgrade head' (assumes schema exists)",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Truncate target tables before inserting (DANGER: deletes existing PG data)",
    )
    args = parser.parse_args()

    sqlite_path = Path(args.sqlite_path).resolve()
    if not sqlite_path.exists():
        print(f"ERROR: SQLite file not found: {sqlite_path}")
        sys.exit(1)

    app_dir = str(Path(__file__).resolve().parent.parent / "app")

    # Step 1: Run Alembic to ensure PG schema is up to date
    if not args.skip_alembic:
        print("[1/4] Running Alembic migrations on PostgreSQL ...")
        run_alembic_upgrade(args.postgres_url, app_dir)
    else:
        print("[1/4] Skipping Alembic (--skip-alembic)")

    # Step 2: Connect to both databases
    print("[2/4] Connecting to databases ...")
    sqlite_conn = sqlite3.connect(str(sqlite_path))
    sqlite_conn.row_factory = None

    pg_engine = create_engine(args.postgres_url)
    with pg_engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print(f"  SQLite : {sqlite_path}")
    pg_display = args.postgres_url.split("@")[-1] if "@" in args.postgres_url else args.postgres_url
    print(f"  Postgres: {pg_display}")

    # Step 3: Discover tables
    sqlite_tables = set(get_sqlite_tables(sqlite_conn))
    tables_to_migrate: list[str] = []
    for t in ORDERED_TABLES:
        if t in sqlite_tables:
            tables_to_migrate.append(t)
    for t in sorted(sqlite_tables - set(ORDERED_TABLES)):
        tables_to_migrate.append(t)

    print(f"  Tables to migrate: {len(tables_to_migrate)}")

    # Step 3.5: Optionally truncate target tables (reverse order for FK)
    if args.truncate:
        print("  Truncating target tables ...")
        with pg_engine.begin() as conn:
            for t in reversed(tables_to_migrate):
                try:
                    conn.execute(text(f'TRUNCATE TABLE "{t}" CASCADE'))
                except Exception:
                    pass

    # Step 4: Migrate data
    print("[3/4] Migrating data ...")
    start = time.time()
    summary: dict[str, int] = {}
    for table in tables_to_migrate:
        count = migrate_table(sqlite_conn, pg_engine, table, args.batch_size)
        summary[table] = count
        status = f"{count:>6} rows" if count else "  empty"
        print(f"  {table:<35} {status}")

    elapsed = time.time() - start
    total_rows = sum(summary.values())
    print(f"  Migrated {total_rows:,} rows in {elapsed:.1f}s")

    # Step 5: Reset sequences
    print("[4/4] Resetting PostgreSQL sequences ...")
    reset_sequences(pg_engine, tables_to_migrate)

    # Done
    sqlite_conn.close()
    pg_engine.dispose()
    print(f"\nMigration complete!")
    print(f"   Total tables: {len(tables_to_migrate)}")
    print(f"   Total rows  : {total_rows:,}")


if __name__ == "__main__":
    main()
