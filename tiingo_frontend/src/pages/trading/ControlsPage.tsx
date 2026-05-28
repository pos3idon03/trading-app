import { useCallback, useEffect, useState } from 'react';
import { executionApi } from '../../api/endpoints';
import type { ExecutionStatus, RiskConfig } from '../../api/executionTypes';
import ErrorAlert from '../../components/ErrorAlert';
import Spinner from '../../components/Spinner';
import Toast from '../../components/Toast';

type ToastState = { message: string; variant: 'success' | 'error' };

export default function ControlsPage() {
  const [status, setStatus] = useState<ExecutionStatus | null>(null);
  const [risk, setRisk] = useState<RiskConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<ToastState | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statusResponse, riskResponse] = await Promise.all([
        executionApi.getStatus(),
        executionApi.getRiskConfig(),
      ]);
      setStatus(statusResponse);
      setRisk(riskResponse);
    } catch (err) {
      setStatus(null);
      setRisk(null);
      setError(err instanceof Error ? err.message : 'Failed to load controls.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const toggleKillSwitch = async () => {
    if (!status) return;
    setBusy(true);
    try {
      const next = !status.kill_switch_enabled;
      await executionApi.setKillSwitch(next);
      setToast({
        message: next ? 'Kill switch enabled.' : 'Kill switch disabled.',
        variant: 'success',
      });
      await load();
    } catch (err) {
      setToast({
        message: err instanceof Error ? err.message : 'Failed to update kill switch.',
        variant: 'error',
      });
    } finally {
      setBusy(false);
    }
  };

  const enqueueEvaluateAll = async () => {
    setBusy(true);
    try {
      const result = await executionApi.enqueueEvaluateAll();
      setToast({
        message: `Evaluation job queued (${result.job_id}).`,
        variant: 'success',
      });
    } catch (err) {
      setToast({
        message: err instanceof Error ? err.message : 'Failed to queue evaluation.',
        variant: 'error',
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Controls</h1>
        <p className="text-slate-400 text-sm mt-1">
          Kill switch, risk limits, and broker connection status.
        </p>
      </div>

      {error && <ErrorAlert message={error} />}
      {toast && (
        <Toast message={toast.message} variant={toast.variant} onDismiss={() => setToast(null)} />
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : (
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-800 bg-surface-900 p-4">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="text-sm font-semibold text-slate-200">Kill switch</h2>
                <p className="text-xs text-slate-500 mt-1">
                  When enabled, no new orders will be submitted.
                </p>
              </div>
              <button
                type="button"
                disabled={busy}
                onClick={() => void toggleKillSwitch()}
                className={
                  status?.kill_switch_enabled
                    ? 'px-3 py-2 rounded-lg bg-red-600 text-white text-sm font-medium'
                    : 'px-3 py-2 rounded-lg bg-slate-700 text-slate-100 text-sm font-medium'
                }
              >
                {status?.kill_switch_enabled ? 'Enabled — click to disable' : 'Disabled — click to enable'}
              </button>
            </div>
          </div>

          <div className="rounded-xl border border-slate-800 bg-surface-900 p-4">
            <h2 className="text-sm font-semibold text-slate-200">Broker status</h2>
            <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-slate-500">Paper mode</dt>
                <dd className="text-slate-100">{status?.trading_mode_paper ? 'Yes' : 'No'}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Trading mode</dt>
                <dd className="text-slate-100">{status?.trading_mode ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Alpaca configured</dt>
                <dd className="text-slate-100">{status?.alpaca_configured ? 'Yes' : 'No'}</dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-slate-500">Base URL</dt>
                <dd className="text-slate-100 break-all">{status?.alpaca_base_url ?? '—'}</dd>
              </div>
            </dl>
          </div>

          {risk && (
            <div className="rounded-xl border border-slate-800 bg-surface-900 p-4">
              <h2 className="text-sm font-semibold text-slate-200">Risk limits</h2>
              <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-slate-500">Max position %</dt>
                  <dd className="text-slate-100">{risk.max_position_pct}%</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Max exposure %</dt>
                  <dd className="text-slate-100">{risk.max_exposure_pct}%</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Daily loss limit %</dt>
                  <dd className="text-slate-100">{risk.daily_loss_limit_pct}%</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Max orders / minute</dt>
                  <dd className="text-slate-100">{risk.max_orders_per_minute}</dd>
                </div>
              </dl>
            </div>
          )}

          <div className="rounded-xl border border-slate-800 bg-surface-900 p-4">
            <h2 className="text-sm font-semibold text-slate-200">Manual evaluation</h2>
            <p className="text-xs text-slate-500 mt-1 mb-3">
              Queue evaluation for all active deployments (runs in worker).
            </p>
            <button
              type="button"
              disabled={busy}
              onClick={() => void enqueueEvaluateAll()}
              className="px-3 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium disabled:opacity-50"
            >
              Evaluate all active
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
