import type { FoundationModelCatalogItem } from '../api/foundationBacktestTypes';

export const SIGNAL_MODE_OPTIONS = [
  { value: 'next_point', label: 'Next point' },
  { value: 'horizon_mean', label: 'Horizon mean' },
] as const;

export const TARGET_SERIES_OPTIONS = [
  { value: 'close', label: 'Close' },
  { value: 'adj_close', label: 'Adjusted close' },
  { value: 'log_return', label: 'Log return' },
] as const;

export function mergeFoundationParams(
  catalogItem: FoundationModelCatalogItem | undefined,
  overrides: Record<string, unknown>,
): Record<string, unknown> {
  return {
    ...(catalogItem?.params ?? {}),
    ...overrides,
  };
}

export function scalarFoundationParams(params: Record<string, unknown>): Record<string, number> {
  const result: Record<string, number> = {};
  for (const [key, value] of Object.entries(params)) {
    if (typeof value === 'number') {
      result[key] = value;
    }
  }
  return result;
}

export function clampParam(
  key: string,
  value: number,
  constraints: Record<string, { min: number; max: number }>,
): number {
  const bounds = constraints[key];
  if (!bounds) {
    return value;
  }
  return Math.min(bounds.max, Math.max(bounds.min, value));
}

export function formatForecastPct(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return '—';
  }
  return `${(value * 100).toFixed(1)}%`;
}
