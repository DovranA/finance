"""Environment-based configuration using pydantic-settings."""

from __future__ import annotations

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
    exchange: str = "finance_events"
    queue_rewards: str = "reward_events"
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


class BatchSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BATCH_")

    size: int = 500
    interval_seconds: int = 5


class Settings:
    """Aggregated application settings."""

    def __init__(self) -> None:
        self.postgres = PostgresSettings()
        self.rabbitmq = RabbitMQSettings()
        self.redis = RedisSettings()
        self.app = AppSettings()
        self.batch = BatchSettings()


def get_settings() -> Settings:
    return Settings()
