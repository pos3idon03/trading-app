import type { ExecutionTimeframe, TradingDeployment } from '../api/executionTypes';
import { EXECUTION_TIMEFRAMES } from '../api/executionTypes';

export function deploymentStatusClass(status: string): string {
  switch (status) {
    case 'active':
      return 'text-emerald-400';
    case 'paused':
      return 'text-amber-400';
    case 'error':
      return 'text-red-400';
    case 'stopped':
      return 'text-slate-400';
    default:
      return 'text-slate-300';
  }
}

export function outcomeClass(outcome: string | null | undefined): string {
  switch (outcome) {
    case 'order_submitted':
      return 'text-emerald-400';
    case 'blocked':
    case 'error':
      return 'text-red-400';
    case 'skipped':
      return 'text-amber-400';
    case 'hold':
      return 'text-slate-400';
    default:
      return 'text-slate-300';
  }
}

export function formatDeploymentStatus(status: string): string {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

export function formatOutcome(outcome: string | null | undefined): string {
  if (!outcome) return '—';
  return outcome.replaceAll('_', ' ');
}

export function formatSignal(signal: string | null | undefined): string {
  if (!signal) return '—';
  return signal.toUpperCase();
}

export function formatProbability(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '—';
  return `${(value * 100).toFixed(1)}%`;
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatDateTimeWithTimezone(value: string | null | undefined): {
  value: string;
  timezone: string;
} {
  if (!value) {
    return { value: '—', timezone: '' };
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return { value: '—', timezone: '' };
  }
  const formatted = formatDateTime(value);
  const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const shortName = new Intl.DateTimeFormat(undefined, {
    timeZoneName: 'short',
  })
    .formatToParts(date)
    .find((part) => part.type === 'timeZoneName')?.value;
  const timezone = shortName ? `${timeZone} (${shortName})` : timeZone;
  return { value: formatted, timezone };
}

export function formatCurrency(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '—';
  return value.toLocaleString(undefined, {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  });
}

export function formatPositionSide(side: string | null | undefined, qty?: number | null): string {
  if (qty != null && qty > 0) {
    return `${side?.toLowerCase() === 'long' ? 'Long' : side ?? 'Long'} ${qty.toFixed(4)}`;
  }
  if (!side || side === 'flat') return 'Flat';
  return side.charAt(0).toUpperCase() + side.slice(1);
}

export interface DeploymentRow {
  id: string;
  deployment: TradingDeployment;
  symbol: string;
  timeframe: string;
  modelName: string;
  status: string;
  allocationPct: string;
  positionLabel: string;
  positionSort: number;
  lastSignal: string;
  lastOutcome: string;
  lastBlockedReason: string;
  lastProbability: string;
  lastEvaluated: string;
  lastEvaluatedSort: number;
}

export function toDeploymentRow(deployment: TradingDeployment): DeploymentRow {
  const lastEvaluatedSort = deployment.last_evaluated_bar_time
    ? new Date(deployment.last_evaluated_bar_time).getTime()
    : 0;
  return {
    id: deployment.id,
    deployment,
    symbol: deployment.symbol,
    timeframe: deployment.timeframe,
    modelName: deployment.model_name ?? '—',
    status: deployment.status,
    allocationPct: `${deployment.allocation_pct}%`,
    positionLabel: formatPositionSide(deployment.position_side, deployment.position_qty),
    positionSort: deployment.position_qty ?? 0,
    lastSignal: formatSignal(deployment.last_signal),
    lastOutcome: formatOutcome(deployment.last_outcome),
    lastBlockedReason: deployment.last_blocked_reason ?? '—',
    lastProbability: formatProbability(deployment.last_probability),
    lastEvaluated: formatDateTime(deployment.last_evaluated_bar_time),
    lastEvaluatedSort: Number.isNaN(lastEvaluatedSort) ? 0 : lastEvaluatedSort,
  };
}

export function mapDeploymentRows(deployments: TradingDeployment[]): DeploymentRow[] {
  return deployments.map(toDeploymentRow);
}

export function isExecutionTimeframe(value: string | null | undefined): value is ExecutionTimeframe {
  if (!value) return false;
  return (EXECUTION_TIMEFRAMES as readonly string[]).includes(value);
}

export function filterDeployableModels<T extends { timeframe?: string | null }>(models: T[]): T[] {
  return models.filter((model) => isExecutionTimeframe(model.timeframe ?? '1d'));
}

export function mergeActivityEvents<T extends { id: string }>(existing: T[], incoming: T[]): T[] {
  const byId = new Map(existing.map((item) => [item.id, item]));
  for (const item of incoming) {
    byId.set(item.id, item);
  }
  return Array.from(byId.values()).sort(
    (a, b) =>
      new Date((b as { created_at?: string }).created_at ?? 0).getTime() -
      new Date((a as { created_at?: string }).created_at ?? 0).getTime(),
  );
}
