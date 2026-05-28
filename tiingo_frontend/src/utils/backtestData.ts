import type { BacktestEquityPoint, BacktestMetrics, BacktestTrade } from '../api/backtestTypes';

export type MetricTone = 'good' | 'neutral' | 'bad' | 'unknown';

/** Backend sentinel when gross profit exists but there are no losing trades. */
export const PROFIT_FACTOR_NO_LOSSES = 999;

export function formatBacktestPct(value?: number | null): string {
  if (value == null || Number.isNaN(value)) return '—';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

export function formatBacktestCurrency(value?: number | null): string {
  if (value == null || Number.isNaN(value)) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatBacktestRatio(value?: number | null): string {
  if (value == null || Number.isNaN(value)) return '—';
  return value.toFixed(2);
}

export function formatBacktestDrawdown(value?: number | null): string {
  if (value == null || Number.isNaN(value)) return '—';
  if (value === 0) return '0.00%';
  return `−${Math.abs(value).toFixed(2)}%`;
}

export function formatBacktestProfitFactor(value?: number | null): string {
  if (value == null || Number.isNaN(value)) return '—';
  if (value >= PROFIT_FACTOR_NO_LOSSES) return '∞';
  return value.toFixed(2);
}

export function isProfitFactorNoLosses(value?: number | null): boolean {
  return value != null && !Number.isNaN(value) && value >= PROFIT_FACTOR_NO_LOSSES;
}

export function metricCardClass(value?: number | null): string {
  if (value == null) return 'border-slate-800 bg-surface-900 text-slate-300';
  if (value > 0) return 'border-emerald-900/50 bg-emerald-950/30 text-emerald-300';
  if (value < 0) return 'border-red-900/50 bg-red-950/30 text-red-300';
  return 'border-slate-800 bg-surface-900 text-slate-300';
}

export function performanceLabelClass(tone: MetricTone): string {
  if (tone === 'good') {
    return 'border-emerald-900/50 bg-emerald-950/40 text-emerald-300';
  }
  if (tone === 'bad') {
    return 'border-red-900/50 bg-red-950/40 text-red-300';
  }
  if (tone === 'neutral') {
    return 'border-amber-900/40 bg-amber-950/30 text-amber-200';
  }
  return 'border-slate-800 bg-surface-900 text-slate-400';
}

function toneFromThresholds(
  value: number,
  badMax: number,
  goodMin: number,
  lowerIsBetter = false,
): MetricTone {
  if (lowerIsBetter) {
    if (value < goodMin) return 'good';
    if (value > badMax) return 'bad';
    return 'neutral';
  }
  if (value >= goodMin) return 'good';
  if (value < badMax) return 'bad';
  return 'neutral';
}

export function performanceMetricTone(key: string, value?: number | null): MetricTone {
  if (value == null || Number.isNaN(value)) return 'unknown';

  switch (key) {
    case 'sharpe_ratio':
      return toneFromThresholds(value, 0.5, 1.0);
    case 'sortino_ratio':
      return toneFromThresholds(value, 0.5, 1.5);
    case 'profit_factor':
      if (isProfitFactorNoLosses(value)) return 'good';
      return toneFromThresholds(value, 1.0, 1.5);
    case 'calmar_ratio':
      return toneFromThresholds(value, 0.5, 1.0);
    case 'max_drawdown_pct':
      return toneFromThresholds(value, 20, 10, true);
    case 'win_rate_pct':
      return toneFromThresholds(value, 45, 55);
    default:
      return 'unknown';
  }
}

export function buildEquityChartData(
  strategy: BacktestEquityPoint[],
  benchmark: BacktestEquityPoint[],
): Array<{ date: string; strategy?: number; benchmark?: number }> {
  const byDate = new Map<string, { date: string; strategy?: number; benchmark?: number }>();

  for (const point of strategy) {
    byDate.set(point.date, { date: point.date, strategy: point.equity });
  }
  for (const point of benchmark) {
    const existing = byDate.get(point.date) ?? { date: point.date };
    existing.benchmark = point.equity;
    byDate.set(point.date, existing);
  }

  return [...byDate.values()].sort((a, b) => a.date.localeCompare(b.date));
}

export function buildIndexedEquityChartData(
  strategy: BacktestEquityPoint[],
  benchmark: BacktestEquityPoint[],
): Array<{ date: string; strategy?: number; benchmark?: number }> {
  const merged = buildEquityChartData(strategy, benchmark);
  if (!merged.length) {
    return [];
  }

  let strategyBase: number | undefined;
  let benchmarkBase: number | undefined;

  for (const row of merged) {
    if (strategyBase == null && row.strategy != null && row.strategy > 0) {
      strategyBase = row.strategy;
    }
    if (benchmarkBase == null && row.benchmark != null && row.benchmark > 0) {
      benchmarkBase = row.benchmark;
    }
    if (strategyBase != null && benchmarkBase != null) {
      break;
    }
  }

  return merged.map((row) => ({
    date: row.date,
    strategy:
      row.strategy != null && strategyBase != null && strategyBase > 0
        ? (row.strategy / strategyBase) * 100
        : undefined,
    benchmark:
      row.benchmark != null && benchmarkBase != null && benchmarkBase > 0
        ? (row.benchmark / benchmarkBase) * 100
        : undefined,
  }));
}

export function buildBacktestQuery(params: {
  start?: string;
  end?: string;
}): { start?: string; end?: string } {
  const query: { start?: string; end?: string } = {};
  if (params.start) query.start = params.start;
  if (params.end) query.end = params.end;
  return query;
}

export function summarizeReturnMetrics(metrics?: BacktestMetrics | null): Array<{
  key: string;
  label: string;
  value: string;
  tone?: number | null;
}> {
  if (!metrics) return [];
  return [
    {
      key: 'total_return_pct',
      label: 'Total Return',
      value: formatBacktestPct(metrics.total_return_pct),
      tone: metrics.total_return_pct,
    },
    {
      key: 'alpha_pct',
      label: 'Alpha vs B&H',
      value: formatBacktestPct(metrics.alpha_pct),
      tone: metrics.alpha_pct,
    },
    {
      key: 'benchmark_return_pct',
      label: 'Buy & Hold Return',
      value: formatBacktestPct(metrics.benchmark_return_pct),
      tone: metrics.benchmark_return_pct,
    },
    {
      key: 'cagr_pct',
      label: 'CAGR',
      value: formatBacktestPct(metrics.cagr_pct),
      tone: metrics.cagr_pct,
    },
    {
      key: 'final_equity',
      label: 'Final Equity',
      value: formatBacktestCurrency(metrics.final_equity),
      tone: metrics.total_return_pct,
    },
    {
      key: 'trade_count',
      label: 'Trades',
      value: String(metrics.trade_count),
      tone: null,
    },
  ];
}

export function summarizePerformanceLabels(metrics?: BacktestMetrics | null): Array<{
  key: string;
  label: string;
  value: string;
  tone: MetricTone;
  tradeDependent?: boolean;
}> {
  if (!metrics) return [];

  const hasTrades = metrics.trade_count > 0;

  return [
    {
      key: 'sharpe_ratio',
      label: 'Sharpe Ratio',
      value: formatBacktestRatio(metrics.sharpe_ratio),
      tone: performanceMetricTone('sharpe_ratio', metrics.sharpe_ratio),
    },
    {
      key: 'sortino_ratio',
      label: 'Sortino Ratio',
      value: formatBacktestRatio(metrics.sortino_ratio),
      tone: performanceMetricTone('sortino_ratio', metrics.sortino_ratio),
    },
    {
      key: 'profit_factor',
      label: 'Profit Factor',
      value: hasTrades ? formatBacktestProfitFactor(metrics.profit_factor) : '—',
      tone: hasTrades ? performanceMetricTone('profit_factor', metrics.profit_factor) : 'unknown',
      tradeDependent: true,
    },
    {
      key: 'calmar_ratio',
      label: 'Calmar Ratio',
      value: formatBacktestRatio(metrics.calmar_ratio),
      tone: performanceMetricTone('calmar_ratio', metrics.calmar_ratio),
    },
    {
      key: 'max_drawdown_pct',
      label: 'Max Drawdown',
      value: formatBacktestDrawdown(metrics.max_drawdown_pct),
      tone: performanceMetricTone('max_drawdown_pct', metrics.max_drawdown_pct),
    },
    {
      key: 'win_rate_pct',
      label: 'Win Rate',
      value: hasTrades ? formatBacktestPct(metrics.win_rate_pct) : '—',
      tone: hasTrades ? performanceMetricTone('win_rate_pct', metrics.win_rate_pct) : 'unknown',
      tradeDependent: true,
    },
  ];
}

/** @deprecated Use summarizeReturnMetrics for cards and summarizePerformanceLabels for pills. */
export function summarizeMetrics(metrics?: BacktestMetrics | null) {
  return [...summarizeReturnMetrics(metrics), ...summarizePerformanceLabels(metrics)];
}

export function sortTradesByExit(trades: BacktestTrade[]): BacktestTrade[] {
  return [...trades].sort((a, b) => b.exit_date.localeCompare(a.exit_date));
}
