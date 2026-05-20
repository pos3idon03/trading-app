import type { McBacktestOptimizeResponse, McBacktestPreset, McModelType } from '../api/types';
import { MC_MAX_PARAM_COMBOS } from '../constants/monteCarlo';
import { defaultCalibrationDaysForTimeframe, isIntradayTimeframe } from './backtestDates';

function normalizeThreshold(value: number): number {
  return value > 1 ? value / 100 : value;
}

function cartesianGrid(grid: Record<string, number[]>): Record<string, number>[] {
  const keys = Object.keys(grid);
  if (keys.length === 0) return [];
  let combos: Record<string, number>[] = [{}];
  for (const key of keys) {
    const values = grid[key];
    if (!values?.length) continue;
    const next: Record<string, number>[] = [];
    for (const combo of combos) {
      for (const v of values) {
        next.push({ ...combo, [key]: v });
      }
    }
    combos = next;
  }
  return combos;
}

/** Count param combos that satisfy sell < buy (matches backend filter). */
export function countValidBacktestCombos(grid: Record<string, number[]>): number {
  return cartesianGrid(grid).filter((combo) => {
    const buy = normalizeThreshold(combo.buy_threshold ?? 65);
    const sell = normalizeThreshold(combo.sell_threshold ?? 40);
    return sell < buy;
  }).length;
}

export function isBacktestGridOverLimit(grid: Record<string, number[]>): boolean {
  return countValidBacktestCombos(grid) > MC_MAX_PARAM_COMBOS;
}

function thresholdToPct(value: number): string {
  const pct = value <= 1 ? value * 100 : value;
  return String(Math.round(pct));
}

export function buildBacktestPreset(
  result: McBacktestOptimizeResponse,
  form: {
    symbol: string;
    modelType: McModelType;
    timeframe: McBacktestPreset['timeframe'];
    startDate: string;
    endDate: string;
    calibrationDays?: number;
  },
): McBacktestPreset | null {
  const p = result.best_params;
  if (!p) return null;
  const intraday = isIntradayTimeframe(form.timeframe);
  return {
    symbol: form.symbol,
    modelType: form.modelType,
    timeframe: form.timeframe,
    startDate: form.startDate,
    endDate: form.endDate,
    calibrationYears: p.calibration_years ?? 10,
    calibrationDays: intraday
      ? (p.calibration_days ?? form.calibrationDays ?? defaultCalibrationDaysForTimeframe(form.timeframe))
      : undefined,
    numPaths: p.num_paths ?? 500,
    buyPct: thresholdToPct(p.buy_threshold ?? 0.65),
    sellPct: thresholdToPct(p.sell_threshold ?? 0.4),
    probSmoothingBars: p.prob_smoothing_bars ?? 0,
    entryConfirmationBars: p.entry_confirmation_bars ?? 1,
    minHoldBars: p.min_hold_bars ?? 0,
    cooldownBars: p.cooldown_bars ?? 0,
    ouMaWindow: p.ou_ma_window ?? 20,
    adxPeriod: p.adx_period ?? 14,
    adxTrendThreshold: p.adx_trend_threshold ?? 25,
  };
}

export function formatThresholdParam(key: string, value: number): string {
  if (key.includes('threshold')) {
    return `${thresholdToPct(value)}%`;
  }
  return String(value);
}
