"""
SQLAlchemy ORM Models for Vocabulary Flashcard Application

Defines all database tables using SQLAlchemy 2.0 declarative mapping.
These models are the single source of truth for the database schema,
used by both Alembic migrations and the application.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True)
    username = Column(String(255), nullable=False, unique=True)
    password_hash = Column(Text, nullable=True)
    salt = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)
    verification_token = Column(Text)
    reset_token = Column(Text)
    reset_token_expires = Column(DateTime)
    first_name = Column(String(255))
    last_name = Column(String(255))
    mobile_number = Column(String(50))
    profile_type = Column(String(50), default="Student")
    class_year = Column(Integer)
    year_of_birth = Column(Integer)
    school_name = Column(String(255))
    preferred_study_time = Column(Text)
    learning_goals = Column(Text)
    avatar_color = Column(String(20), default="#3498db")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login = Column(DateTime)
    login_count = Column(Integer, default=0)
    failed_login_count = Column(Integer, default=0)
    last_failed_login = Column(DateTime)
    oauth_provider = Column(String(50))  # e.g. "google"
    oauth_id = Column(String(255))  # Provider's unique user ID

    # Relationships
    sessions = relationship("UserSessionModel", back_populates="user", cascade="all, delete-orphan")
    vocabulary = relationship("VocabularyModel", back_populates="user", cascade="all, delete-orphan")
    word_likes = relationship("WordLikeModel", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("UserPreferenceModel", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_username", "username"),
    )


class UserSessionModel(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_token = Column(Text, nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())
    last_accessed = Column(DateTime, default=func.now())
    ip_address = Column(String(45))
    user_agent = Column(Text)

    user = relationship("UserModel", back_populates="sessions")

    __table_args__ = (
        Index("idx_sessions_token", "session_token"),
        Index("idx_sessions_user", "user_id"),
    )


class VocabularyModel(Base):
    __tablename__ = "vocabulary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    word = Column(String(255), nullable=False)
    word_type = Column(String(50), nullable=False)
    definition = Column(Text, nullable=False)
    example = Column(Text, nullable=False)
    difficulty = Column(String(20), default="medium")
    times_reviewed = Column(Integer, default=0)
    times_correct = Column(Integer, default=0)
    last_reviewed = Column(DateTime)
    mastery_level = Column(Integer, default=0)
    is_favorite = Column(Boolean, default=False)
    is_hidden = Column(Boolean, default=False)
    tags = Column(Text, default="")
    source = Column(String(50), default="manual")
    base_word_id = Column(Integer, ForeignKey("base_vocabulary.id", ondelete="SET NULL"))
    like_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("UserModel", back_populates="vocabulary")

    __table_args__ = (
        UniqueConstraint("user_id", "word", name="uq_vocabulary_user_word"),
        Index("idx_vocab_user", "user_id"),
        Index("idx_vocab_word", "user_id", "word"),
        Index("idx_vocab_difficulty", "user_id", "difficulty"),
        Index("idx_vocab_base_word", "base_word_id"),
    )


class BaseVocabularyModel(Base):
    __tablename__ = "base_vocabulary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    word = Column(String(255), nullable=False, unique=True)
    word_type = Column(String(50), nullable=False)
    definition = Column(Text, nullable=False)
    example = Column(Text, nullable=False)
    difficulty = Column(String(20), default="medium")
    category = Column(String(100), default="general")
    total_likes = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    approved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_base_vocab_word", "word"),
    )


class WordLikeModel(Base):
    __tablename__ = "word_likes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    word_id = Column(Integer, ForeignKey("vocabulary.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=func.now())

    user = relationship("UserModel", back_populates="word_likes")

    __table_args__ = (
        UniqueConstraint("user_id", "word_id", name="uq_word_likes_user_word"),
        Index("idx_word_likes_user", "user_id"),
        Index("idx_word_likes_word", "word_id"),
    )


class PasswordResetTokenModel(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(Text, nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index("idx_reset_tokens_token", "token"),
        Index("idx_reset_tokens_user", "user_id"),
    )


class StudySessionModel(Base):
    __tablename__ = "study_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_type = Column(String(50), default="review")
    start_time = Column(DateTime, default=func.now())
    end_time = Column(DateTime)
    words_reviewed = Column(Integer, default=0)
    words_correct = Column(Integer, default=0)
    duration_seconds = Column(Integer, default=0)
    session_goal = Column(Integer, default=10)
    accuracy_percentage = Column(Float, default=0)
    is_completed = Column(Boolean, default=False)
    notes = Column(Text, default="")

    __table_args__ = (
        Index("idx_study_sessions_user", "user_id"),
    )


class StudySessionWordModel(Base):
    __tablename__ = "study_session_words"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("study_sessions.id", ondelete="CASCADE"), nullable=False)
    word_id = Column(Integer, ForeignKey("vocabulary.id", ondelete="CASCADE"), nullable=False)
    was_correct = Column(Boolean, nullable=False)
    response_time_ms = Column(Integer, default=0)
    attempts = Column(Integer, default=1)
    created_at = Column(DateTime, default=func.now())


class UserPreferenceModel(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    preference_key = Column(String(255), nullable=False)
    preference_value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("UserModel", back_populates="preferences")

    __table_args__ = (
        UniqueConstraint("user_id", "preference_key", name="uq_user_prefs"),
        Index("idx_preferences_user", "user_id"),
    )


class VocabularyListModel(Base):
    __tablename__ = "vocabulary_lists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    is_public = Column(Boolean, default=False)
    is_system = Column(Boolean, default=False)
    color = Column(String(20), default="#3498db")
    word_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class VocabularyListWordModel(Base):
    __tablename__ = "vocabulary_list_words"

    id = Column(Integer, primary_key=True, autoincrement=True)
    list_id = Column(Integer, ForeignKey("vocabulary_lists.id", ondelete="CASCADE"), nullable=False)
    word_id = Column(Integer, ForeignKey("vocabulary.id", ondelete="CASCADE"), nullable=False)
    added_at = Column(DateTime, default=func.now())

    __table_args__ = (
        UniqueConstraint("list_id", "word_id", name="uq_list_words"),
    )


class UserAchievementModel(Base):
    __tablename__ = "user_achievements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    achievement_type = Column(String(100), nullable=False)
    achievement_name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    points = Column(Integer, default=0)
    earned_at = Column(DateTime, default=func.now())
    metadata_json = Column("metadata", Text, default="{}")


class DailyStatsModel(Base):
    __tablename__ = "daily_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(String(10), nullable=False)  # DATE stored as string for portability
    words_studied = Column(Integer, default=0)
    words_mastered = Column(Integer, default=0)
    study_time_seconds = Column(Integer, default=0)
    sessions_completed = Column(Integer, default=0)
    accuracy_percentage = Column(Float, default=0)
    streak_days = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_daily_stats_user_date"),
        Index("idx_daily_stats_user_date", "user_id", "date"),
    )


class AiLearningSesssionModel(Base):
    __tablename__ = "ai_learning_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_words = Column(Integer, nullable=False, default=10)
    words_completed = Column(Integer, default=0)
    words_correct = Column(Integer, default=0)
    current_difficulty = Column(String(20), default="medium")
    session_started_at = Column(DateTime, default=func.now())
    session_ended_at = Column(DateTime)
    is_completed = Column(Boolean, default=False)
    total_time_seconds = Column(Integer, default=0)

    __table_args__ = (
        Index("idx_ai_sessions_user", "user_id"),
    )


class AiLearningSessionWordModel(Base):
    __tablename__ = "ai_learning_session_words"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("ai_learning_sessions.id", ondelete="CASCADE"), nullable=False)
    word_id = Column(Integer, ForeignKey("vocabulary.id", ondelete="SET NULL"))
    base_word_id = Column(Integer, ForeignKey("base_vocabulary.id", ondelete="SET NULL"))
    word_text = Column(String(255), nullable=False)
    user_response = Column(Text)
    is_correct = Column(Boolean)
    response_time_ms = Column(Integer, default=0)
    difficulty_level = Column(String(20), default="medium")
    word_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index("idx_ai_session_words_session", "session_id"),
    )


class AiSuggestionFeedbackModel(Base):
    __tablename__ = "ai_suggestion_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    word = Column(String(255), nullable=False)
    difficulty = Column(String(20))
    added_to_vocab = Column(Boolean, default=False)
    feedback_at = Column(DateTime, default=func.now())


class WordDeepDiveModel(Base):
    """Cache for deep-dive word lookups from Azure OpenAI."""
    __tablename__ = "word_deep_dives"

    id = Column(Integer, primary_key=True, autoincrement=True)
    word = Column(String(255), nullable=False, unique=True)
    response_json = Column(Text, nullable=False)  # Full JSON response from OpenAI
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    lookup_count = Column(Integer, default=1)  # How many times this word was looked up

    __table_args__ = (
        Index("idx_deep_dive_word", "word"),
    )
