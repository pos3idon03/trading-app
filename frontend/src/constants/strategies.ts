export interface StrategyOption {
  value: string;
  label: string;
  group: string;
}

export const STRATEGIES: StrategyOption[] = [
  // ── Original ──────────────────────────────────────────────────────────
  { value: 'ma_crossover',         label: 'MA Crossover',                        group: 'Original' },
  { value: 'mean_reversion',       label: 'Mean Reversion',                      group: 'Original' },
  { value: 'breakout',             label: 'Breakout (Volatility Expansion)',      group: 'Original' },
  { value: 'trend_pullback',       label: 'Trend-Following with Pullbacks',       group: 'Original' },
  { value: 'gap_fade',             label: 'Gap Fade',                            group: 'Original' },
  { value: 'vrp_harvest',          label: 'VRP Harvest',                         group: 'Original' },
  // ── Moving Average ────────────────────────────────────────────────────
  { value: 'sma_cross',            label: 'SMA Cross (Golden / Death Cross)',     group: 'Moving Average' },
  { value: 'ema_cross',            label: 'EMA Cross',                           group: 'Moving Average' },
  { value: 'sma_break',            label: 'Standard SMA Break (20 / 50 / 200)',  group: 'Moving Average' },
  // ── Momentum ──────────────────────────────────────────────────────────
  { value: 'macd',                 label: 'MACD',                                group: 'Momentum' },
  { value: 'rsi',                  label: 'RSI (Relative Strength Index)',        group: 'Momentum' },
  { value: 'lrsi',                 label: 'LRSI (Laguerre RSI)',                 group: 'Momentum' },
  { value: 'new_high_low',         label: 'New 52-Week High / Low',              group: 'Momentum' },
  { value: 'momentum_rotation',    label: 'Momentum Rotation',                   group: 'Momentum' },
  // ── Volatility / Price-Level ──────────────────────────────────────────
  { value: 'atr_trailing_stop',    label: 'ATR Trailing Stop',                   group: 'Volatility' },
  { value: 'vwap_cross',           label: 'VWAP Cross',                          group: 'Volatility' },
  { value: 'grid_trading',         label: 'Grid Trading',                        group: 'Volatility' },
  { value: 'wedge_compression',    label: 'Horizontal / Wedge Compression',      group: 'Volatility' },
  // ── Mean Reversion ────────────────────────────────────────────────────
  { value: 'mean_reversion_trend', label: 'Mean Reversion to Trend',             group: 'Mean Reversion' },
  { value: 'mean_reversion_range', label: 'Mean Reversion in Range',             group: 'Mean Reversion' },
  { value: 'reverting_market',     label: 'Reverting Market (Sideways)',          group: 'Mean Reversion' },
  // ── Breakout ──────────────────────────────────────────────────────────
  { value: 'range_breakout',       label: 'Range Breakout',                      group: 'Breakout' },
  { value: 'orb',                  label: 'Open Range Breakout (ORB)',            group: 'Breakout' },
  // ── Seasonal ──────────────────────────────────────────────────────────
  { value: 'seasonal',             label: 'Seasonal / Sell in May',              group: 'Seasonal' },
];

export const STRATEGY_GROUPS = [...new Set(STRATEGIES.map((s) => s.group))];

export const DEFAULT_PARAMS_MAP: Record<string, Record<string, number>> = {
  ma_crossover:         { fast_window: 10, slow_window: 50 },
  mean_reversion:       { lookback: 20, z_threshold: 2.0 },
  breakout:             { bb_window: 20, bb_std: 2.0, squeeze_lookback: 120, donchian_window: 20 },
  trend_pullback:       { adx_period: 14, adx_threshold: 25.0, stoch_period: 14, stoch_smooth: 3, oversold: 20.0, overbought: 80.0 },
  gap_fade:             { gap_threshold: 0.03, min_gap_fill_bars: 5 },
  vrp_harvest:          { rv_window: 20, iv_proxy_window: 60, z_entry: -1.0, z_exit: 0.5 },
  sma_cross:            { fast_window: 50, slow_window: 200 },
  ema_cross:            { fast_span: 12, slow_span: 26 },
  sma_break:            { sma_window: 200 },
  macd:                 { fast: 12, slow: 26, signal: 9 },
  rsi:                  { period: 14, overbought: 70.0, oversold: 30.0 },
  lrsi:                 { gamma: 0.5, overbought: 0.8, oversold: 0.2 },
  new_high_low:         { lookback: 252 },
  momentum_rotation:    { short_window: 20, long_window: 60, threshold: 0.0 },
  atr_trailing_stop:    { atr_period: 14, atr_multiplier: 3.0, trend_ma: 50 },
  vwap_cross:           { band_pct: 0.0 },
  grid_trading:         { grid_size: 0.02, num_levels: 5 },
  wedge_compression:    { atr_period: 14, compression_lookback: 20, compression_ratio: 0.5 },
  mean_reversion_trend: { ma_window: 50, z_threshold: 1.5, adx_period: 14, adx_threshold: 25.0 },
  mean_reversion_range: { bb_window: 20, bb_std: 2.0, adx_period: 14, adx_max: 20.0 },
  reverting_market:     { rsi_period: 14, rsi_upper: 60.0, rsi_lower: 40.0, adx_period: 14, adx_max: 20.0 },
  range_breakout:       { lookback: 20 },
  orb:                  { opening_bars: 6 },
  seasonal:             { sell_month: 5, buy_month: 11 },
};

export const DEFAULT_GRID_MAP: Record<string, Record<string, number[]>> = {
  ma_crossover:         { fast_window: [5, 10, 20], slow_window: [30, 50, 100] },
  mean_reversion:       { lookback: [10, 20, 30], z_threshold: [1.5, 2.0, 2.5] },
  breakout:             { bb_window: [15, 20, 25], squeeze_lookback: [60, 120, 180], donchian_window: [15, 20, 25] },
  trend_pullback:       { adx_period: [10, 14, 20], adx_threshold: [20.0, 25.0, 30.0], oversold: [15.0, 20.0, 25.0] },
  gap_fade:             { gap_threshold: [0.02, 0.03, 0.05] },
  vrp_harvest:          { rv_window: [10, 20, 30], iv_proxy_window: [40, 60, 90], z_entry: [-1.5, -1.0, -0.5] },
  sma_cross:            { fast_window: [20, 50, 100], slow_window: [100, 150, 200] },
  ema_cross:            { fast_span: [5, 12, 20], slow_span: [20, 26, 50] },
  sma_break:            { sma_window: [20, 50, 100, 200] },
  macd:                 { fast: [8, 12, 16], slow: [21, 26, 30], signal: [7, 9, 11] },
  rsi:                  { period: [10, 14, 21], overbought: [65.0, 70.0, 75.0], oversold: [25.0, 30.0, 35.0] },
  lrsi:                 { gamma: [0.3, 0.5, 0.7], overbought: [0.75, 0.8, 0.85], oversold: [0.15, 0.2, 0.25] },
  new_high_low:         { lookback: [63, 126, 252] },
  momentum_rotation:    { short_window: [10, 20, 30], long_window: [40, 60, 90] },
  atr_trailing_stop:    { atr_period: [10, 14, 21], atr_multiplier: [2.0, 3.0, 4.0], trend_ma: [20, 50, 100] },
  vwap_cross:           { band_pct: [0.0, 0.01, 0.02] },
  grid_trading:         { grid_size: [0.01, 0.02, 0.03], num_levels: [3, 5, 8] },
  wedge_compression:    { atr_period: [10, 14, 21], compression_lookback: [10, 20, 30], compression_ratio: [0.3, 0.5, 0.7] },
  mean_reversion_trend: { ma_window: [20, 50, 100], z_threshold: [1.0, 1.5, 2.0], adx_threshold: [20.0, 25.0, 30.0] },
  mean_reversion_range: { bb_window: [15, 20, 25], adx_max: [15.0, 20.0, 25.0] },
  reverting_market:     { rsi_period: [10, 14, 21], rsi_upper: [55.0, 60.0, 65.0], rsi_lower: [35.0, 40.0, 45.0] },
  range_breakout:       { lookback: [10, 20, 40] },
  orb:                  { opening_bars: [3, 6, 12] },
  seasonal:             { sell_month: [4, 5, 6], buy_month: [10, 11, 12] },
};

export const OPTIMIZE_METRICS = [
  { value: 'sharpe_ratio',  label: 'Sharpe Ratio' },
  { value: 'sortino_ratio', label: 'Sortino Ratio' },
  { value: 'total_return',  label: 'Total Return' },
  { value: 'profit_factor', label: 'Profit Factor' },
];
