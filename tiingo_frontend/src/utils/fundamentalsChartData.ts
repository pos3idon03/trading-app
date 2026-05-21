import type { FundamentalFormat } from '../constants/fundamentalsMetrics';
import type { FundamentalMetric } from '../api/types';

export interface FundamentalChartPoint {
  period: string;
  time: string;
  value: number;
}

const MIN_POINTS = 2;

export function buildFundamentalsSeries(
  metrics: FundamentalMetric[],
  metricName: string,
): FundamentalChartPoint[] {
  return metrics
    .filter((m) => m.metric_name === metricName)
    .map((m) => ({
      period: m.period ?? m.time.slice(0, 10),
      time: m.time,
      value: m.value,
    }))
    .sort((a, b) => a.time.localeCompare(b.time));
}

export function metricsWithChartData(
  metrics: FundamentalMetric[],
  metricNames: string[],
): Set<string> {
  const counts = new Map<string, number>();
  for (const row of metrics) {
    if (!metricNames.includes(row.metric_name)) continue;
    counts.set(row.metric_name, (counts.get(row.metric_name) ?? 0) + 1);
  }
  return new Set(
    [...counts.entries()].filter(([, n]) => n >= MIN_POINTS).map(([name]) => name),
  );
}

export function formatFundamentalValue(value: number, format: FundamentalFormat): string {
  const abs = Math.abs(value);
  if (format === 'currency') {
    if (abs >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
    if (abs >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
    if (abs >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
    if (abs >= 1e3) return `$${(value / 1e3).toFixed(2)}K`;
    return `$${value.toFixed(2)}`;
  }
  if (format === 'percent') {
    const pct = abs <= 1 ? value * 100 : value;
    return `${pct.toFixed(2)}%`;
  }
  if (format === 'perShare') {
    return `$${value.toFixed(2)}`;
  }
  return value.toFixed(2);
}
