"""Application settings loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    garmin_email: str = ""
    garmin_password: str = ""
    garmin_token_dir: str = "~/.garminconnect"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    llm_provider: str = ""  # "openai", "anthropic", or "" for auto-detect
    log_level: str = "INFO"

    # Auth
    jwt_secret: str = "change-me-in-production"
    admin_email: str = ""
    admin_password: str = ""
    db_path: str = "paceforge.db"
    cors_origins: str = "http://localhost:8501"

    # Strava OAuth
    strava_client_id: str = ""
    strava_client_secret: str = ""

    # SMTP notifications
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    notify_email: str = ""  # Admin email to receive notifications
    app_base_url: str = "https://paceforge-app.azurewebsites.net"

    model_config = {"env_prefix": "PACEFORGE_", "env_file": ".env"}


settings = Settings()
