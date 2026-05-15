"""Provider registry — returns correct DataProvider by name."""
from .alpaca_provider import AlpacaProvider
from .base_provider import DataProvider
from .fmp_provider import FMPProvider
from .polygon_provider import PolygonProvider
from .tiingo_provider import TiingoProvider
from .yfinance_provider import YFinanceProvider

_PROVIDER_MAP: dict[str, type[DataProvider]] = {
    "polygon": PolygonProvider,
    "alpaca": AlpacaProvider,
    "yfinance": YFinanceProvider,
    "fmp": FMPProvider,
    "tiingo": TiingoProvider,
}


def get_provider(name: str) -> DataProvider:
    cls = _PROVIDER_MAP.get(name.lower())
    if cls is None:
        raise ValueError(f"Unknown provider '{name}'. Valid: {list(_PROVIDER_MAP)}")
    return cls()


__all__ = [
    "DataProvider",
    "PolygonProvider",
    "AlpacaProvider",
    "YFinanceProvider",
    "FMPProvider",
    "TiingoProvider",
    "get_provider",
]
