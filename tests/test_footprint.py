import pandas as pd
import pytest

from orderflow import footprint as fpm
from orderflow.data.alpaca import normalize_symbol


def _bars():
    idx = pd.date_range("2026-01-01", periods=3, freq="min", tz="UTC")
    return pd.DataFrame(
        {
            "open": [100.0, 102.0, 101.0],
            "high": [103.0, 102.5, 101.0],
            "low": [100.0, 100.0, 101.0],
            "close": [103.0, 100.0, 101.0],
            "volume": [8.0, 6.0, 2.0],
        },
        index=idx,
    )


def test_from_bars_conserves_volume_and_signs_delta():
    bars = _bars()
    fp = fpm.from_bars(bars, 1.0)
    assert fp.groupby("bar")["volume"].sum().tolist() == pytest.approx([8.0, 6.0, 2.0])
    d = fpm.bar_delta(fp, len(bars))
    assert d[0] == pytest.approx(8.0)  # closed on the high: all buying
    assert d[1] == pytest.approx(-6.0)  # closed on the low: all selling
    assert d[2] == pytest.approx(0.0)  # no range: 50/50
    assert sorted(fp[fp.bar == 0]["bin"]) == [100, 101, 102, 103]


def test_from_trades_uses_taker_side():
    bars = _bars()
    t = pd.DataFrame(
        {"price": [100.2, 100.7, 102.1, 101.0], "size": [1.0, 2.0, 0.5, 3.0], "side": ["B", "S", "B", "B"]},
        index=pd.to_datetime(
            ["2026-01-01 00:00:10", "2026-01-01 00:00:50", "2026-01-01 00:01:05", "2026-01-01 00:05:00"], utc=True
        ),
    )
    fp = fpm.from_trades(bars, t, 1.0)
    # The 00:05 trade has no bar and is dropped.
    assert fp["volume"].sum() == pytest.approx(3.5)
    row = fp[(fp.bar == 0) & (fp.bin == 100)].iloc[0]
    assert (row.buy, row.sell) == (1.0, 2.0)
    assert fpm.bar_delta(fp, 3).tolist() == pytest.approx([-1.0, 0.5, 0.0])


@pytest.mark.parametrize("price,expected", [(90_000, 50.0), (3_000, 2.0), (19_880, 10.0), (0.5, 0.0002)])
def test_auto_bin_size(price, expected):
    assert fpm.auto_bin_size(price) == pytest.approx(expected)


@pytest.mark.parametrize("raw", ["BTC/USD", "btcusd", "BTC-USD", "btc_usd"])
def test_normalize_symbol(raw):
    assert normalize_symbol(raw) == "BTC/USD"
