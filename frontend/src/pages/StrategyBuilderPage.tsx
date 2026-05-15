import { useEffect, useState } from 'react';
import { dataApi, strategyBuilderApi } from '../api/endpoints';
import type { AssetItem, StrategyRecord } from '../api/types';
import AssetStrategyCard from '../components/AssetStrategyCard';
import Spinner from '../components/Spinner';
import ErrorAlert from '../components/ErrorAlert';
import { formatAssetOptionLabel } from '../utils/assetDisplay';

function useAssets() {
  const [assets, setAssets] = useState<AssetItem[]>([]);
  useEffect(() => {
    dataApi.getAssets().then((r) => setAssets(r.assets.filter((a) => a.is_active)));
  }, []);
  return assets;
}

function CreateStrategyForm({
  assets,
  existingAssetIds,
  onCreate,
}: {
  assets: AssetItem[];
  existingAssetIds: Set<number>;
  onCreate: (strategy: StrategyRecord) => void;
}) {
  const available = assets.filter((a) => !existingAssetIds.has(a.id));
  const [selectedId, setSelectedId] = useState<number | ''>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!selectedId) return;
    setLoading(true);
    setError(null);
    try {
      const record = await strategyBuilderApi.create({ asset_id: selectedId as number });
      onCreate(record);
      setSelectedId('');
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed to create strategy';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card flex flex-wrap items-end gap-3">
      <div className="flex-1 min-w-[200px]">
        <label className="metric-label block mb-1">Select Asset</label>
        <select
          className="w-full bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
          value={selectedId}
          onChange={(e) => setSelectedId(e.target.value ? Number(e.target.value) : '')}
          disabled={available.length === 0}
        >
          <option value="">{available.length === 0 ? 'All assets have strategies' : 'Choose asset…'}</option>
          {available.map((a) => (
            <option key={a.id} value={a.id}>
              {formatAssetOptionLabel(a)}
            </option>
          ))}
        </select>
      </div>

      <button
        className="btn-primary"
        onClick={handleCreate}
        disabled={!selectedId || loading}
      >
        {loading ? <Spinner size="sm" /> : 'Create Strategy'}
      </button>

      {error && <div className="w-full"><ErrorAlert message={error} /></div>}
    </div>
  );
}

export default function StrategyBuilderPage() {
  const assets = useAssets();
  const [strategies, setStrategies] = useState<StrategyRecord[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  useEffect(() => {
    strategyBuilderApi
      .list()
      .then(setStrategies)
      .catch(() => setListError('Failed to load strategies'))
      .finally(() => setLoadingList(false));
  }, []);

  const handleCreate = (record: StrategyRecord) => {
    setStrategies((prev) => [...prev, record]);
  };

  const handleRemove = (strategyId: number) => {
    setStrategies((prev) => prev.filter((s) => s.id !== strategyId));
  };

  const handleUpdated = (record: StrategyRecord) => {
    setStrategies((prev) => prev.map((s) => (s.id === record.id ? record : s)));
  };

  const existingAssetIds = new Set(strategies.map((s) => s.asset_id));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-slate-100">Strategy Builder</h1>
        <p className="text-slate-400 text-sm">
          Per-asset strategies combining Monte Carlo, AI Agents, Financials and Algo backtests.
        </p>
      </div>

      <CreateStrategyForm
        assets={assets}
        existingAssetIds={existingAssetIds}
        onCreate={handleCreate}
      />

      {loadingList && (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      )}

      {listError && <ErrorAlert message={listError} />}

      {!loadingList && strategies.length === 0 && !listError && (
        <div className="card text-center py-12 text-slate-500">
          No strategies yet. Create one above to get started.
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {strategies.map((s) => (
          <AssetStrategyCard
            key={s.id}
            strategy={s}
            onRemove={handleRemove}
            onUpdated={handleUpdated}
          />
        ))}
      </div>
    </div>
  );
}
