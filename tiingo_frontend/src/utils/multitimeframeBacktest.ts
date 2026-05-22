import type { BacktestResultsResponse } from '../api/backtestTypes';
import type { DateRangeValue } from '../constants/timeframes';
import { ENSEMBLE_STRATEGY_ID, parseEnsembleLegs } from './ensembleConfig';

export function effectiveSignalTimeframe(
  legSignalTimeframe: string | undefined,
  decisionTimeframe: string,
): string {
  return legSignalTimeframe || decisionTimeframe;
}

export function collectResultSignalTimeframes(
  results: BacktestResultsResponse,
  standaloneSignalTimeframe: string,
  decisionTimeframe: string,
): string[] {
  const timeframes = new Set<string>([decisionTimeframe]);

  if (results.strategy === ENSEMBLE_STRATEGY_ID) {
    for (const leg of parseEnsembleLegs(results.params)) {
      timeframes.add(effectiveSignalTimeframe(leg.signal_timeframe, decisionTimeframe));
    }
    return [...timeframes];
  }

  timeframes.add(effectiveSignalTimeframe(standaloneSignalTimeframe, decisionTimeframe));
  return [...timeframes];
}

export function chartDateRange(
  results: BacktestResultsResponse | null,
  dateRange: DateRangeValue,
): DateRangeValue {
  if (!results?.start_date && !results?.end_date) {
    return dateRange;
  }
  return {
    preset: 'MAX',
    start: results.start_date ?? dateRange.start,
    end: results.end_date ?? dateRange.end,
  };
}

export function apiRangeFromOhlcvQuery(query: { start?: string; end?: string }) {
  return {
    start: query.start,
    end: query.end,
  };
}
