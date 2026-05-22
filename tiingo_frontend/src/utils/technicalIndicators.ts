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

function rsiFromAverages(avgGain: number, avgLoss: number): number {
  if (avgLoss === 0) {
    return avgGain > 0 ? 100 : 50;
  }
  const rs = avgGain / avgLoss;
  return 100 - 100 / (1 + rs);
}

export function computeRSI(values: number[], period: number): (number | null)[] {
  if (period < 1 || values.length < period + 1) {
    return values.map(() => null);
  }

  const result: (number | null)[] = Array.from({ length: period }, () => null);
  const gains: number[] = [];
  const losses: number[] = [];

  for (let i = 1; i < values.length; i += 1) {
    const delta = values[i] - values[i - 1];
    gains.push(Math.max(delta, 0));
    losses.push(Math.max(-delta, 0));
  }

  let avgGain = gains.slice(0, period).reduce((acc, v) => acc + v, 0) / period;
  let avgLoss = losses.slice(0, period).reduce((acc, v) => acc + v, 0) / period;
  result.push(rsiFromAverages(avgGain, avgLoss));

  for (let i = period; i < gains.length; i += 1) {
    avgGain = (avgGain * (period - 1) + gains[i]) / period;
    avgLoss = (avgLoss * (period - 1) + losses[i]) / period;
    result.push(rsiFromAverages(avgGain, avgLoss));
  }

  return result;
}

export function computeDonchian(
  highs: number[],
  lows: number[],
  period: number,
): { upper: (number | null)[]; lower: (number | null)[] } {
  if (period < 1 || highs.length === 0) {
    const empty = highs.map(() => null);
    return { upper: empty, lower: empty };
  }

  const upper: (number | null)[] = [];
  const lower: (number | null)[] = [];
  for (let i = 0; i < highs.length; i += 1) {
    if (i < period) {
      upper.push(null);
      lower.push(null);
      continue;
    }
    const windowHighs = highs.slice(i - period, i);
    const windowLows = lows.slice(i - period, i);
    upper.push(Math.max(...windowHighs));
    lower.push(Math.min(...windowLows));
  }
  return { upper, lower };
}

export function computeBollingerBands(
  values: number[],
  period: number,
  stdDev: number,
): { middle: (number | null)[]; upper: (number | null)[]; lower: (number | null)[] } {
  const middle = computeSMA(values, period);
  const upper: (number | null)[] = [];
  const lower: (number | null)[] = [];

  for (let i = 0; i < values.length; i += 1) {
    const mid = middle[i];
    if (mid == null) {
      upper.push(null);
      lower.push(null);
      continue;
    }
    const window = values.slice(i + 1 - period, i + 1);
    const variance = window.reduce((acc, value) => acc + (value - mid) ** 2, 0) / period;
    const band = stdDev * Math.sqrt(variance);
    upper.push(mid + band);
    lower.push(mid - band);
  }
  return { middle, upper, lower };
}

export function computeStochastic(
  highs: number[],
  lows: number[],
  closes: number[],
  kPeriod: number,
  dPeriod: number,
): { k: (number | null)[]; d: (number | null)[] } {
  if (kPeriod < 1 || dPeriod < 1 || closes.length === 0) {
    const empty = closes.map(() => null);
    return { k: empty, d: empty };
  }

  const kValues: (number | null)[] = [];
  for (let i = 0; i < closes.length; i += 1) {
    if (i + 1 < kPeriod) {
      kValues.push(null);
      continue;
    }
    const windowHighs = highs.slice(i + 1 - kPeriod, i + 1);
    const windowLows = lows.slice(i + 1 - kPeriod, i + 1);
    const highest = Math.max(...windowHighs);
    const lowest = Math.min(...windowLows);
    if (highest === lowest) {
      kValues.push(50);
    } else {
      kValues.push(100 * (closes[i] - lowest) / (highest - lowest));
    }
  }

  const dValues: (number | null)[] = [];
  for (let i = 0; i < kValues.length; i += 1) {
    if (kValues[i] == null || i + 1 < dPeriod) {
      dValues.push(null);
      continue;
    }
    const window = kValues.slice(i + 1 - dPeriod, i + 1) as number[];
    dValues.push(window.reduce((acc, value) => acc + value, 0) / dPeriod);
  }
  return { k: kValues, d: dValues };
}

export function computeMFI(
  highs: number[],
  lows: number[],
  closes: number[],
  volumes: number[],
  period: number,
): (number | null)[] {
  if (period < 1 || closes.length < period + 1) {
    return closes.map(() => null);
  }

  const typicalPrices = closes.map((close, i) => (highs[i] + lows[i] + close) / 3);
  const moneyFlows = typicalPrices.map((price, i) => price * volumes[i]);
  const result: (number | null)[] = Array.from({ length: period }, () => null);

  for (let i = period; i < closes.length; i += 1) {
    let positive = 0;
    let negative = 0;
    for (let j = i - period + 1; j <= i; j += 1) {
      if (typicalPrices[j] > typicalPrices[j - 1]) {
        positive += moneyFlows[j];
      } else if (typicalPrices[j] < typicalPrices[j - 1]) {
        negative += moneyFlows[j];
      }
    }
    if (negative === 0) {
      result.push(positive > 0 ? 100 : 50);
    } else {
      const ratio = positive / negative;
      result.push(100 - 100 / (1 + ratio));
    }
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
