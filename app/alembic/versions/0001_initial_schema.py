"""Initial schema - all 16 tables

Revision ID: 0001
Revises: 
Create Date: 2026-02-22

Creates all application tables. For existing SQLite databases that
already have these tables, run `alembic stamp head` instead of
`alembic upgrade head`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ───────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("username", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("salt", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("is_admin", sa.Boolean, server_default=sa.text("false")),
        sa.Column("email_verified", sa.Boolean, server_default=sa.text("false")),
        sa.Column("verification_token", sa.Text),
        sa.Column("reset_token", sa.Text),
        sa.Column("reset_token_expires", sa.DateTime),
        sa.Column("first_name", sa.String(255)),
        sa.Column("last_name", sa.String(255)),
        sa.Column("mobile_number", sa.String(50)),
        sa.Column("profile_type", sa.String(50), server_default="Student"),
        sa.Column("class_year", sa.Integer),
        sa.Column("year_of_birth", sa.Integer),
        sa.Column("school_name", sa.String(255)),
        sa.Column("preferred_study_time", sa.Text),
        sa.Column("learning_goals", sa.Text),
        sa.Column("avatar_color", sa.String(20), server_default="#3498db"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("last_login", sa.DateTime),
        sa.Column("login_count", sa.Integer, server_default="0"),
        sa.Column("failed_login_count", sa.Integer, server_default="0"),
        sa.Column("last_failed_login", sa.DateTime),
    )
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_username", "users", ["username"])

    # ── user_sessions ───────────────────────────────────────
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_token", sa.Text, nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("last_accessed", sa.DateTime, server_default=sa.func.now()),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.Text),
    )
    op.create_index("idx_sessions_token", "user_sessions", ["session_token"])
    op.create_index("idx_sessions_user", "user_sessions", ["user_id"])

    # ── base_vocabulary ─────────────────────────────────────
    op.create_table(
        "base_vocabulary",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("word", sa.String(255), nullable=False, unique=True),
        sa.Column("word_type", sa.String(50), nullable=False),
        sa.Column("definition", sa.Text, nullable=False),
        sa.Column("example", sa.Text, nullable=False),
        sa.Column("difficulty", sa.String(20), server_default="medium"),
        sa.Column("category", sa.String(100), server_default="general"),
        sa.Column("total_likes", sa.Integer, server_default="0"),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_by", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("approved_by", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_base_vocab_word", "base_vocabulary", ["word"])

    # ── vocabulary ──────────────────────────────────────────
    op.create_table(
        "vocabulary",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("word", sa.String(255), nullable=False),
        sa.Column("word_type", sa.String(50), nullable=False),
        sa.Column("definition", sa.Text, nullable=False),
        sa.Column("example", sa.Text, nullable=False),
        sa.Column("difficulty", sa.String(20), server_default="medium"),
        sa.Column("times_reviewed", sa.Integer, server_default="0"),
        sa.Column("times_correct", sa.Integer, server_default="0"),
        sa.Column("last_reviewed", sa.DateTime),
        sa.Column("mastery_level", sa.Integer, server_default="0"),
        sa.Column("is_favorite", sa.Boolean, server_default=sa.text("false")),
        sa.Column("is_hidden", sa.Boolean, server_default=sa.text("false")),
        sa.Column("tags", sa.Text, server_default=""),
        sa.Column("source", sa.String(50), server_default="manual"),
        sa.Column("base_word_id", sa.Integer, sa.ForeignKey("base_vocabulary.id", ondelete="SET NULL")),
        sa.Column("like_count", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "word", name="uq_vocabulary_user_word"),
    )
    op.create_index("idx_vocab_user", "vocabulary", ["user_id"])
    op.create_index("idx_vocab_word", "vocabulary", ["user_id", "word"])
    op.create_index("idx_vocab_difficulty", "vocabulary", ["user_id", "difficulty"])
    op.create_index("idx_vocab_base_word", "vocabulary", ["base_word_id"])

    # ── word_likes ──────────────────────────────────────────
    op.create_table(
        "word_likes",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("word_id", sa.Integer, sa.ForeignKey("vocabulary.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "word_id", name="uq_word_likes_user_word"),
    )
    op.create_index("idx_word_likes_user", "word_likes", ["user_id"])
    op.create_index("idx_word_likes_word", "word_likes", ["word_id"])

    # ── password_reset_tokens ───────────────────────────────
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.Text, nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("used", sa.Boolean, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_reset_tokens_token", "password_reset_tokens", ["token"])
    op.create_index("idx_reset_tokens_user", "password_reset_tokens", ["user_id"])

    # ── study_sessions ──────────────────────────────────────
    op.create_table(
        "study_sessions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_type", sa.String(50), server_default="review"),
        sa.Column("start_time", sa.DateTime, server_default=sa.func.now()),
        sa.Column("end_time", sa.DateTime),
        sa.Column("words_reviewed", sa.Integer, server_default="0"),
        sa.Column("words_correct", sa.Integer, server_default="0"),
        sa.Column("duration_seconds", sa.Integer, server_default="0"),
        sa.Column("session_goal", sa.Integer, server_default="10"),
        sa.Column("accuracy_percentage", sa.Float, server_default="0"),
        sa.Column("is_completed", sa.Boolean, server_default=sa.text("false")),
        sa.Column("notes", sa.Text, server_default=""),
    )
    op.create_index("idx_study_sessions_user", "study_sessions", ["user_id"])

    # ── study_session_words ─────────────────────────────────
    op.create_table(
        "study_session_words",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.Integer, sa.ForeignKey("study_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("word_id", sa.Integer, sa.ForeignKey("vocabulary.id", ondelete="CASCADE"), nullable=False),
        sa.Column("was_correct", sa.Boolean, nullable=False),
        sa.Column("response_time_ms", sa.Integer, server_default="0"),
        sa.Column("attempts", sa.Integer, server_default="1"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ── user_preferences ────────────────────────────────────
    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("preference_key", sa.String(255), nullable=False),
        sa.Column("preference_value", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "preference_key", name="uq_user_prefs"),
    )
    op.create_index("idx_preferences_user", "user_preferences", ["user_id"])

    # ── vocabulary_lists ────────────────────────────────────
    op.create_table(
        "vocabulary_lists",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("is_public", sa.Boolean, server_default=sa.text("false")),
        sa.Column("is_system", sa.Boolean, server_default=sa.text("false")),
        sa.Column("color", sa.String(20), server_default="#3498db"),
        sa.Column("word_count", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ── vocabulary_list_words ───────────────────────────────
    op.create_table(
        "vocabulary_list_words",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("list_id", sa.Integer, sa.ForeignKey("vocabulary_lists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("word_id", sa.Integer, sa.ForeignKey("vocabulary.id", ondelete="CASCADE"), nullable=False),
        sa.Column("added_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("list_id", "word_id", name="uq_list_words"),
    )

    # ── user_achievements ───────────────────────────────────
    op.create_table(
        "user_achievements",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("achievement_type", sa.String(100), nullable=False),
        sa.Column("achievement_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("points", sa.Integer, server_default="0"),
        sa.Column("earned_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("metadata", sa.Text, server_default="{}"),
    )

    # ── daily_stats ─────────────────────────────────────────
    op.create_table(
        "daily_stats",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.String(10), nullable=False),
        sa.Column("words_studied", sa.Integer, server_default="0"),
        sa.Column("words_mastered", sa.Integer, server_default="0"),
        sa.Column("study_time_seconds", sa.Integer, server_default="0"),
        sa.Column("sessions_completed", sa.Integer, server_default="0"),
        sa.Column("accuracy_percentage", sa.Float, server_default="0"),
        sa.Column("streak_days", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "date", name="uq_daily_stats_user_date"),
    )
    op.create_index("idx_daily_stats_user_date", "daily_stats", ["user_id", "date"])

    # ── ai_learning_sessions ────────────────────────────────
    op.create_table(
        "ai_learning_sessions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_words", sa.Integer, nullable=False, server_default="10"),
        sa.Column("words_completed", sa.Integer, server_default="0"),
        sa.Column("words_correct", sa.Integer, server_default="0"),
        sa.Column("current_difficulty", sa.String(20), server_default="medium"),
        sa.Column("session_started_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("session_ended_at", sa.DateTime),
        sa.Column("is_completed", sa.Boolean, server_default=sa.text("false")),
        sa.Column("total_time_seconds", sa.Integer, server_default="0"),
    )
    op.create_index("idx_ai_sessions_user", "ai_learning_sessions", ["user_id"])

    # ── ai_learning_session_words ───────────────────────────
    op.create_table(
        "ai_learning_session_words",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.Integer, sa.ForeignKey("ai_learning_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("word_id", sa.Integer, sa.ForeignKey("vocabulary.id", ondelete="SET NULL")),
        sa.Column("base_word_id", sa.Integer, sa.ForeignKey("base_vocabulary.id", ondelete="SET NULL")),
        sa.Column("word_text", sa.String(255), nullable=False),
        sa.Column("user_response", sa.Text),
        sa.Column("is_correct", sa.Boolean),
        sa.Column("response_time_ms", sa.Integer, server_default="0"),
        sa.Column("difficulty_level", sa.String(20), server_default="medium"),
        sa.Column("word_order", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_ai_session_words_session", "ai_learning_session_words", ["session_id"])

    # ── ai_suggestion_feedback ──────────────────────────────
    op.create_table(
        "ai_suggestion_feedback",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("word", sa.String(255), nullable=False),
        sa.Column("difficulty", sa.String(20)),
        sa.Column("added_to_vocab", sa.Boolean, server_default=sa.text("false")),
        sa.Column("feedback_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    """Drop all tables in reverse order."""
    op.drop_table("ai_suggestion_feedback")
    op.drop_table("ai_learning_session_words")
    op.drop_table("ai_learning_sessions")
    op.drop_table("daily_stats")
    op.drop_table("user_achievements")
    op.drop_table("vocabulary_list_words")
    op.drop_table("vocabulary_lists")
    op.drop_table("user_preferences")
    op.drop_table("study_session_words")
    op.drop_table("study_sessions")
    op.drop_table("password_reset_tokens")
    op.drop_table("word_likes")
    op.drop_table("vocabulary")
    op.drop_table("base_vocabulary")
    op.drop_table("user_sessions")
    op.drop_table("users")
