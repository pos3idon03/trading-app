/**
 * Align per-leg signal timelines onto a shared finest-timeframe grid for charts.
 */
import type { ComboStrategySignal, SignalPoint } from '../api/types';
import { timeframeToMs } from './executionSignals';

export interface TimelinePoint {
  time: string;
  [strategyKey: string]: number | string;
}

const TIMEFRAME_MS = {
  '1m': 60_000,
  '5m': 300_000,
  '15m': 900_000,
  '30m': 1_800_000,
  '1h': 3_600_000,
  '3h': 10_800_000,
  '4h': 14_400_000,
  '1d': 86_400_000,
  '1w': 604_800_000,
} as const;

export function finestTimeframe(timeframes: string[], fallback = '1d'): string {
  if (timeframes.length === 0) return fallback;
  return timeframes.reduce((a, b) =>
    (TIMEFRAME_MS[a as keyof typeof TIMEFRAME_MS] ?? timeframeToMs(a)) <
    (TIMEFRAME_MS[b as keyof typeof TIMEFRAME_MS] ?? timeframeToMs(b))
      ? a
      : b,
  );
}

function normalizeSignal(signal: string): 'Buy' | 'Neutral' | 'Sell' {
  const s = signal.toUpperCase();
  if (s === 'BUY') return 'Buy';
  if (s === 'NEUTRAL' || s === 'HOLD') return 'Neutral';
  return 'Sell';
}

export function signalToValue(signal: string): number {
  const norm = normalizeSignal(signal);
  if (norm === 'Buy') return 1;
  if (norm === 'Neutral') return 0.5;
  return 0;
}

function parseTimeMs(t: string): number {
  const ms = new Date(t).getTime();
  return Number.isNaN(ms) ? 0 : ms;
}

function floorToGrid(ms: number, gridMs: number): number {
  return Math.floor(ms / gridMs) * gridMs;
}

function buildGridTimes(
  strategies: ComboStrategySignal[],
  gridMs: number,
): number[] {
  let minMs = Infinity;
  let maxMs = -Infinity;
  for (const s of strategies) {
    for (const p of s.signal_timeline) {
      const t = parseTimeMs(p.time);
      if (t > 0) {
        minMs = Math.min(minMs, t);
        maxMs = Math.max(maxMs, t);
      }
    }
  }
  if (!Number.isFinite(minMs) || !Number.isFinite(maxMs)) return [];

  const start = floorToGrid(minMs, gridMs);
  const end = floorToGrid(maxMs, gridMs);
  const times: number[] = [];
  for (let t = start; t <= end; t += gridMs) {
    times.push(t);
  }
  return times;
}

function forwardFillOnGrid(
  timeline: SignalPoint[],
  gridTimes: number[],
): Map<number, number> {
  const sorted = [...timeline]
    .map((p) => ({ ms: parseTimeMs(p.time), value: signalToValue(p.signal) }))
    .filter((p) => p.ms > 0)
    .sort((a, b) => a.ms - b.ms);

  const result = new Map<number, number>();
  let idx = 0;
  let last = 0.5;

  for (const gridMs of gridTimes) {
    while (idx < sorted.length && sorted[idx].ms <= gridMs) {
      last = sorted[idx].value;
      idx += 1;
    }
    result.set(gridMs, last);
  }
  return result;
}

/** Plot native per-bar stances without re-bucketing (single-leg charts). */
export function buildRawTimelineData(strategy: ComboStrategySignal): TimelinePoint[] {
  return strategy.signal_timeline.map((p) => ({
    time: p.time,
    [strategy.strategy_name]: signalToValue(p.signal),
  }));
}

/** Merge legs onto a shared alignment grid (finest TF among legs by default). */
export function buildAlignedTimelineData(
  strategies: ComboStrategySignal[],
  alignmentTimeframe?: string,
): TimelinePoint[] {
  if (strategies.length === 0) return [];

  const alignTf = alignmentTimeframe ?? '1d';
  const gridMs = timeframeToMs(alignTf);
  const gridTimes = buildGridTimes(strategies, gridMs);
  if (gridTimes.length === 0) return [];

  const filled = strategies.map((strategy) =>
    forwardFillOnGrid(strategy.signal_timeline, gridTimes),
  );

  return gridTimes.map((ms, i) => {
    const point: TimelinePoint = { time: new Date(ms).toISOString() };
    strategies.forEach((strategy, si) => {
      point[strategy.strategy_name] = filled[si].get(ms) ?? 0.5;
    });
    return point;
  });
}
