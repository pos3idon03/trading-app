import type { DateRangeValue } from '../constants/timeframes';
import { toApiRange } from '../constants/timeframes';

export type EffectiveCoverage = {
  min_time: string;
  max_time: string;
  bar_count: number;
  source: string | null;
  derived_from: string | null;
};

export type OhlcvCoverageResponse = {
  timeframe: string;
  native: Array<Record<string, unknown>>;
  effective: EffectiveCoverage | null;
};

export function parseEffectiveCoverage(data: unknown): OhlcvCoverageResponse | null {
  if (!data || typeof data !== 'object') return null;
  const record = data as Record<string, unknown>;
  const effective = record.effective;
  if (!effective || typeof effective !== 'object') {
    return {
      timeframe: String(record.timeframe ?? ''),
      native: Array.isArray(record.native) ? record.native : [],
      effective: null,
    };
  }
  const eff = effective as Record<string, unknown>;
  return {
    timeframe: String(record.timeframe ?? ''),
    native: Array.isArray(record.native) ? record.native : [],
    effective: {
      min_time: String(eff.min_time ?? ''),
      max_time: String(eff.max_time ?? ''),
      bar_count: Number(eff.bar_count ?? 0),
      source: eff.source != null ? String(eff.source) : null,
      derived_from: eff.derived_from != null ? String(eff.derived_from) : null,
    },
  };
}

export function requestedRangeStart(dateRange: DateRangeValue): string | null {
  const range = toApiRange(dateRange);
  return range.start ?? null;
}

export type CoverageWarning = {
  timeframe: string;
  message: string;
};

export function buildCoverageWarnings(
  coverages: Record<string, OhlcvCoverageResponse | null>,
  dateRange: DateRangeValue,
  requirements: Record<string, number>,
): CoverageWarning[] {
  const rangeStart = requestedRangeStart(dateRange);
  const warnings: CoverageWarning[] = [];

  for (const [timeframe, requiredBars] of Object.entries(requirements)) {
    const coverage = coverages[timeframe];
    const effective = coverage?.effective;
    if (!effective) {
      warnings.push({
        timeframe,
        message: `No ${timeframe} data ingested. Run OHLCV backfill (1h) or narrow the date range.`,
      });
      continue;
    }

    if (rangeStart && effective.min_time && rangeStart < effective.min_time) {
      warnings.push({
        timeframe,
        message: `${timeframe} data starts ${formatCoverageTime(effective.min_time)}; your range begins earlier. Narrow the range or backfill.`,
      });
    }

    if (effective.bar_count < requiredBars) {
      warnings.push({
        timeframe,
        message: `${timeframe} has ~${effective.bar_count} bars; strategies need at least ${requiredBars}. Lower periods or use a coarser signal timeframe (e.g. 1d).`,
      });
    }
  }

  return warnings;
}

function formatCoverageTime(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toISOString().slice(0, 10);
}

export function warmupRequirementBars(
  strategyId: string,
  params: Record<string, number>,
): number {
  if (strategyId === 'ema_crossover' || strategyId === 'sma_crossover') {
    return Math.max(27, params.slow_period ?? 26);
  }
  if (strategyId === 'rsi_reversion' || strategyId === 'mfi_reversion') {
    return Math.max(16, params.period ?? 14);
  }
  if (strategyId === 'donchian_breakout') {
    return Math.max(21, params.channel_period ?? 20);
  }
  if (strategyId === 'bollinger_breakout') {
    return Math.max(21, params.period ?? 20);
  }
  if (strategyId === 'ts_momentum') {
    return Math.max(64, params.lookback ?? 63);
  }
  return 20;
}
