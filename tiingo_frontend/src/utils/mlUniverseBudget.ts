import type { DateRangeValue } from '../constants/timeframes';
import {
  estimateWalkForwardFoldCount,
  minimumBarsRequired,
  resolveWarmupBars,
  WALK_FORWARD_CONSTRAINTS,
  type WalkForwardParamKey,
  type WalkForwardParams,
} from './mlBacktestConfig';

export interface WalkForwardBudget {
  barCount: number;
  warmupBars: number;
  labelTail: number;
  minimumRequired: number;
  walkForwardBudget: number;
  remainingBars: number;
  structuralFolds: number;
  simulationStartBarIndex: number;
}

function clampParamMax(key: WalkForwardParamKey, rawMax: number): number {
  const { min, max } = WALK_FORWARD_CONSTRAINTS[key];
  return Math.max(min, Math.min(max, rawMax));
}

export function maxWalkForwardParamValue(
  key: WalkForwardParamKey,
  barCount: number,
  params: WalkForwardParams,
): number {
  if (barCount <= 0) {
    return WALK_FORWARD_CONSTRAINTS[key].min;
  }

  if (key === 'step_bars') {
    const rawStepMax = barCount - params.train_bars - params.test_bars;
    return clampParamMax(key, rawStepMax);
  }

  const fixedOther =
    resolveWarmupBars(params) +
    (key === 'train_bars' ? 0 : params.train_bars) +
    (key === 'test_bars' ? 0 : params.test_bars) +
    (key === 'label_horizon' ? 0 : params.label_horizon);

  const rawMax = barCount - fixedOther;
  return clampParamMax(key, rawMax);
}

export function computeWalkForwardBudget(
  barCount: number,
  params: WalkForwardParams,
): WalkForwardBudget {
  const warmupBars = resolveWarmupBars(params);
  const minimumRequired = minimumBarsRequired(params);
  const walkForwardBudget = Math.max(0, barCount - warmupBars - params.label_horizon);
  const remainingBars = barCount - minimumRequired;

  return {
    barCount,
    warmupBars,
    labelTail: params.label_horizon,
    minimumRequired,
    walkForwardBudget,
    remainingBars,
    structuralFolds: estimateWalkForwardFoldCount(
      barCount,
      params.train_bars,
      params.test_bars,
      params.step_bars,
    ),
    simulationStartBarIndex: params.train_bars,
  };
}

function formatBarTimestamp(value: string): string {
  return value.slice(0, 10);
}

export function formatMlDateRangeLabel(
  dateRange: DateRangeValue,
  actualStart?: string | null,
  actualEnd?: string | null,
): string {
  if (actualStart || actualEnd) {
    const start = actualStart ? formatBarTimestamp(actualStart) : '—';
    const end = actualEnd ? formatBarTimestamp(actualEnd) : '—';
    return `${start} → ${end}`;
  }

  if (dateRange.preset === 'MAX' && !dateRange.start && !dateRange.end) {
    return 'MAX (full ingested history)';
  }

  const start = dateRange.start ? formatBarTimestamp(dateRange.start) : '—';
  const end = dateRange.end ? formatBarTimestamp(dateRange.end) : 'today';
  return `${start} → ${end}`;
}

export function isUsingMaxPreset(dateRange: DateRangeValue): boolean {
  return dateRange.preset === 'MAX' && !dateRange.start && !dateRange.end;
}
