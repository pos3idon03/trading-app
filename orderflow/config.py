"""Strategy and backtest settings.

Every rule in the strategy is driven by a number in here, so the setup from
the video ("one price where LVN + single prints + delta outlier line up,
sellers absorbed there, buyers take control, target the next HVN") is
explicit and can be tuned or optimised.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProfileConfig:
    # Price bucket size. None = automatic (about 0.05% of the session's first price).
    bin_size: float | None = None
    # TPO period length, in minutes (market profile standard is 30).
    tpo_minutes: int = 30
    # Value area share of volume.
    value_area: float = 0.70
    # Smoothing window (bins) applied to volume before finding HVN/LVN.
    smooth_bins: int = 3
    # HVN: local volume peak at least this share of the biggest peak.
    hvn_ratio: float = 0.45
    # LVN: a valley whose volume is at most this share of the higher
    # volume found both above and below it.
    lvn_valley_ratio: float = 0.5
    # Delta outlier: |delta| >= mult * median |delta| of traded bins ...
    delta_outlier_mult: float = 2.0
    # ... and the bin is one-sided: |delta| / volume >= this.
    delta_outlier_imbalance: float = 0.4
    # How many bins apart LVN, single print and delta outlier may be and
    # still count as "one price".
    confluence_tolerance_bins: int = 1


@dataclass(frozen=True)
class StrategyConfig:
    # Price must have closed this many bins away from a level before a
    # return to it counts as a pullback.
    min_departure_bins: int = 2
    # A bar "touches" the level if it trades within this many bins of it.
    touch_tolerance_bins: int = 0
    # A close beyond the level by more than this many bins = level failed.
    break_tolerance_bins: int = 1
    # Absorption: while touching, at least one bar's opposite-side delta must
    # reach absorb_mult * median |bar delta| of the session so far.
    absorb_mult: float = 5.0
    # Bars allowed between the first touch and the confirmation bar.
    confirm_within_bars: int = 15
    # Stop goes this many bins beyond the level / touch extreme.
    stop_buffer_bins: int = 1
    # Skip trades whose reward:risk to the next HVN is below this.
    min_reward_risk: float = 1.0
    max_trades_per_session: int = 3
    allow_longs: bool = True
    allow_shorts: bool = True


@dataclass(frozen=True)
class BacktestConfig:
    initial_equity: float = 10_000.0
    # Fraction of equity risked per trade (distance entry -> stop).
    risk_per_trade: float = 0.01
    # Max position notional as a multiple of equity.
    max_leverage: float = 1.0
    # Per side. Entries/exits are market orders = taker. 25 bps is Alpaca's
    # crypto taker fee at the lowest volume tier; set it to your own tier.
    fee_bps: float = 25.0
    slippage_bps: float = 2.0  # per side, against us
    # Session boundaries: crypto trades 24/7, so a "session" is one UTC day
    # by default. Open positions are closed at session end.
    session_start_hour_utc: int = 0
    session_hours: int = 24


@dataclass(frozen=True)
class Config:
    profile: ProfileConfig = field(default_factory=ProfileConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
