import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { executionApi, mlBacktestApi } from '../../api/endpoints';
import type { MlSavedModel } from '../../api/mlBacktestTypes';
import ConfirmModal from '../../components/ConfirmModal';
import DataTable, { type DataTableColumn } from '../../components/DataTable';
import ErrorAlert from '../../components/ErrorAlert';
import Spinner from '../../components/Spinner';
import Toast from '../../components/Toast';
import {
  deploymentStatusClass,
  formatDeploymentStatus,
  mapDeploymentRows,
  outcomeClass,
  type DeploymentRow,
} from '../../utils/tradingDeployments';

type ToastState = { message: string; variant: 'success' | 'error' };

export default function DeploymentsPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const prefillModelId = searchParams.get('modelId');

  const [rows, setRows] = useState<DeploymentRow[]>([]);
  const [savedModels, setSavedModels] = useState<MlSavedModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<ToastState | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(Boolean(prefillModelId));
  const [selectedModelId, setSelectedModelId] = useState(prefillModelId ?? '');
  const [allocationPct, setAllocationPct] = useState('100');
  const [confirmStop, setConfirmStop] = useState<DeploymentRow | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [deploymentsResponse, savedResponse] = await Promise.all([
        executionApi.listDeployments(),
        mlBacktestApi.listSavedModels(),
      ]);
      setRows(mapDeploymentRows(deploymentsResponse.deployments));
      setSavedModels(savedResponse.models);
    } catch (err) {
      setRows([]);
      setSavedModels([]);
      setError(err instanceof Error ? err.message : 'Failed to load deployments.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (prefillModelId) {
      setSelectedModelId(prefillModelId);
      setShowCreate(true);
    }
  }, [prefillModelId]);

  const handleCreate = async () => {
    if (!selectedModelId) return;
    setBusyId('create');
    try {
      await executionApi.createDeployment({
        model_id: selectedModelId,
        allocation_pct: Number(allocationPct) || 100,
      });
      setToast({ message: 'Deployment created.', variant: 'success' });
      setShowCreate(false);
      await load();
    } catch (err) {
      setToast({
        message: err instanceof Error ? err.message : 'Failed to create deployment.',
        variant: 'error',
      });
    } finally {
      setBusyId(null);
    }
  };

  const runAction = async (
    row: DeploymentRow,
    action: 'activate' | 'pause' | 'stop' | 'evaluate',
  ) => {
    setBusyId(row.id);
    try {
      if (action === 'activate') await executionApi.activateDeployment(row.id);
      if (action === 'pause') await executionApi.pauseDeployment(row.id);
      if (action === 'stop') await executionApi.stopDeployment(row.id);
      if (action === 'evaluate') {
        const result = await executionApi.evaluateDeployment(row.id);
        const detail =
          result.blocked_reason ?? result.outcome ?? result.signal ?? 'done';
        setToast({ message: `Evaluation: ${detail}`, variant: 'success' });
      } else {
        setToast({ message: `Deployment ${action}d.`, variant: 'success' });
      }
      await load();
    } catch (err) {
      setToast({
        message: err instanceof Error ? err.message : `Failed to ${action} deployment.`,
        variant: 'error',
      });
    } finally {
      setBusyId(null);
      setConfirmStop(null);
    }
  };

  const columns = useMemo((): DataTableColumn<DeploymentRow>[] => [
    { key: 'symbol', label: 'Symbol', sortValue: (row) => row.symbol },
    { key: 'modelName', label: 'Model', sortValue: (row) => row.modelName },
    {
      key: 'status',
      label: 'Status',
      sortValue: (row) => row.status,
      render: (row) => (
        <span className={deploymentStatusClass(row.status)}>
          {formatDeploymentStatus(row.status)}
        </span>
      ),
    },
    { key: 'allocationPct', label: 'Allocation', sortValue: (row) => row.deployment.allocation_pct },
    { key: 'lastSignal', label: 'Signal', sortValue: (row) => row.lastSignal },
    { key: 'lastProbability', label: 'Probability', sortValue: (row) => row.deployment.last_probability ?? 0 },
    {
      key: 'lastOutcome',
      label: 'Outcome',
      sortValue: (row) => row.lastOutcome,
      render: (row) => (
        <span className={outcomeClass(row.deployment.last_outcome)}>{row.lastOutcome}</span>
      ),
    },
    {
      key: 'lastBlockedReason',
      label: 'Block reason',
      sortValue: (row) => row.lastBlockedReason,
      render: (row) => (
        <span className="text-xs text-slate-400" title={row.lastBlockedReason}>
          {row.lastBlockedReason}
        </span>
      ),
    },
    {
      key: 'lastEvaluated',
      label: 'Last evaluated',
      sortValue: (row) => row.lastEvaluatedSort,
      render: (row) => row.lastEvaluated,
    },
    {
      key: 'actions',
      label: 'Actions',
      render: (row) => {
        const busy = busyId === row.id;
        return (
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={() => navigate(`/trading/activity?deploymentId=${encodeURIComponent(row.id)}`)}
              className="text-xs font-medium text-brand-500 hover:text-brand-400 disabled:opacity-50"
            >
              View activity
            </button>
            {row.status !== 'active' && (
              <button
                type="button"
                disabled={busy}
                onClick={() => void runAction(row, 'activate')}
                className="text-xs font-medium text-brand-500 hover:text-brand-400 disabled:opacity-50"
              >
                Activate
              </button>
            )}
            {row.status === 'active' && (
              <>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void runAction(row, 'pause')}
                  className="text-xs font-medium text-amber-400 hover:text-amber-300 disabled:opacity-50"
                >
                  Pause
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void runAction(row, 'evaluate')}
                  className="text-xs font-medium text-slate-300 hover:text-slate-100 disabled:opacity-50"
                >
                  Evaluate now
                </button>
              </>
            )}
            <button
              type="button"
              disabled={busy}
              onClick={() => setConfirmStop(row)}
              className="text-xs font-medium text-red-400 hover:text-red-300 disabled:opacity-50"
            >
              Stop
            </button>
          </div>
        );
      },
    },
  ], [busyId, navigate]);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Deployments</h1>
          <p className="text-slate-400 text-sm mt-1">
            Activate saved ML models for paper trading via Alpaca.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowCreate(true)}
          className="px-3 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-500"
        >
          New deployment
        </button>
      </div>

      {error && <ErrorAlert message={error} />}
      {toast && (
        <Toast message={toast.message} variant={toast.variant} onDismiss={() => setToast(null)} />
      )}

      {showCreate && (
        <div className="rounded-xl border border-slate-800 bg-surface-900 p-4 space-y-4">
          <h2 className="text-sm font-semibold text-slate-200">Create deployment</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block text-sm text-slate-400">
              Saved model
              <select
                value={selectedModelId}
                onChange={(e) => setSelectedModelId(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-700 bg-surface-800 px-3 py-2 text-slate-100"
              >
                <option value="">Select a model</option>
                {savedModels.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm text-slate-400">
              Allocation %
              <input
                type="number"
                min={1}
                max={100}
                value={allocationPct}
                onChange={(e) => setAllocationPct(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-700 bg-surface-800 px-3 py-2 text-slate-100"
              />
            </label>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={!selectedModelId || busyId === 'create'}
              onClick={() => void handleCreate()}
              className="px-3 py-2 rounded-lg bg-brand-600 text-white text-sm disabled:opacity-50"
            >
              Create
            </button>
            <button
              type="button"
              onClick={() => setShowCreate(false)}
              className="px-3 py-2 rounded-lg border border-slate-700 text-slate-300 text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <ConfirmModal
        open={confirmStop !== null}
        title="Stop deployment?"
        message={
          confirmStop
            ? `Stop deployment for ${confirmStop.symbol}? It will no longer evaluate or trade.`
            : ''
        }
        confirmLabel="Stop"
        busy={confirmStop !== null && busyId === confirmStop.id}
        onConfirm={() => confirmStop && void runAction(confirmStop, 'stop')}
        onCancel={() => setConfirmStop(null)}
      />

      {loading ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : (
        <DataTable
          columns={columns}
          rows={rows}
          rowKey={(row) => row.id}
          sortResetKey={rows.length ? 'loaded' : 'empty'}
          emptyMessage="No deployments yet. Create one from a saved model."
        />
      )}
    </div>
  );
}
