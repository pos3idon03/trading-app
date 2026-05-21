import { ingestionApi, marketDataApi } from '../api/endpoints';
import type {
  DashboardSeriesRef,
  Instrument,
  MacroObservation,
  MacroSeries,
  OHLCVBar,
} from '../api/types';
import {
  type DateRangeValue,
  buildOhlcvQuery,
  toApiRange,
} from '../constants/timeframes';

export interface TimeSeriesPoint {
  date: string;
  value: number | null;
}

export function macroToRef(series: MacroSeries): DashboardSeriesRef {
  return {
    source: 'macro',
    id: series.series_id,
    label: series.title,
  };
}

export function instrumentToRef(instrument: Instrument): DashboardSeriesRef {
  return {
    source: 'instrument',
    id: instrument.symbol.toUpperCase(),
    label: instrument.name ?? instrument.symbol,
    assetType: instrument.asset_type,
  };
}

export function observationsToPoints(observations: MacroObservation[]): TimeSeriesPoint[] {
  return observations.map((o) => ({ date: o.obs_date, value: o.value ?? null }));
}

export function ohlcvToPoints(records: OHLCVBar[]): TimeSeriesPoint[] {
  const sorted = [...records].sort((a, b) => a.time.localeCompare(b.time));
  return sorted.map((r) => ({
    date: new Date(r.time).toISOString().slice(0, 10),
    value: r.close,
  }));
}

export function pointsToObservations(points: TimeSeriesPoint[]): MacroObservation[] {
  return points.map((p) => ({ obs_date: p.date, value: p.value }));
}

function buildMacroObsParams(dateRange: DateRangeValue) {
  const rangeParams = toApiRange(dateRange);
  const isMaxRange = dateRange.preset === 'MAX' && !rangeParams.start && !rangeParams.end;
  return isMaxRange
    ? { all: true, order: 'asc' as const }
    : { limit: 5000, order: 'asc' as const, ...rangeParams };
}

export async function fetchSeriesObservations(
  ref: DashboardSeriesRef,
  dateRange: DateRangeValue,
): Promise<TimeSeriesPoint[]> {
  if (ref.source === 'macro') {
    const data = await ingestionApi.macroObservations(ref.id, buildMacroObsParams(dateRange));
    return observationsToPoints(data.observations);
  }

  const query = buildOhlcvQuery('1d', dateRange);
  const data = await marketDataApi.getOhlcv(ref.id, query);
  return ohlcvToPoints(data.records);
}

export function formatSeriesLabel(ref: DashboardSeriesRef): string {
  if (ref.source === 'macro') {
    return `${ref.id} — ${ref.label}`;
  }
  const badge = ref.assetType ? ` (${ref.assetType})` : '';
  return `${ref.id} — ${ref.label}${badge}`;
}
