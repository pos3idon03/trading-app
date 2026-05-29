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
    deployment_reconciliation_interval_minutes: int = Field(
        default=10,
        validation_alias="DEPLOYMENT_RECONCILIATION_INTERVAL_MINUTES",
    )

    redis_url: str = Field(default="redis://redis:6379", validation_alias="REDIS_URL")
    arq_max_jobs: int = Field(default=4, validation_alias="ARQ_MAX_JOBS")
    arq_heavy_queue_name: str = Field(default="heavy", validation_alias="ARQ_HEAVY_QUEUE_NAME")
    arq_heavy_max_jobs: int = Field(default=1, validation_alias="ARQ_HEAVY_MAX_JOBS")
    auto_backfill_on_create: bool = Field(default=True, validation_alias="AUTO_BACKFILL_ON_CREATE")
    crypto_meta_cache_ttl_seconds: int = 86400
    crypto_history_start_date: str = Field(
        default="2010-01-01",
        validation_alias="CRYPTO_HISTORY_START_DATE",
    )
    ml_artifact_dir: str = Field(default="./data/ml_models", validation_alias="ML_ARTIFACT_DIR")

    sentiment_enabled: bool = Field(default=False, validation_alias="SENTIMENT_ENABLED")
    sentiment_model_name: str = Field(default="ProsusAI/finbert", validation_alias="SENTIMENT_MODEL_NAME")
    sentiment_model_version: str = Field(default="1", validation_alias="SENTIMENT_MODEL_VERSION")
    sentiment_device: str = Field(default="cpu", validation_alias="SENTIMENT_DEVICE")
    sentiment_batch_size: int = Field(default=16, validation_alias="SENTIMENT_BATCH_SIZE")
    sentiment_max_text_chars: int = Field(default=512, validation_alias="SENTIMENT_MAX_TEXT_CHARS")
    sentiment_interval_minutes: int = Field(default=30, validation_alias="SENTIMENT_INTERVAL_MINUTES")

    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    sentiment_llm_enabled: bool = Field(default=False, validation_alias="SENTIMENT_LLM_ENABLED")
    sentiment_llm_model: str = Field(default="gemini-2.5-flash", validation_alias="SENTIMENT_LLM_MODEL")
    sentiment_llm_model_version: str = Field(default="1", validation_alias="SENTIMENT_LLM_MODEL_VERSION")
    sentiment_llm_neutral_only: bool = Field(default=True, validation_alias="SENTIMENT_LLM_NEUTRAL_ONLY")
    sentiment_llm_batch_size: int = Field(default=5, validation_alias="SENTIMENT_LLM_BATCH_SIZE")
    sentiment_llm_timeout_seconds: int = Field(default=60, validation_alias="SENTIMENT_LLM_TIMEOUT")
    news_title_dedup_hours: int = Field(default=6, validation_alias="NEWS_TITLE_DEDUP_HOURS")

    macro_brief_enabled: bool = Field(default=True, validation_alias="MACRO_BRIEF_ENABLED")
    macro_brief_model: str = Field(default="gemini-2.5-flash", validation_alias="MACRO_BRIEF_MODEL")
    macro_brief_timeout_seconds: int = Field(default=60, validation_alias="MACRO_BRIEF_TIMEOUT")

    foundation_models_enabled: bool = Field(
        default=False,
        validation_alias="FOUNDATION_MODELS_ENABLED",
    )
    foundation_device: str = Field(default="cpu", validation_alias="FOUNDATION_DEVICE")
    foundation_model_cache_dir: str | None = Field(
        default=None,
        validation_alias="FOUNDATION_MODEL_CACHE_DIR",
    )
    foundation_max_context: int = Field(default=1024, validation_alias="FOUNDATION_MAX_CONTEXT")
    foundation_max_horizon: int = Field(default=256, validation_alias="FOUNDATION_MAX_HORIZON")

    alpaca_api_key: str = Field(default="", validation_alias="ALPACA_API_KEY")
    alpaca_secret_key: str = Field(default="", validation_alias="ALPACA_SECRET_KEY")
    alpaca_base_url: str = Field(
        default="https://api.alpaca.markets",
        validation_alias="ALPACA_BASE_URL",
    )
    alpaca_base_paper_url: str = Field(
        default="https://paper-api.alpaca.markets",
        validation_alias="ALPACA_BASE_PAPER_URL",
    )
    alpaca_data_base_url: str = Field(
        default="https://data.alpaca.markets",
        validation_alias="ALPACA_DATA_BASE_URL",
    )
    crypto_intraday_source: str = Field(
        default="alpaca",
        validation_alias="CRYPTO_INTRADAY_SOURCE",
    )
    trading_mode_paper: bool = Field(default=True, validation_alias="TRADING_MODE_PAPER")
    max_position_pct: float = Field(default=5.0, validation_alias="MAX_POSITION_PCT")
    max_exposure_pct: float = Field(default=80.0, validation_alias="MAX_EXPOSURE_PCT")
    daily_loss_limit_pct: float = Field(default=5.0, validation_alias="DAILY_LOSS_LIMIT_PCT")
    max_orders_per_minute: int = Field(default=10, validation_alias="MAX_ORDERS_PER_MINUTE")
    deployment_max_drawdown_pct: float = Field(
        default=15.0,
        validation_alias="DEPLOYMENT_MAX_DRAWDOWN_PCT",
    )
    stale_data_max_missed_slots: int = Field(
        default=2,
        validation_alias="STALE_DATA_MAX_MISSED_SLOTS",
    )
    stale_data_block_orders: bool = Field(
        default=True,
        validation_alias="STALE_DATA_BLOCK_ORDERS",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def fundamentals_addon_active(self) -> bool:
        return self.tiingo_fundamentals_tier.startswith("addon_")

    @property
    def alpaca_configured(self) -> bool:
        return bool(self.alpaca_api_key and self.alpaca_secret_key)

    @property
    def trading_mode(self) -> str:
        return "paper" if self.trading_mode_paper else "live"

    @property
    def paper_trading_only(self) -> bool:
        return self.trading_mode_paper

    @property
    def effective_alpaca_base_url(self) -> str:
        raw = self.alpaca_base_paper_url if self.trading_mode_paper else self.alpaca_base_url
        normalized = raw.rstrip("/")
        if normalized.endswith("/v2"):
            normalized = normalized[:-3]
        return normalized


@lru_cache
def get_settings() -> Settings:
    import os

    overrides: dict = {}
    if url := os.getenv("TIINGO_DATABASE_URL"):
        overrides["database_url"] = url
    if sync := os.getenv("TIINGO_DATABASE_SYNC_URL"):
        overrides["database_sync_url"] = sync
    return Settings(**overrides) if overrides else Settings()
