from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5174"

    database_url: str = "postgresql+asyncpg://tiingo_user:changeme@tiingo_db:5432/tiingo_db"
    database_sync_url: str = "postgresql://tiingo_user:changeme@tiingo_db:5432/tiingo_db"
    # Alias: set TIINGO_DATABASE_URL in .env to override database_url
    db_pool_size: int = 5
    db_max_overflow: int = 10

    tiingo_api_key: str = ""
    fred_api_key: str = ""

    enable_scheduler: bool = Field(default=True, validation_alias="ENABLE_TIINGO_SCHEDULER")
    stream_enabled: bool = Field(default=False, validation_alias="STREAM_ENABLED")

    tiingo_fundamentals_tier: str = "dow30"
    tiingo_hourly_limit: int = 9500
    tiingo_daily_limit: int = 95000
    ingest_concurrency: int = 8
    iex_backfill_days: int = 120
    news_interval_minutes: int = 20

    redis_url: str = Field(default="redis://redis:6379", validation_alias="REDIS_URL")
    arq_max_jobs: int = Field(default=4, validation_alias="ARQ_MAX_JOBS")
    auto_backfill_on_create: bool = Field(default=True, validation_alias="AUTO_BACKFILL_ON_CREATE")
    crypto_meta_cache_ttl_seconds: int = 86400
    crypto_history_start_date: str = Field(
        default="2010-01-01",
        validation_alias="CRYPTO_HISTORY_START_DATE",
    )
    ml_artifact_dir: str = Field(default="./data/ml_models", validation_alias="ML_ARTIFACT_DIR")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def fundamentals_addon_active(self) -> bool:
        return self.tiingo_fundamentals_tier.startswith("addon_")


@lru_cache
def get_settings() -> Settings:
    import os

    overrides: dict = {}
    if url := os.getenv("TIINGO_DATABASE_URL"):
        overrides["database_url"] = url
    if sync := os.getenv("TIINGO_DATABASE_SYNC_URL"):
        overrides["database_sync_url"] = sync
    return Settings(**overrides) if overrides else Settings()
