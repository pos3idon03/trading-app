import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { mlBacktestApi } from '../../api/endpoints';
import type { MlModelCatalogItem, MlSavedModel } from '../../api/mlBacktestTypes';
import TradingModelResultsModal from '../../components/backtesting/TradingModelResultsModal';
import ConfirmModal from '../../components/ConfirmModal';
import DataTable, { type DataTableColumn } from '../../components/DataTable';
import ErrorAlert from '../../components/ErrorAlert';
import Spinner from '../../components/Spinner';
import Toast from '../../components/Toast';
import {
  buildCatalogById,
  buildMlEditUrl,
  mapTradingModelRows,
  type TradingModelRow,
} from '../../utils/tradingModels';

const EMPTY_MESSAGE =
  'No saved models yet. Train one from Backtesting → ML using Train & save model.';

const BASE_COLUMNS: DataTableColumn<TradingModelRow>[] = [
  { key: 'symbol', label: 'Asset', sortValue: (row) => row.symbol },
  { key: 'name', label: 'Model name', sortValue: (row) => row.name },
  { key: 'algorithm', label: 'Algorithm', sortValue: (row) => row.algorithm },
  { key: 'featureMode', label: 'Feature mode', sortValue: (row) => row.featureMode },
  { key: 'timeframe', label: 'Timeframe', sortValue: (row) => row.timeframe },
  {
    key: 'trainAccuracy',
    label: 'Train accuracy',
    align: 'right',
    sortValue: (row) => row.trainAccuracy,
  },
  {
    key: 'sampleCount',
    label: 'Samples',
    align: 'right',
    sortValue: (row) => row.sampleCount,
  },
  {
    key: 'createdAt',
    label: 'Created',
    sortValue: (row) => row.createdAtSort,
    render: (row) => row.createdAt,
  },
];

type ToastState = { message: string; variant: 'success' | 'error' };

export default function TradingModelsPage() {
  const navigate = useNavigate();
  const [catalog, setCatalog] = useState<MlModelCatalogItem[]>([]);
  const [rows, setRows] = useState<TradingModelRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resultsModel, setResultsModel] = useState<MlSavedModel | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<MlSavedModel | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [toast, setToast] = useState<ToastState | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [catalogResponse, savedResponse] = await Promise.all([
        mlBacktestApi.listModels(),
        mlBacktestApi.listSavedModels(),
      ]);
      setCatalog(catalogResponse.models);
      const catalogById = buildCatalogById(catalogResponse.models);
      setRows(mapTradingModelRows(savedResponse.models, catalogById));
    } catch (err) {
      setCatalog([]);
      setRows([]);
      setError(err instanceof Error ? err.message : 'Failed to load saved models.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleDeleteConfirm = async () => {
    if (!confirmDelete) return;
    setDeletingId(confirmDelete.id);
    try {
      await mlBacktestApi.deleteSavedModel(confirmDelete.id);
      setToast({ message: `Deleted ${confirmDelete.name}.`, variant: 'success' });
      setConfirmDelete(null);
      await load();
    } catch (err) {
      setToast({
        message: err instanceof Error ? err.message : 'Failed to delete model.',
        variant: 'error',
      });
    } finally {
      setDeletingId(null);
    }
  };

  const columns = useMemo((): DataTableColumn<TradingModelRow>[] => {
    return [
      ...BASE_COLUMNS,
      {
        key: 'actions',
        label: 'Actions',
        render: (row) => {
          const busy = deletingId === row.id || resultsModel?.id === row.id;
          return (
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={busy}
                onClick={() => setResultsModel(row.model)}
                className="text-xs font-medium text-brand-500 hover:text-brand-400 disabled:opacity-50"
              >
                See results
              </button>
              <button
                type="button"
                disabled={busy || row.symbol === '—'}
                onClick={() => navigate(buildMlEditUrl(row.model))}
                className="text-xs font-medium text-slate-300 hover:text-slate-100 disabled:opacity-50"
              >
                Update
              </button>
              <button
                type="button"
                disabled={busy || row.symbol === '—'}
                onClick={() =>
                  navigate(`/trading/deployments?modelId=${encodeURIComponent(row.id)}`)
                }
                className="text-xs font-medium text-emerald-400 hover:text-emerald-300 disabled:opacity-50"
              >
                Activate
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => setConfirmDelete(row.model)}
                className="text-xs font-medium text-red-400 hover:text-red-300 disabled:opacity-50"
              >
                Delete
              </button>
            </div>
          );
        },
      },
    ];
  }, [deletingId, navigate, resultsModel?.id]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Trading Models</h1>
        <p className="text-slate-400 text-sm mt-1">
          Persisted ML models trained via Backtesting → ML, with the asset each model was fit on.
        </p>
      </div>

      {error && <ErrorAlert message={error} />}
      {toast && (
        <Toast
          message={toast.message}
          variant={toast.variant}
          onDismiss={() => setToast(null)}
        />
      )}

      <ConfirmModal
        open={confirmDelete !== null}
        title="Delete saved model?"
        message={
          confirmDelete
            ? `Delete "${confirmDelete.name}"? This removes the model artifact and cannot be undone.`
            : ''
        }
        confirmLabel="Delete"
        busy={confirmDelete !== null && deletingId === confirmDelete.id}
        onConfirm={() => void handleDeleteConfirm()}
        onCancel={() => setConfirmDelete(null)}
      />

      <TradingModelResultsModal
        open={resultsModel !== null}
        model={resultsModel}
        onClose={() => setResultsModel(null)}
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
          sortResetKey={catalog.length ? 'loaded' : 'empty'}
          emptyMessage={EMPTY_MESSAGE}
        />
      )}
    </div>
  );
}
