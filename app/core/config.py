"""Environment-based configuration using pydantic-settings."""

from __future__ import annotations

import logging
import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class PostgresSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="POSTGRES_")

    host: str = "localhost"
    port: int = 5432
    db: str = "finance_db"
    user: str = "finance_user"
    password: str = "finance_secret"
    pool_min: int = 10
    pool_max: int = 50

    def model_post_init(self, __context):
        """Log loaded values for debugging."""
        logger.info(
            f"PostgresSettings loaded: host={self.host}, port={self.port}, "
            f"db={self.db}, user={self.user}, pool_min={self.pool_min}, "
            f"pool_max={self.pool_max}"
        )
        # Also log raw env vars to debug
        postgres_host_env = os.getenv("POSTGRES_HOST")
        postgres_port_env = os.getenv("POSTGRES_PORT")
        logger.info(
            f"Raw env vars: POSTGRES_HOST={postgres_host_env}, "
            f"POSTGRES_PORT={postgres_port_env}"
        )

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
    queue_competition: str = "user-competition.joined:update.finance"
    queue_user_registered: str = "user.registered:update.finance"
    queue_user_deleted: str = "user.deleted:update.finance"
    queue_user_blocked: str = "user.blocked:update.finance"
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
    enable_competition_consumer: bool = True
    enable_user_registered_consumer: bool = True
    enable_user_deleted_consumer: bool = True
    enable_user_blocked_consumer: bool = True
    enable_metrics: bool = True
    metrics_port: int | None = None
    metrics_db_interval_seconds: float = 5.0


class BatchSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BATCH_")

    size: int = 500
    interval_seconds: int = 5


class InboxCleanupSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="INBOX_")

    cleanup_days: int = 7
    cleanup_interval: int = 3600


class OutboxSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OUTBOX_")

    poll_interval: float = 1.0  # seconds between relay polls
    batch_size: int = 200  # max messages per poll cycle
    cleanup_days: int = 7  # delete sent messages older than N days
    cleanup_interval: int = 3600  # seconds between cleanup runs


class RestApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REST_API_")

    base_url: str = ""
    timeout_seconds: float = 10.0
    max_connections: int = 100
    max_keepalive_connections: int = 20


class UserManagementSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="USER_MANAGEMENT_")

    endpoint: str = "https://kong.tmbiz.info/public/user-management"
    api_key: str = "apikey"
    users_lookup_path: str = "/api/v0/users/lookup"
    timeout_seconds: float = 10.0


class JwtSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JWT_")

    enabled: bool = True
    algorithm: str = "HS256"
    secret_key: str = ""
    leeway_seconds: int = 0


class Settings:
    """Aggregated application settings."""

    def __init__(self) -> None:
        self.postgres = PostgresSettings()
        self.rabbitmq = RabbitMQSettings()
        self.redis = RedisSettings()
        self.app = AppSettings()
        self.batch = BatchSettings()
        self.inbox_cleanup = InboxCleanupSettings()
        self.outbox = OutboxSettings()
        self.rest_api = RestApiSettings()
        self.user_management = UserManagementSettings()
        self.jwt = JwtSettings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings (parsed once from env vars)."""
    return Settings()
