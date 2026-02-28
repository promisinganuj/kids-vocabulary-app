"""
Application Settings

Centralized configuration using pydantic-settings.
All configuration flows through this module — no direct os.getenv() elsewhere.

Supports:
- Environment variables
- .env files
- Docker secrets (file-based: SECRET_KEY_FILE, DATABASE_URL_FILE, etc.)
- Environment profiles: development, staging, production

Usage:
    from settings import settings
    print(settings.SECRET_KEY)
    print(settings.DATABASE_URL)
"""

import os
import secrets
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


def _read_secret_file(env_var_name: str) -> Optional[str]:
    """Read a secret from a file path specified by an env var (Docker/K8s secrets pattern).

    For example, if SECRET_KEY_FILE=/run/secrets/secret_key, this reads that file.
    """
    file_path = os.environ.get(env_var_name)
    if file_path and os.path.isfile(file_path):
        return Path(file_path).read_text().strip()
    return None


class Settings(BaseSettings):
    """Application settings with environment variable support.

    Priority (highest to lowest):
    1. Environment variables
    2. Docker secrets files (*_FILE env vars)
    3. .env file
    4. Default values
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Application ────────────────────────────────────────────
    APP_ENV: AppEnvironment = AppEnvironment.DEVELOPMENT
    APP_NAME: str = "VCE Vocabulary Flashcards"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False

    # ─── Server ─────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 5001
    WORKERS: int = 1  # uvicorn workers; increase in production
    RELOAD: bool = False  # auto-reload on code changes (dev only)

    # ─── Security ───────────────────────────────────────────────
    SECRET_KEY: str = ""  # validated below — required in production
    SESSION_TIMEOUT_HOURS: int = 24

    # ─── Database (PostgreSQL) ──────────────────────────────────
    DATABASE_URL: str = ""  # validated below — required in all environments

    # ─── Azure OpenAI (optional) ────────────────────────────────
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_DEPLOYMENT: Optional[str] = None
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"

    # ─── Google OAuth (optional) ──────────────────────────────────
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = None  # e.g. https://yourapp.com/auth/google/callback

    # ─── Seed Data ──────────────────────────────────────────────
    SEED_DATA_PATH: str = os.path.join("..", "seed-data", "words-list.txt")

    @model_validator(mode="before")
    @classmethod
    def _load_docker_secrets(cls, values: dict) -> dict:
        """Load secrets from file paths (Docker/K8s secrets pattern).

        Checks for *_FILE env vars and reads the file contents.
        Only sets the value if the non-file env var is not already set.
        """
        secret_mappings = {
            "SECRET_KEY_FILE": "SECRET_KEY",
            "DATABASE_URL_FILE": "DATABASE_URL",
            "AZURE_OPENAI_API_KEY_FILE": "AZURE_OPENAI_API_KEY",
            "GOOGLE_CLIENT_SECRET_FILE": "GOOGLE_CLIENT_SECRET",
        }
        for file_var, target_var in secret_mappings.items():
            if not values.get(target_var):
                file_value = _read_secret_file(file_var)
                if file_value:
                    values[target_var] = file_value
        return values

    @model_validator(mode="after")
    def _apply_environment_defaults(self) -> "Settings":
        """Apply environment-specific defaults and validate required config."""

        if self.APP_ENV == AppEnvironment.DEVELOPMENT:
            # Development: generate defaults for convenience
            if not self.SECRET_KEY:
                self.SECRET_KEY = secrets.token_hex(32)
            if not self.DATABASE_URL:
                raise ValueError(
                    "DATABASE_URL is required. "
                    "Set DATABASE_URL env var, e.g. postgresql://user:pass@localhost:5432/dbname"
                )
            if self.RELOAD is False and self.WORKERS == 1:
                self.RELOAD = True  # auto-reload in dev by default
            self.DEBUG = True

        elif self.APP_ENV == AppEnvironment.STAGING:
            if not self.SECRET_KEY:
                self.SECRET_KEY = secrets.token_hex(32)
            if not self.DATABASE_URL:
                raise ValueError(
                    "DATABASE_URL is required in staging. "
                    "Set DATABASE_URL env var or DATABASE_URL_FILE for Docker secrets."
                )

        elif self.APP_ENV == AppEnvironment.PRODUCTION:
            # Production: fail fast on missing required config
            if not self.SECRET_KEY:
                raise ValueError(
                    "SECRET_KEY is required in production. "
                    "Set SECRET_KEY env var or SECRET_KEY_FILE for Docker secrets."
                )
            if not self.DATABASE_URL:
                raise ValueError(
                    "DATABASE_URL is required in production. "
                    "Set DATABASE_URL env var or DATABASE_URL_FILE for Docker secrets."
                )
            if self.RELOAD:
                self.RELOAD = False  # never auto-reload in production
            self.DEBUG = False

        return self

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == AppEnvironment.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == AppEnvironment.DEVELOPMENT

    @property
    def google_oauth_configured(self) -> bool:
        """Check if Google OAuth is fully configured."""
        return bool(
            self.GOOGLE_CLIENT_ID
            and self.GOOGLE_CLIENT_SECRET
        )

    @property
    def openai_configured(self) -> bool:
        """Check if Azure OpenAI is fully configured."""
        return bool(
            self.AZURE_OPENAI_API_KEY
            and self.AZURE_OPENAI_ENDPOINT
            and self.AZURE_OPENAI_DEPLOYMENT
        )


# Singleton instance — import this everywhere
settings = Settings()
