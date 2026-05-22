import type { MacroObservation } from '../api/types';

export type TrendType = 'sma' | 'ema';

export interface TrendOverlayConfig {
  id: string;
  type: TrendType;
  period: number;
}

export interface StandaloneChartPoint {
  date: string;
  primary?: number | null;
  [key: string]: string | number | null | undefined;
}

export const TREND_COLORS = ['#60a5fa', '#f472b6', '#fbbf24'] as const;
export const MAX_TREND_OVERLAYS = 3;

export function computeSMA(values: number[], period: number): (number | null)[] {
  if (period < 1 || values.length === 0) return values.map(() => null);

  const result: (number | null)[] = [];
  for (let i = 0; i < values.length; i += 1) {
    if (i + 1 < period) {
      result.push(null);
      continue;
    }
    const window = values.slice(i + 1 - period, i + 1);
    const sum = window.reduce((acc, v) => acc + v, 0);
    result.push(sum / period);
  }
  return result;
}

export function computeEMA(values: number[], period: number): (number | null)[] {
  if (period < 1 || values.length === 0) return values.map(() => null);

  const multiplier = 2 / (period + 1);
  const result: (number | null)[] = [];
  let ema: number | null = null;

  for (let i = 0; i < values.length; i += 1) {
    if (i + 1 < period) {
      result.push(null);
      continue;
    }
    if (ema === null) {
      const seed = values.slice(0, period);
      ema = seed.reduce((acc, v) => acc + v, 0) / period;
      result.push(ema);
      continue;
    }
    ema = (values[i] - ema) * multiplier + ema;
    result.push(ema);
  }
  return result;
}

export function trendSeriesKey(type: TrendType, period: number): string {
  return `${type}_${period}`;
}

export function trendSeriesLabel(type: TrendType, period: number): string {
  return type === 'sma' ? `MA ${period}` : `EMA ${period}`;
}

function extractFiniteValues(observations: MacroObservation[]): number[] {
  return observations
    .map((o) => o.value)
    .filter((v): v is number => v != null && Number.isFinite(v));
}

export function buildStandaloneChartData(
  observations: MacroObservation[],
  overlays: TrendOverlayConfig[],
): StandaloneChartPoint[] {
  const values = observations.map((o) =>
    o.value != null && Number.isFinite(o.value) ? o.value : null,
  );
  const finiteValues = values.filter((v): v is number => v != null);

  const overlaySeries = overlays.map((overlay) => {
    const computed =
      overlay.type === 'sma'
        ? computeSMA(finiteValues, overlay.period)
        : computeEMA(finiteValues, overlay.period);

    let finiteIdx = 0;
    const aligned: (number | null)[] = values.map((v) => {
      if (v == null) return null;
      const next = computed[finiteIdx] ?? null;
      finiteIdx += 1;
      return next;
    });
    return { key: trendSeriesKey(overlay.type, overlay.period), values: aligned };
  });

  return observations.map((obs, i) => {
    const point: StandaloneChartPoint = {
      date: obs.obs_date,
      primary: values[i],
    };
    for (const series of overlaySeries) {
      point[series.key] = series.values[i];
    }
    return point;
  });
}
