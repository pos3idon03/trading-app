import type { MacroObservation } from '../api/types';
import type { TimeSeriesPoint } from './seriesData';

export interface AlignedMacroAssetPoint {
  date: string;
  macroValue: number;
  assetValue: number;
}

export interface PeriodChangePoint {
  date: string;
  macroChange: number;
  assetChange: number;
}

export interface PeriodChangeContext {
  point: PeriodChangePoint;
  macroPercentile: number;
  assetPercentile: number;
  macroHistory: number[];
  assetHistory: number[];
}

export interface SliderYearTick {
  year: number;
  index: number;
  percent: number;
}

export interface ScatterTooltipLines {
  period: string;
  macroLine: string;
  assetLine: string;
}

const FREQUENCY_LABELS: Record<string, string> = {
  Daily: 'daily',
  Weekly: 'weekly',
  Monthly: 'monthly',
  Quarterly: 'quarterly',
  Annual: 'annual',
};

export function resolveMacroStepLabel(frequency?: string | null): string {
  if (frequency && FREQUENCY_LABELS[frequency]) {
    return FREQUENCY_LABELS[frequency];
  }
  return 'period';
}

function medianGapDays(dates: string[]): number | null {
  if (dates.length < 2) return null;
  const gaps: number[] = [];
  for (let i = 1; i < dates.length; i += 1) {
    const prev = new Date(`${dates[i - 1]}T00:00:00Z`).getTime();
    const curr = new Date(`${dates[i]}T00:00:00Z`).getTime();
    gaps.push(Math.round((curr - prev) / 86_400_000));
  }
  gaps.sort((a, b) => a - b);
  const mid = Math.floor(gaps.length / 2);
  return gaps.length % 2 === 0 ? (gaps[mid - 1] + gaps[mid]) / 2 : gaps[mid];
}

export function resolveMacroStep(
  frequency?: string | null,
  observations?: MacroObservation[],
): string {
  if (frequency && FREQUENCY_LABELS[frequency]) {
    return FREQUENCY_LABELS[frequency];
  }
  const dates = observations?.map((o) => o.obs_date) ?? [];
  const gap = medianGapDays(dates);
  if (gap == null) return 'period';
  if (gap <= 2) return 'daily';
  if (gap <= 10) return 'weekly';
  if (gap <= 45) return 'monthly';
  if (gap <= 120) return 'quarterly';
  return 'annual';
}

function isFiniteValue(value: number | null | undefined): value is number {
  return value != null && Number.isFinite(value);
}

export function alignAssetToMacroDates(
  macroObs: MacroObservation[],
  assetPoints: TimeSeriesPoint[],
): AlignedMacroAssetPoint[] {
  const sortedAsset = [...assetPoints]
    .filter((p) => isFiniteValue(p.value))
    .sort((a, b) => a.date.localeCompare(b.date));

  if (!sortedAsset.length) return [];

  const aligned: AlignedMacroAssetPoint[] = [];
  let assetIdx = 0;
  let lastAssetValue: number | null = null;

  for (const obs of macroObs) {
    if (!isFiniteValue(obs.value)) continue;

    while (assetIdx < sortedAsset.length && sortedAsset[assetIdx].date <= obs.obs_date) {
      lastAssetValue = sortedAsset[assetIdx].value;
      assetIdx += 1;
    }

    if (lastAssetValue == null) continue;
    aligned.push({
      date: obs.obs_date,
      macroValue: obs.value,
      assetValue: lastAssetValue,
    });
  }

  return aligned;
}

function pctChange(current: number, prior: number): number | null {
  if (prior === 0) return null;
  return ((current - prior) / prior) * 100;
}

export function buildPeriodChangeSeries(
  aligned: AlignedMacroAssetPoint[],
): PeriodChangePoint[] {
  const changes: PeriodChangePoint[] = [];

  for (let i = 1; i < aligned.length; i += 1) {
    const prev = aligned[i - 1];
    const curr = aligned[i];
    const macroChange = pctChange(curr.macroValue, prev.macroValue);
    const assetChange = pctChange(curr.assetValue, prev.assetValue);
    if (macroChange == null || assetChange == null) continue;
    changes.push({
      date: curr.date,
      macroChange,
      assetChange,
    });
  }

  return changes;
}

export function computePercentileRank(value: number, history: number[]): number {
  if (history.length === 0) return 50;
  const sorted = [...history].sort((a, b) => a - b);
  let below = 0;
  for (const item of sorted) {
    if (item < value) below += 1;
  }
  return Math.round((below / sorted.length) * 100);
}

export function getSliderSteps(changeSeries: PeriodChangePoint[]): number {
  return Math.max(0, changeSeries.length);
}

export function buildPeriodChangeContext(
  changeSeries: PeriodChangePoint[],
  selectedIndex: number,
): PeriodChangeContext | null {
  if (changeSeries.length === 0 || selectedIndex < 0 || selectedIndex >= changeSeries.length) {
    return null;
  }

  const macroHistory = changeSeries.map((p) => p.macroChange);
  const assetHistory = changeSeries.map((p) => p.assetChange);
  const point = changeSeries[selectedIndex];

  return {
    point,
    macroHistory,
    assetHistory,
    macroPercentile: computePercentileRank(point.macroChange, macroHistory),
    assetPercentile: computePercentileRank(point.assetChange, assetHistory),
  };
}

function subsampleYearTicks(ticks: SliderYearTick[], maxLabels: number): SliderYearTick[] {
  if (ticks.length <= maxLabels) return ticks;

  const step = Math.ceil((ticks.length - 1) / (maxLabels - 1));
  const picked: SliderYearTick[] = [];

  for (let i = 0; i < ticks.length && picked.length < maxLabels - 1; i += step) {
    picked.push(ticks[i]);
  }
  picked.push(ticks[ticks.length - 1]);

  const seen = new Set<number>();
  return picked
    .filter((t) => {
      if (seen.has(t.year)) return false;
      seen.add(t.year);
      return true;
    })
    .slice(0, maxLabels);
}

export function buildSliderYearTicks(changeSeries: PeriodChangePoint[]): SliderYearTick[] {
  if (changeSeries.length === 0) return [];
  if (changeSeries.length === 1) {
    const year = Number.parseInt(changeSeries[0].date.slice(0, 4), 10);
    return [{ year, index: 0, percent: 0 }];
  }

  const maxIndex = changeSeries.length - 1;
  const byYear = new Map<number, number>();

  changeSeries.forEach((point, index) => {
    const year = Number.parseInt(point.date.slice(0, 4), 10);
    if (!byYear.has(year)) byYear.set(year, index);
  });

  const ticks: SliderYearTick[] = [...byYear.entries()]
    .sort(([a], [b]) => a - b)
    .map(([year, index]) => ({
      year,
      index,
      percent: (index / maxIndex) * 100,
    }));

  return subsampleYearTicks(ticks, 20);
}

function formatPct(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

export function formatScatterTooltipLines(
  point: PeriodChangePoint,
  macroId: string,
  assetId: string,
): ScatterTooltipLines {
  return {
    period: point.date,
    macroLine: `${macroId} Δ%: ${formatPct(point.macroChange)}`,
    assetLine: `${assetId} Δ%: ${formatPct(point.assetChange)}`,
  };
}
