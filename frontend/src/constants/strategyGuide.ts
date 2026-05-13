/**
 * Educational content for every strategy in the backtest catalog.
 *
 * Buy/sell descriptions are derived directly from the corresponding
 * *_signals functions in backend/features/backtesting/strategies/.
 * This file is the single source of truth for UI copy; no API calls needed.
 */

export interface StrategyGuideContent {
  overview: string;
  whenBuy: string;
  whenSell: string;
  valueAndCaveats: string;
  paramDescriptions: Record<string, string>;
}

export const STRATEGY_GUIDE: Record<string, StrategyGuideContent> = {
  // ── Original ──────────────────────────────────────────────────────────────

  ma_crossover: {
    overview:
      'Computes two simple moving averages — one short (fast) and one long (slow) — over closing prices. ' +
      'When the faster average rises above the slower one, momentum is considered positive; the reverse signals a downturn.',
    whenBuy:
      'A buy signal fires on the bar where the fast SMA first crosses above the slow SMA (the "golden cross").',
    whenSell:
      'A sell signal fires on the bar where the fast SMA first crosses below the slow SMA (the "death cross").',
    valueAndCaveats:
      'Simple and broadly applicable. Works well in sustained trends but produces frequent false signals in choppy, sideways markets. ' +
      'Longer windows reduce noise at the cost of slower reaction time.',
    paramDescriptions: {
      fast_window: 'Number of bars used for the short-term (fast) moving average. Smaller values react more quickly to price changes.',
      slow_window: 'Number of bars used for the long-term (slow) moving average. Must be larger than fast_window to form a meaningful crossover.',
    },
  },

  mean_reversion: {
    overview:
      'Calculates a rolling z-score of the closing price relative to its recent mean and standard deviation. ' +
      'Assumes prices will revert to their statistical mean after an unusually large move away from it.',
    whenBuy:
      'Buys when the z-score falls below the negative threshold (e.g. −2.0), meaning price has dropped more than 2 standard deviations below its rolling mean.',
    whenSell:
      'Sells when the z-score crosses back above zero — that is, when price returns to its rolling mean.',
    valueAndCaveats:
      'Effective in range-bound, mean-reverting environments. Can suffer large drawdowns in trending markets where the z-score stays extreme for extended periods. ' +
      'Not suitable for strongly trending assets.',
    paramDescriptions: {
      lookback: 'Rolling window (in bars) used to compute the mean and standard deviation of price.',
      z_threshold: 'Number of standard deviations below the mean required to trigger a buy. Higher values mean the price must be more extreme before entering.',
    },
  },

  breakout: {
    overview:
      'Combines a Bollinger Band squeeze detector with a Donchian Channel breakout. ' +
      'The squeeze identifies periods of low volatility where a large move is likely; the Donchian breakout confirms the direction of that move.',
    whenBuy:
      'Buys when two conditions are met simultaneously: the Bollinger Band width is at its narrowest point over the last squeeze_lookback bars (the coil is tightest) AND ' +
      'price closes above the prior bar\'s Donchian Channel high.',
    whenSell:
      'Sells when price closes below the midpoint of the Donchian Channel (the average of the N-bar high and low).',
    valueAndCaveats:
      'Targets explosive moves that follow extended low-volatility consolidations. ' +
      'False breakouts can occur; combining with volume confirmation reduces but does not eliminate this risk.',
    paramDescriptions: {
      bb_window: 'Lookback window for Bollinger Band calculations (mean and standard deviation of close).',
      bb_std: 'Number of standard deviations used to compute Bollinger Band width. Does not affect entry directly, only the bandwidth metric.',
      squeeze_lookback: 'Number of bars over which to measure whether Bollinger Band width is at a minimum. Larger values find rarer, more compressed setups.',
      donchian_window: 'Number of bars for the Donchian Channel (highest high and lowest low). Determines the breakout level and mid-band exit.',
    },
  },

  trend_pullback: {
    overview:
      'Combines the ADX trend-strength indicator with the Stochastic oscillator to enter during a confirmed trend on short-term weakness. ' +
      'The idea is to buy the dip inside a healthy uptrend rather than chasing price at highs.',
    whenBuy:
      'Buys when three conditions align: ADX is above the threshold (confirming a strong trend), the Stochastic %K is in the oversold zone, AND %K crosses above %D (momentum turning up).',
    whenSell:
      'Sells when the Stochastic %K rises above the overbought level, indicating the short-term pullback has fully recovered.',
    valueAndCaveats:
      'Produces higher-quality entry points in strong directional markets. ' +
      'If the broader trend reverses while waiting for a stochastic signal, the strategy may enter against the new direction.',
    paramDescriptions: {
      adx_period: 'Lookback period for the ADX calculation. Shorter periods react faster; longer periods are smoother.',
      adx_threshold: 'Minimum ADX value required to confirm a strong trend. Values below 20 are typically considered ranging.',
      stoch_period: 'Lookback window for the raw Stochastic %K calculation.',
      stoch_smooth: 'Smoothing period applied to %K to produce the signal line %D.',
      oversold: 'Stochastic %K level below which the market is considered oversold. Entry requires %K to be in this zone.',
      overbought: 'Stochastic %K level above which the position is exited.',
    },
  },

  gap_fade: {
    overview:
      'A mean-reversion strategy targeting overnight gap-ups that are immediately rejected. ' +
      'When a stock opens significantly higher than its prior close but fails to hold that gap by closing below its own open, ' +
      'there is evidence that buyers were unable to sustain the move.',
    whenBuy:
      'Buys (short the gap) when the open is more than gap_threshold percent above the prior close AND the bar closes below its own open (rejection candle). ' +
      'This is a contrarian, gap-fill trade.',
    whenSell:
      'Sells (exits the trade) once price falls back to the prior close — that is, when the gap has been filled.',
    valueAndCaveats:
      'Works well in equities with frequent overnight gaps driven by earnings or news. ' +
      'Gaps caused by genuine fundamental shifts (e.g. a takeover bid) may not fill; stop-loss discipline is important.',
    paramDescriptions: {
      gap_threshold: 'Minimum fractional gap size (e.g. 0.03 = 3%) required between the prior close and the current open to qualify for a fade setup.',
      min_gap_fill_bars: 'Currently stored as a parameter but not used in signal logic; reserved for future minimum hold-time filtering.',
    },
  },

  vrp_harvest: {
    overview:
      'Harvests the Volatility Risk Premium (VRP) — the well-documented tendency for implied volatility to exceed realised volatility. ' +
      'A longer-window rolling standard deviation proxies implied vol; a shorter-window one measures realised vol. ' +
      'Entry occurs when realised vol is unusually cheap relative to implied vol, favouring a long-volatility or long-carry position.',
    whenBuy:
      'Buys when the z-score of the spread (realised vol minus IV proxy) falls below z_entry — meaning realised vol is significantly below its historical norm relative to the IV proxy.',
    whenSell:
      'Sells when the z-score rises back above z_exit, indicating the spread has normalised or inverted.',
    valueAndCaveats:
      'Historically profitable in equities due to structural vol overpricing. ' +
      'Can suffer sudden, severe losses during volatility spikes (e.g. market crashes). ' +
      'Best used with position-sizing discipline and awareness of tail risk.',
    paramDescriptions: {
      rv_window: 'Rolling window (in bars) for realised volatility calculation using log returns.',
      iv_proxy_window: 'Longer rolling window used to approximate implied volatility. Must be larger than rv_window.',
      z_entry: 'Z-score threshold (negative) at which the spread is considered extreme enough to enter. More negative = rarer, stronger signal.',
      z_exit: 'Z-score level at which the spread is considered normalised and the position is closed.',
    },
  },

  // ── Moving Average ────────────────────────────────────────────────────────

  sma_cross: {
    overview:
      'The classic Golden / Death Cross using two Simple Moving Averages. ' +
      'Defaults to SMA(50) and SMA(200) — the most widely watched institutional indicator. ' +
      'When the 50-day average crosses above the 200-day average, many participants interpret this as the start of a long-term uptrend.',
    whenBuy:
      'Buys when the fast SMA crosses above the slow SMA (golden cross) for the first time — i.e. the fast was below on the prior bar.',
    whenSell:
      'Sells when the fast SMA crosses below the slow SMA (death cross) for the first time.',
    valueAndCaveats:
      'Widely followed, which creates some self-fulfilling momentum. ' +
      'Highly reliable at filtering out secular downtrends but is a lagging indicator that sacrifices significant profit at turns. ' +
      'Best on longer-term (weekly/monthly) charts.',
    paramDescriptions: {
      fast_window: 'Period for the faster SMA. Default 50 — represents roughly one quarter of daily trading.',
      slow_window: 'Period for the slower SMA. Default 200 — represents roughly one year of daily trading. Must be larger than fast_window.',
    },
  },

  ema_cross: {
    overview:
      'An EMA crossover that uses exponentially weighted moving averages instead of simple averages, giving more weight to recent price data. ' +
      'Defaults to the popular 12/26 combination used in MACD.',
    whenBuy:
      'Buys when the fast EMA crosses above the slow EMA — the fast was below on the prior bar and is now above.',
    whenSell:
      'Sells when the fast EMA crosses below the slow EMA.',
    valueAndCaveats:
      'Reacts faster than SMA-based crossovers, reducing lag at the cost of more false signals. ' +
      'Particularly useful for assets with trending momentum and regular pullbacks.',
    paramDescriptions: {
      fast_span: 'Span (half-life equivalent) for the fast EMA. Smaller values weight recent prices more heavily.',
      slow_span: 'Span for the slow EMA. Must be larger than fast_span.',
    },
  },

  sma_break: {
    overview:
      'Watches for price to cross above or below a single SMA level — commonly the 20, 50, or 200-day average. ' +
      'Traders use these levels as dynamic support and resistance.',
    whenBuy:
      'Buys when the closing price crosses above the SMA from below (was below on the prior bar, is above today).',
    whenSell:
      'Sells when the closing price crosses below the SMA from above.',
    valueAndCaveats:
      'Very simple and transparent. The 200-SMA is especially meaningful because it is tracked by institutional investors globally. ' +
      'Generates whipsaws in low-trend environments where price oscillates around the average.',
    paramDescriptions: {
      sma_window: 'Period for the single SMA used as the dynamic support/resistance level. Common choices: 20 (short-term), 50 (medium), 200 (long-term).',
    },
  },

  // ── Momentum ──────────────────────────────────────────────────────────────

  macd: {
    overview:
      'MACD (Moving Average Convergence/Divergence) subtracts a slow EMA from a fast EMA to create the MACD line, ' +
      'then plots a signal line as an EMA of the MACD line. The crossover of these two lines indicates momentum shifts.',
    whenBuy:
      'Buys when the MACD line crosses above the signal line — meaning short-term momentum has just turned positive.',
    whenSell:
      'Sells when the MACD line crosses below the signal line.',
    valueAndCaveats:
      'One of the most widely used technical indicators. The histogram (MACD minus signal) visually shows momentum acceleration. ' +
      'Divergences between price and MACD can be powerful early warning signals. ' +
      'Prone to whipsaws in ranging, low-momentum conditions.',
    paramDescriptions: {
      fast: 'Span for the fast EMA used in the MACD line calculation. Default 12.',
      slow: 'Span for the slow EMA. Default 26. Must be larger than fast.',
      signal: 'Span of the EMA applied to the MACD line to create the signal line. Default 9.',
    },
  },

  rsi: {
    overview:
      'RSI (Relative Strength Index) measures the speed and magnitude of recent price changes on a 0–100 scale. ' +
      'Values above 70 conventionally indicate overbought conditions; values below 30 indicate oversold conditions.',
    whenBuy:
      'Buys on the first bar where RSI rises back to or above the oversold level after having been below it — a cross-back, not a simple level touch.',
    whenSell:
      'Sells on the first bar where RSI falls back to or below the overbought level after having been above it.',
    valueAndCaveats:
      'Very effective in range-bound markets. In strong trends, RSI can remain overbought or oversold for prolonged periods, ' +
      'causing premature exits or repeated false entries. Divergence between RSI and price is a powerful supplemental signal.',
    paramDescriptions: {
      period: 'Lookback period for the RSI calculation. Default 14. Shorter periods produce a more volatile oscillator.',
      overbought: 'RSI level above which the asset is considered overbought. Exit fires when RSI drops back below this level.',
      oversold: 'RSI level below which the asset is considered oversold. Entry fires when RSI crosses back above this level.',
    },
  },

  lrsi: {
    overview:
      'Laguerre RSI applies a Laguerre filter to the price series before computing RSI, ' +
      'producing a smoother oscillator that reduces noise while remaining relatively responsive. ' +
      'Output is normalised to a 0–1 scale.',
    whenBuy:
      'Buys when LRSI crosses back above the oversold threshold after having been below it.',
    whenSell:
      'Sells when LRSI crosses back below the overbought threshold after having been above it.',
    valueAndCaveats:
      'Generates fewer false signals than standard RSI in volatile assets due to its smoothing properties. ' +
      'The gamma parameter significantly affects responsiveness — values closer to 1 smooth more aggressively.',
    paramDescriptions: {
      gamma: 'Laguerre filter smoothing coefficient (0–1). Higher values produce a smoother but slower oscillator. Default 0.5.',
      overbought: 'LRSI level (0–1 scale) above which the asset is overbought. Default 0.8.',
      oversold: 'LRSI level (0–1 scale) below which the asset is oversold. Default 0.2.',
    },
  },

  new_high_low: {
    overview:
      'A momentum-breakout strategy based on price extremes. ' +
      'Making a new N-period high is evidence that buyers are winning decisively; ' +
      'making a new N-period low is evidence that sellers have taken control.',
    whenBuy:
      'Buys on the first bar where closing price equals the rolling N-period maximum — a new high just made, not an existing one.',
    whenSell:
      'Sells on the first bar where closing price equals the rolling N-period minimum — a new low just made.',
    valueAndCaveats:
      'Captures strong trending moves and avoids accumulating positions in stagnant assets. ' +
      'Entry naturally happens at the top of a range, which feels counterintuitive but is backed by price-momentum research. ' +
      'Can produce late entries after large runs.',
    paramDescriptions: {
      lookback: 'Number of bars in the rolling window for computing the high and low extremes. Default 252 (≈ 1 year of daily data).',
    },
  },

  momentum_rotation: {
    overview:
      'Compares a short-term price return to a longer-term price return. ' +
      'When recent momentum is stronger than the longer-term trend, the asset is considered to be accelerating — a signal to be long.',
    whenBuy:
      'Buys when the short-term rolling return (e.g. 20-bar) first exceeds the long-term rolling return (e.g. 60-bar) plus any threshold offset.',
    whenSell:
      'Sells when the short-term return falls back below the long-term return, indicating momentum has decelerated.',
    valueAndCaveats:
      'Works well in cross-sectional momentum portfolios where assets are ranked and rotated. ' +
      'On a single asset, the signal can be noisy. ' +
      'Best combined with a universe of assets so capital always rotates to the strongest performer.',
    paramDescriptions: {
      short_window: 'Lookback period (bars) for the short-term return calculation.',
      long_window: 'Lookback period (bars) for the long-term return calculation. Must be larger than short_window.',
      threshold: 'Additional buffer that short_return must exceed above long_return to trigger entry. Set to 0 for a simple crossover.',
    },
  },

  aroon: {
    overview:
      'Aroon measures how recently within a given period price made its highest high (Aroon Up) and lowest low (Aroon Down), ' +
      'expressed as percentages. High Aroon Up with low Aroon Down indicates a fresh uptrend.',
    whenBuy:
      'Buys when Aroon Up crosses above Aroon Down for the first time AND Aroon Up is above the threshold — confirming a fresh, strong uptrend.',
    whenSell:
      'Sells when Aroon Down crosses above Aroon Up, indicating the most recent low occurred more recently than the most recent high.',
    valueAndCaveats:
      'Particularly good at detecting the early stages of new trends. ' +
      'Less prone to whipsaws than many crossover systems because the threshold filters weak signals. ' +
      'Best suited to trending assets and longer timeframes.',
    paramDescriptions: {
      period: 'Number of bars used to locate the highest high and lowest low. Default 52 (≈ 1 year of weekly bars).',
      threshold: 'Minimum Aroon Up value (0–100) required at the time of the crossover to confirm a meaningful uptrend. Default 50.',
    },
  },

  stoch_rsi: {
    overview:
      'Stochastic RSI applies the Stochastic oscillator formula to RSI values rather than price, ' +
      'creating a more sensitive indicator that oscillates between 0 and 1. ' +
      'It is designed to identify when RSI itself is at an extreme relative to its own recent history.',
    whenBuy:
      'Buys when %K (fast line) was in the oversold zone on the prior bar AND %K crosses above the %D signal line.',
    whenSell:
      'Sells when %K was in the overbought zone on the prior bar AND %K crosses below %D.',
    valueAndCaveats:
      'Generates signals more frequently than RSI alone, which increases trading activity. ' +
      'Highly effective in short-term swing trading but can produce many false signals on daily data without additional filters.',
    paramDescriptions: {
      rsi_period: 'Lookback period for the initial RSI calculation.',
      stoch_period: 'Window over which the Stochastic formula is applied to the RSI series.',
      smooth_k: 'Smoothing period applied to the raw %K line.',
      smooth_d: 'Smoothing period applied to %K to produce the %D signal line.',
      overbought: 'Stoch RSI level (0–1) above which %K must have been for a sell signal. Default 0.8.',
      oversold: 'Stoch RSI level (0–1) below which %K must have been for a buy signal. Default 0.2.',
    },
  },

  // ── Volatility / Price-Level ───────────────────────────────────────────────

  atr_trailing_stop: {
    overview:
      'Uses the Average True Range (ATR) to set a dynamic trailing stop that expands and contracts with market volatility. ' +
      'Entry is triggered by price moving above a trend filter; the stop adapts in real time as volatility changes.',
    whenBuy:
      'Buys on the first bar that price closes above the rolling trend MA — a cross from below to above.',
    whenSell:
      'Sells when price closes below the trailing stop level, computed as close minus (atr_multiplier × ATR). ' +
      'This stop moves up as price rises and ATR contracts.',
    valueAndCaveats:
      'Effective at riding trends while protecting gains. ' +
      'In low-volatility environments ATR can produce very tight stops, leading to premature exits. ' +
      'Conversely, very high volatility can create wide stops with large drawdowns before triggering.',
    paramDescriptions: {
      atr_period: 'Lookback period for Average True Range calculation.',
      atr_multiplier: 'Number of ATR units below the close to place the trailing stop. Larger values give more room.',
      trend_ma: 'Period for the trend filter moving average. Price must cross above this MA to generate a buy signal.',
    },
  },

  vwap_cross: {
    overview:
      'Volume-Weighted Average Price (VWAP) is the cumulative ratio of price × volume to total volume. ' +
      'It is widely used by institutional traders as a benchmark; price above VWAP signals intraday bullish sentiment.',
    whenBuy:
      'Buys when closing price crosses above VWAP (plus optional band_pct buffer) for the first time.',
    whenSell:
      'Sells when closing price drops below VWAP, reversing the cross.',
    valueAndCaveats:
      'Most powerful on intraday timeframes where VWAP resets each session. ' +
      'On daily bars the VWAP accumulates over the full series and may diverge significantly from intraday VWAP references. ' +
      'The band_pct parameter can reduce false entries near the VWAP level.',
    paramDescriptions: {
      band_pct: 'Optional percentage buffer added to VWAP. Price must exceed VWAP × (1 + band_pct) to trigger a buy. Set to 0 for a plain VWAP cross.',
    },
  },

  grid_trading: {
    overview:
      'Places virtual buy orders at equally spaced price levels below a rolling baseline and sell orders above it. ' +
      'When price falls to the bottom of the grid the strategy accumulates; when price rises to the top it exits. ' +
      'Best suited to sideways, oscillating markets.',
    whenBuy:
      'Buys on the first bar that price drops to or below the lower grid boundary (baseline minus grid_size × num_levels percentage move).',
    whenSell:
      'Sells on the first bar that price rises to or above the upper grid boundary (baseline plus grid_size × num_levels percentage move).',
    valueAndCaveats:
      'Can generate consistent income in range-bound assets through frequent small profits. ' +
      'Suffers significant losses if price trends strongly in one direction, particularly to the downside. ' +
      'Not suitable for strongly trending markets.',
    paramDescriptions: {
      grid_size: 'Percentage distance between each grid level (e.g. 0.02 = 2%). Smaller values create tighter grids with more levels.',
      num_levels: 'Number of grid levels on each side of the baseline. Determines the total grid span (grid_size × num_levels).',
    },
  },

  wedge_compression: {
    overview:
      'Detects "spring-loaded" compression patterns where ATR has fallen to a multi-period low — the market has become unusually quiet. ' +
      'When price then breaks out above the recent high, the strategy assumes a directional expansion is beginning.',
    whenBuy:
      'Buys when two conditions are simultaneously true: ATR is within (1 + compression_ratio) × its lookback minimum (volatility is compressed) ' +
      'AND closing price is above the prior bar\'s highest high in the compression window.',
    whenSell:
      'Sells when ATR rises above its rolling mean over the compression_lookback window, indicating that volatility has normalised.',
    valueAndCaveats:
      'Excellent at capturing the start of explosive directional moves after consolidation. ' +
      'Can give back a portion of gains while waiting for ATR to expand to its mean. ' +
      'Works best for assets that alternate between compression and expansion phases.',
    paramDescriptions: {
      atr_period: 'Lookback period for ATR computation.',
      compression_lookback: 'Window (bars) used to measure both the ATR minimum (entry) and ATR mean (exit).',
      compression_ratio: 'Tolerance above the ATR minimum still considered "compressed". E.g. 0.5 means ATR must be ≤ 1.5 × minimum.',
    },
  },

  // ── Mean Reversion ────────────────────────────────────────────────────────

  mean_reversion_trend: {
    overview:
      'A dual-condition variant of mean reversion: requires both a strong directional trend (ADX filter) and a pullback away from the trend MA. ' +
      'The idea is to buy temporary weakness within a healthy uptrend rather than entering against a genuine reversal.',
    whenBuy:
      'Buys when ADX exceeds adx_threshold (confirming a strong trend) AND the closing price z-score relative to the MA is below −z_threshold (price has pulled back significantly).',
    whenSell:
      'Sells when the z-score rises back above zero — price has returned to its moving average.',
    valueAndCaveats:
      'Better risk/reward than pure mean reversion because the trend filter avoids buying in genuine downtrends. ' +
      'In flat markets ADX stays low, preventing entries even when price looks extended.',
    paramDescriptions: {
      ma_window: 'Period for the rolling mean and standard deviation used to compute the z-score.',
      z_threshold: 'How many standard deviations below the MA price must be to trigger entry.',
      adx_period: 'Lookback period for the ADX trend-strength indicator.',
      adx_threshold: 'Minimum ADX value required to confirm a strong trend. Typical boundary: 25.',
    },
  },

  mean_reversion_range: {
    overview:
      'Buys at the lower Bollinger Band in low-ADX (non-trending) environments. ' +
      'Bollinger Bands statistically contain 95% of price action; touching the lower band suggests the move may be over-extended.',
    whenBuy:
      'Buys when price is below the lower Bollinger Band AND ADX is below adx_max, confirming the market is range-bound rather than trending.',
    whenSell:
      'Sells when price crosses back above the Bollinger mid-band (the rolling mean).',
    valueAndCaveats:
      'The ADX filter is critical — without it, this strategy would buy into downtrends. ' +
      'In genuine trending markets ADX rises and suppresses entries, protecting against buying falling knives.',
    paramDescriptions: {
      bb_window: 'Period for Bollinger Band calculation (rolling mean and standard deviation).',
      bb_std: 'Number of standard deviations below the mean that defines the lower Bollinger Band.',
      adx_period: 'Lookback period for the ADX indicator.',
      adx_max: 'Maximum ADX value permitted. Entry is blocked when ADX exceeds this, indicating a trend.',
    },
  },

  reverting_market: {
    overview:
      'An RSI oscillator strategy that only activates in non-trending (sideways) markets. ' +
      'Uses ADX to gate entries: when the market is trending, the strategy stays flat; when it is ranging, ' +
      'it buys oversold RSI dips.',
    whenBuy:
      'Buys when RSI is below rsi_lower AND ADX is below adx_max (range-bound condition confirmed).',
    whenSell:
      'Sells when RSI rises above rsi_upper.',
    valueAndCaveats:
      'Narrow, well-defined entry conditions reduce false signals. ' +
      'The ADX gate is the key innovation over plain RSI. ' +
      'Suitable for highly liquid range-bound instruments like major currency pairs or commodity ETFs.',
    paramDescriptions: {
      rsi_period: 'Lookback period for RSI calculation.',
      rsi_upper: 'RSI level above which the position is closed. Tighter than classic overbought (typically 60).',
      rsi_lower: 'RSI level below which the entry fires. Tighter than classic oversold (typically 40).',
      adx_period: 'Lookback period for ADX.',
      adx_max: 'Maximum ADX allowed for entry. Market must be ranging (ADX below this) for signals to activate.',
    },
  },

  // ── Breakout ──────────────────────────────────────────────────────────────

  range_breakout: {
    overview:
      'A clean horizontal support/resistance breakout: buy when price eclipses the N-bar high, sell when price falls below the N-bar low. ' +
      'Does not require any volatility squeeze condition — any breakout above the lookback high qualifies.',
    whenBuy:
      'Buys on the first bar that the closing price exceeds the prior bar\'s N-period rolling high (resistance breakout).',
    whenSell:
      'Sells on the first bar that the closing price falls below the prior bar\'s N-period rolling low (support break).',
    valueAndCaveats:
      'Among the simplest and most tested breakout rules in systematic trading. ' +
      'Donchian channel-based systems have historically shown positive returns in commodities and trend-following contexts. ' +
      'False breakouts are common in low-volatility environments.',
    paramDescriptions: {
      lookback: 'Number of bars in the rolling window for computing the high and low extremes used as breakout levels.',
    },
  },

  orb: {
    overview:
      'Open Range Breakout treats the first few bars of the data series as an "opening range" (price discovery period). ' +
      'A breakout above the opening range high is treated as a bullish momentum signal for the session.',
    whenBuy:
      'Buys on the first bar that price closes above the high of the initial opening_bars period.',
    whenSell:
      'Sells on the first bar that price closes below the low of the initial opening_bars period.',
    valueAndCaveats:
      'Designed for intraday data where the opening range resets each session. ' +
      'On daily bars, the opening range is derived from the first N bars of the entire series, making the signal approximate. ' +
      'Best used with intraday (e.g. 15-min) data for accurate session-level breakout detection.',
    paramDescriptions: {
      opening_bars: 'Number of bars considered the "opening range". For 5-minute data with a 30-minute range, use 6.',
    },
  },

  // ── Seasonal ──────────────────────────────────────────────────────────────

  seasonal: {
    overview:
      'Implements the "Sell in May and go away" calendar anomaly. ' +
      'Equity markets historically underperform from May through October relative to November through April. ' +
      'The strategy holds the asset only during the statistically stronger half of the year.',
    whenBuy:
      'Buys on the first bar of the buy_month (default: November) — the start of the historically stronger seasonal period.',
    whenSell:
      'Sells on the first bar of the sell_month (default: May) — the start of the historically weaker seasonal period.',
    valueAndCaveats:
      'The seasonal effect is well-documented across many decades and equity markets globally. ' +
      'It is not guaranteed to hold every year and should not be used as a standalone strategy without additional filters. ' +
      'Tax implications of annual portfolio turnover should also be considered.',
    paramDescriptions: {
      sell_month: 'Calendar month number (1–12) on which to exit (sell). Default 5 = May.',
      buy_month: 'Calendar month number (1–12) on which to enter (buy). Default 11 = November.',
    },
  },
};
