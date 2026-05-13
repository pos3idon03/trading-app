from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173"

    # Database
    database_url: str
    database_sync_url: str

    # Market Data APIs
    polygon_api_key: str = ""
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_base_url: str = "https://paper-api.alpaca.markets"
    alpaca_base_paper_url: str = "https://paper-api.alpaca.markets/v2"
    alpaca_data_ws_url: str = "wss://stream.data.alpaca.markets/v2/iex"
    fmp_api_key: str = ""

    # AI Agents (Phase 4)
    openai_api_key: str = ""
    newsapi_key: str = ""
    fred_api_key: str = ""

    # Gemini fallback (Google AI Studio)
    gemini_api_key: str = ""
    llm_fallback_enabled: bool = True
    llm_request_timeout: int = 120

    # Scheduler
    enable_scheduler: bool = True

    # Live Trading & Execution (Phase 5-6)
    trading_mode: str = "paper"
    max_position_pct: float = 5.0
    max_exposure_pct: float = 80.0
    daily_loss_limit_pct: float = 5.0
    max_orders_per_minute: int = 10

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
