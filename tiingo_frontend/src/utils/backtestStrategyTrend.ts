import type { OHLCVBar } from '../api/types';
import { isDailyPlusTimeframe } from '../constants/timeframes';
import {
  computeBollingerBands,
  computeDonchian,
  computeEMA,
  computeMFI,
  computeRSI,
  computeSMA,
  computeStochastic,
} from './technicalIndicators';
import { ensembleResultsTitle, parseEnsembleLegs } from './ensembleConfig';

export { ensembleResultsTitle, parseEnsembleLegs };

export type StrategyTrendChartMode = 'rsi' | 'ma' | 'channel' | 'bands' | 'momentum';

export type StrategyTrendPoint = {
  date: string;
  close?: number | null;
  rsi?: number | null;
  fast?: number | null;
  slow?: number | null;
  upper?: number | null;
  lower?: number | null;
  middle?: number | null;
  momentum?: number | null;
  oversold?: number;
  overbought?: number;
};

export function toChartDate(time: string, timeframe = '1d'): string {
  const parsed = new Date(time);
  if (isDailyPlusTimeframe(timeframe)) {
    return parsed.toISOString().slice(0, 10);
  }
  return parsed.toISOString().replace('.000Z', 'Z');
}

function sortedRecords(records: OHLCVBar[]): OHLCVBar[] {
  return [...records].sort((a, b) => a.time.localeCompare(b.time));
}

export function strategyTrendChartMode(strategyId: string): StrategyTrendChartMode | null {
  if (strategyId === 'rsi_reversion') return 'rsi';
  if (strategyId === 'stochastic_reversion' || strategyId === 'mfi_reversion') return 'rsi';
  if (strategyId === 'sma_crossover' || strategyId === 'ema_crossover') return 'ma';
  if (strategyId === 'donchian_breakout') return 'channel';
  if (strategyId === 'bollinger_breakout') return 'bands';
  if (strategyId === 'ts_momentum') return 'momentum';
  return null;
}

export function strategyTrendChartSubtitle(
  records: OHLCVBar[],
  signalTimeframe: string,
  strategyId?: string,
  params?: Record<string, number>,
): string | null {
  if (records.length === 0) return null;
  const bars = sortedRecords(records);
  const first = toChartDate(bars[0].time, signalTimeframe);
  const last = toChartDate(bars[bars.length - 1].time, signalTimeframe);
  let suffix = '';
  if (strategyId && params && strategyTrendChartMode(strategyId) === 'ma') {
    const slowPeriod = params.slow_period ?? 50;
    const mode = strategyId === 'ema_crossover' ? 'EMA' : 'SMA';
    suffix = ` · ${mode} warmup: first ${slowPeriod} bars`;
  }
  return `${bars.length} bars · ${first} – ${last}${suffix}`;
}

export function strategyTrendTitle(strategyId: string, params: Record<string, number>): string {
  if (strategyId === 'rsi_reversion') {
    return `RSI (${params.period ?? 14})`;
  }
  if (strategyId === 'stochastic_reversion') {
    return `Stochastic %K (${params.k_period ?? 14})`;
  }
  if (strategyId === 'mfi_reversion') {
    return `MFI (${params.period ?? 14})`;
  }
  if (strategyId === 'sma_crossover') {
    return `SMA ${params.fast_period ?? 20} / ${params.slow_period ?? 50}`;
  }
  if (strategyId === 'ema_crossover') {
    return `EMA ${params.fast_period ?? 12} / ${params.slow_period ?? 26}`;
  }
  if (strategyId === 'donchian_breakout') {
    return `Donchian (${params.channel_period ?? 20})`;
  }
  if (strategyId === 'bollinger_breakout') {
    return `Bollinger ${params.period ?? 20} / ${params.std_dev ?? 2}`;
  }
  if (strategyId === 'ts_momentum') {
    return `Momentum (${params.lookback ?? 63})`;
  }
  return 'Strategy trend';
}

export function boundedSeriesLabel(strategyId: string, params: Record<string, number>): string {
  if (strategyId === 'stochastic_reversion') {
    return `%K ${params.k_period ?? 14}`;
  }
  if (strategyId === 'mfi_reversion') {
    return `MFI ${params.period ?? 14}`;
  }
  return rsiSeriesLabel(params);
}

export function buildStrategyTrendChartData(
  strategyId: string,
  params: Record<string, number>,
  records: OHLCVBar[],
  signalTimeframe = '1d',
): StrategyTrendPoint[] | null {
  const mode = strategyTrendChartMode(strategyId);
  if (!mode || records.length === 0) {
    return null;
  }

  const bars = sortedRecords(records);
  const dates = bars.map((bar) => toChartDate(bar.time, signalTimeframe));
  const closes = bars.map((bar) => bar.close);
  const highs = bars.map((bar) => bar.high);
  const lows = bars.map((bar) => bar.low);
  const volumes = bars.map((bar) => bar.volume ?? 0);

  if (mode === 'rsi') {
    const oversold = params.oversold ?? (strategyId === 'rsi_reversion' ? 30 : 20);
    const overbought = params.overbought ?? (strategyId === 'rsi_reversion' ? 70 : 80);
    const series =
      strategyId === 'stochastic_reversion'
        ? computeStochastic(
            highs,
            lows,
            closes,
            params.k_period ?? 14,
            params.d_period ?? 3,
          ).k
        : strategyId === 'mfi_reversion'
          ? computeMFI(highs, lows, closes, volumes, params.period ?? 14)
          : computeRSI(closes, params.period ?? 14);

    return dates.map((date, index) => ({
      date,
      rsi: series[index],
      oversold,
      overbought,
    }));
  }

  if (mode === 'channel') {
    const { upper, lower } = computeDonchian(highs, lows, params.channel_period ?? 20);
    return dates.map((date, index) => ({
      date,
      close: closes[index],
      upper: upper[index],
      lower: lower[index],
    }));
  }

  if (mode === 'bands') {
    const { middle, upper, lower } = computeBollingerBands(
      closes,
      params.period ?? 20,
      params.std_dev ?? 2,
    );
    return dates.map((date, index) => ({
      date,
      close: closes[index],
      middle: middle[index],
      upper: upper[index],
      lower: lower[index],
    }));
  }

  if (mode === 'momentum') {
    const lookback = params.lookback ?? 63;
    return dates.map((date, index) => {
      if (index < lookback || closes[index - lookback] === 0) {
        return { date, momentum: null };
      }
      const momentum = ((closes[index] / closes[index - lookback]) - 1) * 100;
      return { date, momentum };
    });
  }

  const fastPeriod = params.fast_period ?? 20;
  const slowPeriod = params.slow_period ?? 50;
  const compute = strategyId === 'ema_crossover' ? computeEMA : computeSMA;
  const fast = compute(closes, fastPeriod);
  const slow = compute(closes, slowPeriod);

  return dates.map((date, index) => ({
    date,
    close: closes[index],
    fast: fast[index],
    slow: slow[index],
  }));
}

export function maSeriesLabels(
  strategyId: string,
  params: Record<string, number>,
): { close: string; fast: string; slow: string } {
  const prefix = strategyId === 'ema_crossover' ? 'EMA' : 'SMA';
  return {
    close: 'Close',
    fast: `${prefix} ${params.fast_period ?? 20}`,
    slow: `${prefix} ${params.slow_period ?? 50}`,
  };
}

export function rsiSeriesLabel(params: Record<string, number>): string {
  return `RSI ${params.period ?? 14}`;
}

export function channelSeriesLabels(params: Record<string, number>): {
  close: string;
  upper: string;
  lower: string;
} {
  return {
    close: 'Close',
    upper: `Upper (${params.channel_period ?? 20})`,
    lower: `Lower (${params.channel_period ?? 20})`,
  };
}

export function bandsSeriesLabels(params: Record<string, number>): {
  close: string;
  middle: string;
  upper: string;
  lower: string;
} {
  return {
    close: 'Close',
    middle: `Middle (${params.period ?? 20})`,
    upper: `Upper (${params.std_dev ?? 2}σ)`,
    lower: `Lower (${params.std_dev ?? 2}σ)`,
  };
}

export function momentumSeriesLabel(params: Record<string, number>): string {
  return `Return ${params.lookback ?? 63} bars (%)`;
}
