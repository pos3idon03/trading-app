from features.backtesting.trade_exits import (
    TradeExitConfig,
    evaluate_position_exit,
    intrabar_long_exit,
    resolve_trade_exit_config,
)


def test_intrabar_long_exit_stop_before_profit():
    assert intrabar_long_exit(105.0, 94.0, profit_level=110.0, stop_level=95.0) == "stop"


def test_intrabar_long_exit_profit_when_stop_not_hit():
    assert intrabar_long_exit(105.0, 96.0, profit_level=104.0, stop_level=90.0) == "profit"


def test_resolve_trade_exit_config_binary_defaults():
    cfg = resolve_trade_exit_config({"label_mode": "binary", "label_horizon": 5})
    assert cfg.policy == "label_horizon"
    assert cfg.max_hold_bars == 5


def test_resolve_trade_exit_config_meta_label_defaults():
    cfg = resolve_trade_exit_config({"label_mode": "meta_label", "max_horizon_bars": 48})
    assert cfg.policy == "atr_bracket"
    assert cfg.max_hold_bars == 48


def test_evaluate_position_exit_max_hold_at_open():
    bars = [{"open": 100, "high": 101, "low": 99, "close": 100}] * 10
    config = TradeExitConfig(
        policy="label_horizon",
        max_hold_bars=3,
        profit_atr_mult=2.0,
        stop_atr_mult=1.5,
        atr_period=14,
    )
    decision = evaluate_position_exit(
        bar_index=5,
        bar=bars[5],
        entry_bar_index=2,
        entry_price=100.0,
        bars=bars,
        config=config,
    )
    assert decision is not None
    assert decision.reason == "max_hold"
    assert decision.fill_price == 100.0


def test_evaluate_position_exit_signal_only_inactive():
    config = TradeExitConfig(
        policy="signal_only",
        max_hold_bars=5,
        profit_atr_mult=2.0,
        stop_atr_mult=1.5,
        atr_period=14,
    )
    assert not config.is_active()
    bars = [{"open": 100, "high": 50, "low": 40, "close": 45}]
    assert evaluate_position_exit(
        bar_index=1,
        bar=bars[0],
        entry_bar_index=0,
        entry_price=100.0,
        bars=bars,
        config=config,
    ) is None
