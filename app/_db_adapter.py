"""
SQLAlchemy <-> sqlite3 Adapter Layer

Provides a sqlite3-compatible interface over SQLAlchemy sessions so that
existing DatabaseManager method bodies require minimal changes.

This adapter automatically:
- Converts ? positional placeholders to :named parameters
- Adapts SQLite-specific SQL for PostgreSQL (julianday, COLLATE NOCASE, etc.)
- Wraps SQLAlchemy Row objects with dict-like access (row['column'])
"""

import re
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session


class RowAdapter:
    """Wraps a SQLAlchemy Row to provide sqlite3.Row-like dict/index access."""
    __slots__ = ("_mapping",)

    def __init__(self, sa_row):
        object.__setattr__(self, "_mapping", sa_row._mapping)

    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self._mapping.values())[key]
        return self._mapping[key]

    def keys(self):
        return self._mapping.keys()

    def __iter__(self):
        return iter(self._mapping.values())

    def __repr__(self):
        return f"RowAdapter({dict(self._mapping)})"


class CursorAdapter:
    """Wraps a SQLAlchemy session to behave like sqlite3.Cursor."""

    def __init__(self, session: Session, is_sqlite: bool):
        self._session = session
        self._is_sqlite = is_sqlite
        self._result = None
        self.lastrowid: Optional[int] = None
        self.rowcount: int = 0

    # ── placeholder conversion ────────────────────────────────
    @staticmethod
    def _positional_to_named(sql: str, params):
        """Convert ? placeholders to :_p1, :_p2, ... named parameters."""
        if not params:
            return sql, {}
        counter = [0]
        named = {}

        def _repl(_match):
            counter[0] += 1
            return f":_p{counter[0]}"

        new_sql = re.sub(r"\?", _repl, sql)
        for i, val in enumerate(params, 1):
            named[f"_p{i}"] = val
        return new_sql, named

    # ── dialect adaptation ────────────────────────────────────
    # Boolean column names across all tables — used to rewrite
    # SQLite integer comparisons (= 1 / = 0) to PostgreSQL boolean literals.
    _BOOL_COLUMNS = frozenset({
        "added_to_vocab", "email_verified", "is_active", "is_admin",
        "is_completed", "is_correct", "is_favorite", "is_hidden",
        "is_public", "is_system", "used", "was_correct",
    })

    def _adapt_sql(self, sql: str) -> str:
        """Adapt SQLite-specific SQL for PostgreSQL when running on PG."""
        if self._is_sqlite:
            return sql

        # Rewrite boolean column comparisons: col = 1 → col = TRUE, col = 0 → col = FALSE
        # This handles SQLite idiom where booleans are stored/compared as integers.
        for col in self._BOOL_COLUMNS:
            sql = re.sub(
                rf"\b{col}\s*=\s*1\b", f"{col} = TRUE", sql
            )
            sql = re.sub(
                rf"\b{col}\s*=\s*0\b", f"{col} = FALSE", sql
            )

        # Strip COLLATE NOCASE (PostgreSQL is case-sensitive by default)
        sql = sql.replace("COLLATE NOCASE", "")

        # julianday('now') - julianday(col) → EXTRACT(EPOCH FROM ...) / 86400
        sql = re.sub(
            r"julianday\s*\(\s*'now'\s*\)\s*-\s*julianday\s*\((\w+)\)",
            r"EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - \1)) / 86400.0",
            sql,
        )

        # datetime('now', '-N days') → CURRENT_TIMESTAMP - INTERVAL 'N days'
        sql = re.sub(
            r"datetime\s*\(\s*'now'\s*,\s*'(-?\d+)\s+days?'\s*\)",
            lambda m: f"CURRENT_TIMESTAMP - INTERVAL '{abs(int(m.group(1)))} days'",
            sql,
        )

        # INSERT OR REPLACE → plain INSERT (caller should handle conflicts)
        sql = re.sub(r"INSERT\s+OR\s+REPLACE\s+INTO", "INSERT INTO", sql, flags=re.IGNORECASE)

        # INSERT OR IGNORE → INSERT ... ON CONFLICT DO NOTHING
        sql = re.sub(r"INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", sql, flags=re.IGNORECASE)

        return sql

    # ── execute ───────────────────────────────────────────────
    def execute(self, sql: str, params=None):
        stripped = sql.strip().upper()

        # Skip SQLite-only statements on PostgreSQL
        if not self._is_sqlite:
            if stripped.startswith("PRAGMA"):
                return self
            if stripped.startswith("CREATE TRIGGER"):
                return self

        sql, named = self._positional_to_named(sql, params)
        sql = self._adapt_sql(sql)

        self._result = self._session.execute(text(sql), named)

        # Capture lastrowid and rowcount
        self.lastrowid = getattr(self._result, "lastrowid", None)
        rc = getattr(self._result, "rowcount", -1)
        self.rowcount = rc if rc >= 0 else 0
        return self

    # ── fetch ─────────────────────────────────────────────────
    def fetchone(self):
        if self._result is None:
            return None
        row = self._result.fetchone()
        return RowAdapter(row) if row else None

    def fetchall(self):
        if self._result is None:
            return []
        return [RowAdapter(r) for r in self._result.fetchall()]


class ConnectionAdapter:
    """Wraps a SQLAlchemy session to behave like sqlite3.Connection.

    Supports the ``with`` context-manager pattern:
    - On normal exit: commits the transaction
    - On exception: rolls back
    - Always closes the session on exit
    """

    def __init__(self, session: Session, is_sqlite: bool):
        self._session = session
        self._is_sqlite = is_sqlite

    def cursor(self) -> CursorAdapter:
        return CursorAdapter(self._session, self._is_sqlite)

    def execute(self, sql: str, params=None) -> CursorAdapter:
        c = self.cursor()
        c.execute(sql, params)
        return c

    def commit(self):
        self._session.commit()

    def close(self):
        self._session.close()

    # ── context manager ───────────────────────────────────────
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self._session.rollback()
        else:
            try:
                self._session.commit()
            except Exception:
                self._session.rollback()
                raise
        self._session.close()
        return False
