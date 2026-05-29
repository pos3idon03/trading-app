import { useCallback, useState } from 'react';
import { executionApi } from '../../api/endpoints';
import type { DeploymentOverview } from '../../api/executionTypes';
import DeploymentOverviewCard from '../../components/trading/DeploymentOverviewCard';
import ErrorAlert from '../../components/ErrorAlert';
import Spinner from '../../components/Spinner';
import Toast from '../../components/Toast';
import { useTradingOverview } from '../../hooks/useTradingOverview';

type ToastState = { message: string; variant: 'success' | 'error' };

export default function OverviewPage() {
  const { deployments, loading, error, connectionState, reload } = useTradingOverview();
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<ToastState | null>(null);

  const staleCount = deployments.filter((row) => row.update_status === 'stale').length;

  const runGlobalAction = useCallback(
    async (label: string, action: () => Promise<{ job_id: string }>) => {
      setBusy(true);
      try {
        const result = await action();
        setToast({
          message: `${label} queued (${result.job_id}).`,
          variant: 'success',
        });
      } catch (err) {
        setToast({
          message: err instanceof Error ? err.message : `Failed to ${label.toLowerCase()}.`,
          variant: 'error',
        });
      } finally {
        setBusy(false);
      }
    },
    [],
  );

  const handleRefresh = useCallback(
    async (deployment: DeploymentOverview) => {
      setBusy(true);
      try {
        await executionApi.refreshDeployment(deployment.id);
        setToast({
          message: `${deployment.symbol} market data refreshed.`,
          variant: 'success',
        });
        await reload();
      } catch (err) {
        setToast({
          message: err instanceof Error ? err.message : 'Refresh failed.',
          variant: 'error',
        });
      } finally {
        setBusy(false);
      }
    },
    [reload],
  );

  const handleEvaluate = useCallback(
    async (deployment: DeploymentOverview) => {
      setBusy(true);
      try {
        const result = await executionApi.evaluateDeployment(deployment.id);
        const signal = result.signal?.toUpperCase() ?? '—';
        setToast({
          message: result.skipped
            ? `${deployment.symbol} already evaluated for latest bar.`
            : `${deployment.symbol} evaluated — ${signal}.`,
          variant: 'success',
        });
        await reload();
      } catch (err) {
        setToast({
          message: err instanceof Error ? err.message : 'Evaluation failed.',
          variant: 'error',
        });
      } finally {
        setBusy(false);
      }
    },
    [reload],
  );

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Overview</h1>
          <p className="text-slate-400 text-sm mt-1">
            Live snapshot of every deployment — price, signal, positions, orders, and strategy P/L.
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2 text-xs text-slate-400">
          <span>
            WebSocket:{' '}
            <span
              className={
                connectionState === 'connected' ? 'text-emerald-400' : 'text-amber-400'
              }
            >
              {connectionState}
            </span>
          </span>
          <button
            type="button"
            disabled={busy}
            onClick={() => void runGlobalAction('Market data refresh', () => executionApi.enqueueMarketDataRefresh())}
            className="rounded-lg border border-slate-700 px-3 py-1.5 text-slate-300 hover:bg-surface-800 disabled:opacity-50"
          >
            Refresh all data
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => void runGlobalAction('Evaluate all', () => executionApi.enqueueEvaluateAll())}
            className="rounded-lg border border-brand-700/60 bg-brand-950/30 px-3 py-1.5 text-brand-300 hover:bg-brand-950/50 disabled:opacity-50"
          >
            Evaluate all
          </button>
          <button
            type="button"
            onClick={() => void reload()}
            className="rounded-lg border border-slate-700 px-3 py-1.5 text-slate-300 hover:bg-surface-800"
          >
            Reload
          </button>
        </div>
      </div>

      {toast && (
        <Toast message={toast.message} variant={toast.variant} onDismiss={() => setToast(null)} />
      )}

      {staleCount > 0 && (
        <div className="rounded-xl border border-amber-800/60 bg-amber-950/20 px-4 py-3 text-sm text-amber-200">
          {staleCount} deployment{staleCount === 1 ? '' : 's'} behind schedule — reconciliation
          will catch up automatically, or use Refresh / Evaluate on each card.
        </div>
      )}

      {error && <ErrorAlert message={error} />}

      {loading ? (
        <Spinner />
      ) : deployments.length === 0 ? (
        <div className="rounded-xl border border-slate-800 bg-surface-900 p-6 text-sm text-slate-400">
          No deployments yet. Create one from the Deployments page to start paper trading.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 items-start">
          {deployments.map((deployment) => (
            <DeploymentOverviewCard
              key={deployment.id}
              deployment={deployment}
              busy={busy}
              onRefresh={handleRefresh}
              onEvaluate={handleEvaluate}
            />
          ))}
        </div>
      )}
    </div>
  );
}
