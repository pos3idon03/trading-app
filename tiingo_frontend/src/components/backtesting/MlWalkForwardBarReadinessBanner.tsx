import type { WalkForwardBarReadiness } from '../../utils/mlWalkForwardBarReadiness';
import { formatWalkForwardMinimumBreakdown } from '../../utils/mlWalkForwardBarReadiness';

interface MlWalkForwardBarReadinessBannerProps {
  readiness: WalkForwardBarReadiness;
  validationError?: string | null;
}

function statusStyles(status: WalkForwardBarReadiness['status']): {
  border: string;
  bg: string;
  badge: string;
  badgeText: string;
  bar: string;
} {
  switch (status) {
    case 'ready':
      return {
        border: 'border-emerald-900/60',
        bg: 'bg-emerald-950/25',
        badge: 'bg-emerald-900/50',
        badgeText: 'text-emerald-200',
        bar: 'bg-emerald-500',
      };
    case 'loading':
    case 'unknown':
      return {
        border: 'border-slate-700',
        bg: 'bg-surface-950/50',
        badge: 'bg-slate-800',
        badgeText: 'text-slate-300',
        bar: 'bg-slate-500',
      };
    default:
      return {
        border: 'border-red-900/60',
        bg: 'bg-red-950/20',
        badge: 'bg-red-900/50',
        badgeText: 'text-red-200',
        bar: 'bg-red-500',
      };
  }
}

function statusBadgeLabel(status: WalkForwardBarReadiness['status']): string {
  switch (status) {
    case 'ready':
      return 'Data Prep OK';
    case 'loading':
      return 'Checking…';
    case 'unknown':
      return 'Awaiting bars';
    case 'insufficient_bars':
      return 'Data Prep blocked';
    default:
      return 'Check settings';
  }
}

export default function MlWalkForwardBarReadinessBanner({
  readiness,
  validationError,
}: MlWalkForwardBarReadinessBannerProps) {
  const cryptoTip = readiness.cryptoTip;
  const styles = statusStyles(readiness.status);
  const available = readiness.availableBars;
  const minimum = readiness.minimumRequired;
  const progressPct =
    available != null && available > 0
      ? Math.min(100, Math.round((available / minimum) * 100))
      : null;

  return (
    <div className={`rounded-lg border p-4 space-y-3 ${styles.border} ${styles.bg}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1 min-w-0 flex-1">
          <p className="text-sm font-medium text-slate-100">{readiness.headline}</p>
          {readiness.detail && (
            <p className="text-xs text-slate-400 leading-relaxed">{readiness.detail}</p>
          )}
        </div>
        <span
          className={`shrink-0 text-xs font-semibold uppercase tracking-wide px-2.5 py-1 rounded ${styles.badge} ${styles.badgeText}`}
        >
          {statusBadgeLabel(readiness.status)}
        </span>
      </div>

      <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
        <div>
          <dt className="text-slate-500 text-xs">Available bars</dt>
          <dd className="text-slate-100 font-medium tabular-nums">
            {available != null ? available.toLocaleString() : '—'}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500 text-xs">Minimum for Data Prep</dt>
          <dd className="text-slate-100 font-medium tabular-nums">
            {minimum.toLocaleString()}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500 text-xs">
            {readiness.shortfall != null ? 'Shortfall' : 'Headroom'}
          </dt>
          <dd
            className={`font-medium tabular-nums ${
              readiness.shortfall != null ? 'text-red-300' : 'text-slate-100'
            }`}
          >
            {readiness.shortfall != null
              ? `−${readiness.shortfall.toLocaleString()}`
              : readiness.headroom != null
                ? `+${readiness.headroom.toLocaleString()}`
                : '—'}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500 text-xs">Structural folds</dt>
          <dd className="text-slate-100 font-medium tabular-nums">
            {readiness.status === 'loading' || readiness.status === 'unknown'
              ? '—'
              : `~${readiness.structuralFolds}`}
          </dd>
        </div>
      </dl>

      {progressPct != null && (
        <div className="space-y-1">
          <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${styles.bar}`}
              style={{ width: `${progressPct}%` }}
            />
          </div>
          <p className="text-xs text-slate-500 tabular-nums">
            {available?.toLocaleString()} / {minimum.toLocaleString()} bars required for Data Prep
          </p>
        </div>
      )}

      <p className="text-xs text-slate-500">
        Minimum breakdown: {formatWalkForwardMinimumBreakdown(readiness.breakdown)}. Walk-forward
        budget (after warmup and label tail):{' '}
        {readiness.walkForwardBudget != null
          ? readiness.walkForwardBudget.toLocaleString()
          : '—'}{' '}
        bars for train + test windows.
      </p>

      {cryptoTip && (
        <p className="text-xs text-sky-200/80 leading-relaxed border border-sky-900/40 bg-sky-950/20 rounded-lg px-3 py-2">
          {cryptoTip}
        </p>
      )}

      {validationError && readiness.status !== 'ready' && (
        <p className="text-xs text-amber-200/90">{validationError}</p>
      )}
    </div>
  );
}
