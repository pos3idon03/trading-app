import type { TradingDeployment } from '../api/executionTypes';

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

export function formatCurrency(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '—';
  return value.toLocaleString(undefined, {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  });
}

export interface DeploymentRow {
  id: string;
  deployment: TradingDeployment;
  symbol: string;
  modelName: string;
  status: string;
  allocationPct: string;
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
    modelName: deployment.model_name ?? '—',
    status: deployment.status,
    allocationPct: `${deployment.allocation_pct}%`,
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
