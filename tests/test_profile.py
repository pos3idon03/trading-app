import numpy as np
import pandas as pd
import pytest

from orderflow import footprint as fpm
from orderflow.config import ProfileConfig
from orderflow.profile import Profile


def make_profile(volume, delta, tpo, cfg=None) -> Profile:
    bins = np.arange(100, 100 + len(volume))
    volume = np.asarray(volume, float)
    delta = np.asarray(delta, float)
    t = pd.DataFrame(
        {
            "volume": volume,
            "buy": (volume + delta) / 2,
            "sell": (volume - delta) / 2,
            "delta": delta,
            "tpo": tpo,
        },
        index=pd.Index(bins, name="bin"),
    )
    return Profile(t, 1.0, cfg or ProfileConfig(smooth_bins=1))


# Two balance areas with a thin, one-sided, single-print gap between them.
VOL = [5, 40, 100, 60, 8, 6, 7, 50, 70, 30]
DELTA = [0, 2, -3, 1, 6, 5, 6, 2, -1, 0]
TPO = [2, 6, 8, 6, 1, 1, 1, 5, 6, 3]


def test_poc_and_value_area():
    p = make_profile(VOL, DELTA, TPO)
    assert p.poc_bin == 102
    val, vah = p.value_area()
    covered = sum(VOL[val - 100 : vah - 100 + 1])
    assert covered >= 0.7 * sum(VOL)
    assert val <= 102 <= vah


def test_hvn_lvn():
    p = make_profile(VOL, DELTA, TPO)
    assert p.hvn_bins() == [102, 108]
    assert set(p.lvn_bins()) >= {104, 105, 106}
    assert 102 not in p.lvn_bins()


def test_single_prints_are_interior_only():
    tpo = [1, 6, 8, 6, 1, 1, 1, 5, 6, 1]  # tails at both ends are not single prints
    p = make_profile(VOL, DELTA, tpo)
    assert p.single_print_bins() == [104, 105, 106]


def test_delta_outliers_need_size_and_one_sidedness():
    p = make_profile(VOL, DELTA, TPO)
    # Bins 104-106: |delta| well above median and ~75% of their volume.
    assert set(p.delta_outlier_bins()) == {104, 105, 106}


def test_level_is_confluence_with_direction():
    p = make_profile(VOL, DELTA, TPO)
    levels = p.levels()
    assert len(levels) == 1
    lv = levels[0]
    assert (lv.low_bin, lv.high_bin) == (104, 106)
    assert lv.direction == 1
    assert lv.low == 104 and lv.high == 107


def test_no_level_without_single_prints():
    p = make_profile(VOL, DELTA, [2, 6, 8, 6, 3, 3, 3, 5, 6, 3])
    assert p.levels() == []


def test_seller_level_is_resistance():
    p = make_profile(VOL, [-d for d in DELTA], TPO)
    assert [lv.direction for lv in p.levels()] == [-1]


def test_next_hvn():
    p = make_profile(VOL, DELTA, TPO)
    assert p.next_hvn_above(105) == pytest.approx(108.5)
    assert p.next_hvn_below(105) == pytest.approx(102.5)
    assert p.next_hvn_above(109) is None


def test_build_from_bars_counts_tpo_periods():
    idx = pd.date_range("2026-01-01", periods=90, freq="min", tz="UTC")
    bars = pd.DataFrame({"open": 10.0, "high": 10.9, "low": 10.0, "close": 10.5, "volume": 1.0}, index=idx)
    bars.iloc[30:60, :] = [12.0, 12.9, 12.0, 12.5, 1.0]
    fp = fpm.from_bars(bars, 1.0)
    p = Profile.build(fp, bars, 1.0, ProfileConfig(), idx[0])
    assert p.table.loc[10, "tpo"] == 2  # periods 0 and 2
    assert p.table.loc[12, "tpo"] == 1
    assert p.table.loc[11, "tpo"] == 0
    assert p.table["volume"].sum() == pytest.approx(90.0)
