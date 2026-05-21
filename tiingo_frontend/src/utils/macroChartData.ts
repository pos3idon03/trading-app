import type { MacroObservation } from '../api/types';
import type { TimeSeriesPoint } from './seriesData';

export interface MacroChartPoint {
  date: string;
  primary?: number | null;
  compare?: number | null;
}

export interface MacroCompareSeries {
  seriesId: string;
  title: string;
  observations: MacroObservation[];
  color: string;
}

export interface DateBounds {
  start: string;
  end: string;
}

export interface MacroCompareMeta {
  chartStart: string;
  chartEnd: string;
  overlapStart: string | null;
  overlapEnd: string | null;
  primaryCount: number;
  compareCount: number;
}

export function getObservationBounds(
  observations: MacroObservation[],
): DateBounds | null {
  if (!observations.length) return null;
  const dates = observations.map((o) => o.obs_date).sort();
  return { start: dates[0], end: dates[dates.length - 1] };
}

function clipBounds(bounds: DateBounds, filter?: { start?: string; end?: string }): DateBounds {
  let { start, end } = bounds;
  if (filter?.start && start < filter.start) start = filter.start;
  if (filter?.end && end > filter.end) end = filter.end;
  return { start, end };
}

function unionBounds(a: DateBounds, b: DateBounds): DateBounds {
  return {
    start: a.start < b.start ? a.start : b.start,
    end: a.end > b.end ? a.end : b.end,
  };
}

function intersectBounds(a: DateBounds, b: DateBounds): DateBounds | null {
  const start = a.start > b.start ? a.start : b.start;
  const end = a.end < b.end ? a.end : b.end;
  return start <= end ? { start, end } : null;
}

export function filterObservationsByRange(
  observations: MacroObservation[],
  filter?: { start?: string; end?: string },
): MacroObservation[] {
  if (!filter?.start && !filter?.end) return observations;
  return observations.filter((obs) => {
    if (filter.start && obs.obs_date < filter.start) return false;
    if (filter.end && obs.obs_date > filter.end) return false;
    return true;
  });
}

export function computeMacroCompareMeta(
  primary: MacroObservation[],
  compare?: MacroObservation[],
  filter?: { start?: string; end?: string },
): MacroCompareMeta | null {
  const primaryBounds = getObservationBounds(primary);
  if (!primaryBounds) return null;

  const compareBounds = compare?.length ? getObservationBounds(compare) : null;
  let chartBounds = primaryBounds;
  if (compareBounds) {
    chartBounds = unionBounds(primaryBounds, compareBounds);
  }
  chartBounds = clipBounds(chartBounds, filter);

  const overlap = compareBounds ? intersectBounds(primaryBounds, compareBounds) : null;
  const clippedOverlap = overlap ? clipBounds(overlap, filter) : null;

  return {
    chartStart: chartBounds.start,
    chartEnd: chartBounds.end,
    overlapStart: clippedOverlap?.start ?? null,
    overlapEnd: clippedOverlap?.end ?? null,
    primaryCount: primary.length,
    compareCount: compare?.length ?? 0,
  };
}

export function formatMacroCompareSubtitle(
  primaryId: string,
  meta: MacroCompareMeta,
  compareId?: string,
  rangeLabel?: string,
): string {
  const range = `${meta.chartStart.slice(0, 7)} → ${meta.chartEnd.slice(0, 7)}`;
  const parts = compareId
    ? `${primaryId} (${meta.primaryCount}) vs ${compareId} (${meta.compareCount}) · ${range}`
    : `${primaryId} · ${meta.primaryCount} observations · ${range}`;

  if (compareId && meta.overlapStart && meta.overlapEnd) {
    const overlap = `${meta.overlapStart.slice(0, 7)} → ${meta.overlapEnd.slice(0, 7)}`;
    return `${parts} · overlap ${overlap}${rangeLabel ? ` · ${rangeLabel}` : ''}`;
  }
  return `${parts}${rangeLabel ? ` · ${rangeLabel}` : ''}`;
}

export function mergeTimelineSeries(
  primary: TimeSeriesPoint[],
  compare?: TimeSeriesPoint[],
): MacroChartPoint[] {
  const byDate = new Map<string, MacroChartPoint>();

  for (const pt of primary) {
    byDate.set(pt.date, { date: pt.date, primary: pt.value ?? null });
  }

  if (compare) {
    for (const pt of compare) {
      const existing = byDate.get(pt.date) ?? { date: pt.date };
      existing.compare = pt.value ?? null;
      byDate.set(pt.date, existing);
    }
  }

  return [...byDate.values()].sort((a, b) => a.date.localeCompare(b.date));
}

export function mergeMacroSeries(
  primary: MacroObservation[],
  compare?: MacroObservation[],
): MacroChartPoint[] {
  const toPoint = (o: MacroObservation): TimeSeriesPoint => ({
    date: o.obs_date,
    value: o.value ?? null,
  });
  return mergeTimelineSeries(primary.map(toPoint), compare?.map(toPoint));
}
