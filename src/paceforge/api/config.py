"""Application settings loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    garmin_email: str = ""
    garmin_password: str = ""
    garmin_token_dir: str = "~/.garminconnect"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    log_level: str = "INFO"

    # Auth
    jwt_secret: str = "change-me-in-production"
    admin_email: str = ""
    admin_password: str = ""
    db_path: str = "paceforge.db"
    cors_origins: str = "http://localhost:8501"

    model_config = {"env_prefix": "PACEFORGE_", "env_file": ".env"}


settings = Settings()
