import type { DeploymentOverview, ExecutionActivityEvent } from '../api/executionTypes';
import { formatBacktestCurrency, formatBacktestPct, metricCardClass } from './backtestData';
import { formatProbabilityContext, PROBABILITY_UP_LABEL } from './probabilityExplainability';
import {
  formatDateTime,
  formatDateTimeWithTimezone,
  formatProbability,
  formatSignal,
} from './tradingDeployments';

export interface OverviewMetricRow {
  label: string;
  value: string;
  sublabel?: string;
  expandable?: boolean;
}

export function formatOverviewPrice(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatOverviewProfit(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '—';
  const formatted = formatBacktestCurrency(value);
  if (value > 0 && formatted.startsWith('$')) {
    return `+${formatted}`;
  }
  return formatted;
}

export function formatOverviewProfitPct(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '—';
  const formatted = formatBacktestPct(value);
  if (formatted === '—') return formatted;
  return formatted;
}

export function profitMetricClass(value: number | null | undefined): string {
  return metricCardClass(value);
}

export function mergeOverviewWithActivity(
  deployments: DeploymentOverview[],
  events: ExecutionActivityEvent[],
): DeploymentOverview[] {
  if (!events.length) return deployments;
  const latestByDeployment = new Map<string, ExecutionActivityEvent>();
  for (const event of events) {
    const existing = latestByDeployment.get(event.deployment_id);
    if (!existing || event.created_at > existing.created_at) {
      latestByDeployment.set(event.deployment_id, event);
    }
  }
  return deployments.map((row) => {
    const event = latestByDeployment.get(row.id);
    if (!event) return row;
    return {
      ...row,
      last_signal: event.signal,
      last_probability: event.probability,
      buy_threshold: event.buy_threshold ?? row.buy_threshold,
      sell_threshold: event.sell_threshold ?? row.sell_threshold,
      last_explainability: event.explainability ?? row.last_explainability,
      last_evaluated_bar_time: event.bar_time,
    };
  });
}

export function overviewLatestUpdate(row: DeploymentOverview): {
  value: string;
  timezone: string;
} {
  if (row.last_evaluated_bar_time) {
    return formatDateTimeWithTimezone(row.last_evaluated_bar_time);
  }
  if (row.price_updated_at) {
    return formatDateTimeWithTimezone(row.price_updated_at);
  }
  return { value: '—', timezone: '' };
}

export function overviewMetricRows(row: DeploymentOverview): OverviewMetricRow[] {
  const latestUpdate = overviewLatestUpdate(row);
  return [
    { label: 'Latest price', value: formatOverviewPrice(row.current_price) },
    {
      label: 'Latest update',
      value: latestUpdate.value,
      sublabel: latestUpdate.timezone || undefined,
    },
    { label: 'Signal', value: formatSignal(row.last_signal) },
    {
      label: PROBABILITY_UP_LABEL,
      value: formatProbability(row.last_probability),
      sublabel: formatProbabilityContext(
        row.last_probability,
        row.buy_threshold,
        row.sell_threshold,
      ) || undefined,
      expandable: true,
    },
    { label: 'Positions executed', value: String(row.round_trip_count) },
    { label: 'Open positions', value: String(row.open_position_count) },
    { label: 'Orders', value: String(row.order_count) },
    { label: 'Strategy profit', value: formatOverviewProfit(row.strategy_profit) },
    {
      label: 'Strategy profit %',
      value: formatOverviewProfitPct(row.strategy_profit_pct),
    },
  ];
}
