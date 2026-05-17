export interface MetricTier {
  tierIndex: number;
  label: string;
  barClass: string;
}

const SHARPE_CAP = 3.5;
const PROFIT_FACTOR_CAP = 3.5;

function clamp01(n: number): number {
  return Math.min(1, Math.max(0, n));
}

function isFiniteNumber(v: number | null | undefined): v is number {
  return v !== null && v !== undefined && Number.isFinite(v);
}

export function getSharpeTier(value: number | null | undefined): MetricTier | null {
  if (!isFiniteNumber(value)) return null;
  if (value < 1.0) {
    return { tierIndex: 0, label: 'Suboptimal', barClass: 'bg-red-500' };
  }
  if (value < 2.0) {
    return { tierIndex: 1, label: 'Good', barClass: 'bg-amber-500' };
  }
  if (value < 3.0) {
    return { tierIndex: 2, label: 'Very Good', barClass: 'bg-emerald-500' };
  }
  return { tierIndex: 3, label: 'Excellent', barClass: 'bg-cyan-500' };
}

export function getProfitFactorTier(value: number | null | undefined): MetricTier | null {
  if (!isFiniteNumber(value)) return null;
  if (value < 1.0) {
    return { tierIndex: 0, label: 'Losing', barClass: 'bg-red-500' };
  }
  if (value < 1.5) {
    return { tierIndex: 1, label: 'Moderate', barClass: 'bg-amber-500' };
  }
  if (value < 2.5) {
    return { tierIndex: 2, label: 'Strong', barClass: 'bg-emerald-500' };
  }
  return { tierIndex: 3, label: 'Exceptional', barClass: 'bg-cyan-500' };
}

/** Bar width 0–1; capped at SHARPE_CAP so excellent values nearly fill the track. */
export function normalizeSharpeFill(value: number | null | undefined): number | null {
  if (!isFiniteNumber(value)) return null;
  return clamp01(value / SHARPE_CAP);
}

/** Bar width 0–1; capped at PROFIT_FACTOR_CAP. */
export function normalizeProfitFactorFill(value: number | null | undefined): number | null {
  if (!isFiniteNumber(value)) return null;
  return clamp01(value / PROFIT_FACTOR_CAP);
}

export function getSortinoTier(value: number | null | undefined): MetricTier | null {
  return getSharpeTier(value);
}

export function normalizeSortinoFill(value: number | null | undefined): number | null {
  return normalizeSharpeFill(value);
}

export function getMetricTier(
  kind: 'sharpe' | 'sortino' | 'profit_factor',
  value: number | null | undefined,
): MetricTier | null {
  if (kind === 'profit_factor') return getProfitFactorTier(value);
  if (kind === 'sortino') return getSortinoTier(value);
  return getSharpeTier(value);
}

export function getMetricFill(
  kind: 'sharpe' | 'sortino' | 'profit_factor',
  value: number | null | undefined,
): number | null {
  if (kind === 'profit_factor') return normalizeProfitFactorFill(value);
  if (kind === 'sortino') return normalizeSortinoFill(value);
  return normalizeSharpeFill(value);
}
