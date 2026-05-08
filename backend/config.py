"""
Tata - AI Personality Replication Chat Companion
Backend Configuration
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    app_name: str = "Tata"
    app_version: str = "1.0.0"
    debug: bool = False
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Database
    database_url: str = "sqlite:///./tata.db"

    # LLM Providers
    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"
    deepseek_api_key: Optional[str] = None
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    default_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    # Stripe Payment
    stripe_api_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    free_tier_messages: int = 50
    pro_price_id: Optional[str] = None
    pro_monthly_price: float = 9.99  # USD
    enterprise_price_id: Optional[str] = None
    enterprise_monthly_price: float = 29.99

    # Vector Store (ChromaDB)
    chroma_persist_dir: str = "./chroma_data"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"

    # Scheduled Messages
    max_scheduled_messages_per_day: int = 20

    # Rate Limits
    rate_limit_messages_per_minute: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
