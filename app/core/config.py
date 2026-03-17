"""Environment-based configuration using pydantic-settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class PostgresSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="POSTGRES_")

    host: str = "localhost"
    port: int = 5432
    db: str = "finance_db"
    user: str = "finance_user"
    password: str = "finance_secret"
    pool_min: int = 10
    pool_max: int = 50

    @property
    def dsn(self) -> str:
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.db}"
        )


class RabbitMQSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RABBITMQ_")

    host: str = "localhost"
    port: int = 5672
    user: str = "guest"
    password: str = "guest"
    vhost: str = "/"
    exchange: str = "finance"
    queue_rewards: str = "finance.processed:user.event"
    prefetch_count: int = 100

    @property
    def url(self) -> str:
        return (
            f"amqp://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.vhost}"
        )


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REDIS_")

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str = ""
    pool_size: int = 20

    @property
    def url(self) -> str:
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_")

    name: str = "finance-service"
    env: str = "development"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000
    enable_inbox_consumer: bool = True


class BatchSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BATCH_")

    size: int = 500
    interval_seconds: int = 5


class OutboxSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OUTBOX_")

    poll_interval: float = 1.0  # seconds between relay polls
    batch_size: int = 200  # max messages per poll cycle
    cleanup_days: int = 7  # delete sent messages older than N days
    cleanup_interval: int = 3600  # seconds between cleanup runs


class Settings:
    """Aggregated application settings."""

    def __init__(self) -> None:
        self.postgres = PostgresSettings()
        self.rabbitmq = RabbitMQSettings()
        self.redis = RedisSettings()
        self.app = AppSettings()
        self.batch = BatchSettings()
        self.outbox = OutboxSettings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings (parsed once from env vars)."""
    return Settings()
