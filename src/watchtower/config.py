"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Watchtower Scraper settings loaded from environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database & Cache
    DATABASE_URL: str = "sqlite:///./watchtower.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Telegram Alerting
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None

    # Email Alerting (SendGrid or SMTP)
    SENDGRID_API_KEY: Optional[str] = None
    ALERT_FROM_EMAIL: str = "alerts@watchtower.io"
    ALERT_TO_EMAILS: List[str] = Field(default_factory=list)

    # Scraper & Proxy Configuration
    PROXIES: List[str] = Field(default_factory=list)
    USER_AGENTS: List[str] = Field(
        default_factory=lambda: [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:124.0) Gecko/20100101 Firefox/124.0",
        ]
    )
    DOWNLOAD_DELAY: float = 2.0
    ROBOTSTXT_OBEY: bool = True
    AUTOTHROTTLE_ENABLED: bool = True
    RANDOMIZE_DOWNLOAD_DELAY: bool = True

    # Change Detection & Retention Thresholds
    MIN_PRICE_DELTA_PCT: float = 1.0
    MISSING_AFTER_HOURS: int = 24
    RETENTION_DAYS: int = 90

    # Logging & Monitoring API
    LOG_LEVEL: str = "INFO"
    HTTP_PORT: int = 8000
    DISPLAY_TIMEZONE: str = "Africa/Nairobi"

    @field_validator("ALERT_TO_EMAILS", mode="before")
    @classmethod
    def parse_alert_emails(cls, v):
        if isinstance(v, str):
            if not v.strip():
                return []
            return [email.strip() for email in v.split(",") if email.strip()]
        if isinstance(v, list):
            return v
        return []

    @field_validator("PROXIES", mode="before")
    @classmethod
    def parse_proxies(cls, v):
        if isinstance(v, str):
            if not v.strip():
                return []
            # Split on newline or comma
            return [p.strip() for p in v.replace(",", "\n").splitlines() if p.strip()]
        if isinstance(v, list):
            return v
        return []


@lru_cache()
def get_settings() -> Settings:
    """Return cached Settings singleton."""
    return Settings()
