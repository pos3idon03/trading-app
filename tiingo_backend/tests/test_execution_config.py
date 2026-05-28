import pytest


@pytest.mark.parametrize(
    ("paper", "paper_url", "live_url", "expected"),
    [
        (True, "https://paper-api.alpaca.markets/v2", "https://api.alpaca.markets", "https://paper-api.alpaca.markets"),
        (False, "https://paper-api.alpaca.markets", "https://api.alpaca.markets/v2", "https://api.alpaca.markets"),
        (True, "https://paper-api.alpaca.markets/", "https://api.alpaca.markets", "https://paper-api.alpaca.markets"),
    ],
)
def test_effective_alpaca_base_url(monkeypatch, paper, paper_url, live_url, expected):
    monkeypatch.setenv("TRADING_MODE_PAPER", "true" if paper else "false")
    monkeypatch.setenv("ALPACA_BASE_PAPER_URL", paper_url)
    monkeypatch.setenv("ALPACA_BASE_URL", live_url)
    from config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    assert settings.effective_alpaca_base_url == expected
    assert settings.trading_mode == ("paper" if paper else "live")
    get_settings.cache_clear()


def test_trading_mode_paper_defaults_true(monkeypatch):
    monkeypatch.delenv("TRADING_MODE_PAPER", raising=False)
    from config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    assert settings.trading_mode_paper is True
    assert settings.trading_mode == "paper"
    get_settings.cache_clear()
