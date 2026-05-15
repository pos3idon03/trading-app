import { useCallback, useEffect, useState } from 'react';
import { dataApi } from '../api/endpoints';
import type { AssetWithPrice, IngestionStatusResponse, IngestResponse } from '../api/types';
import MetricCard from '../components/MetricCard';
import StatusBadge from '../components/StatusBadge';
import Spinner from '../components/Spinner';
import ErrorAlert from '../components/ErrorAlert';
import TickerSearch from '../components/TickerSearch';

const DEFAULT_TIMEFRAMES = ['1d', '1h'];
const PAGE_SIZE = 20;

interface DeleteConfirm {
  symbol: string;
}

export default function Dashboard() {
  const [status, setStatus] = useState<IngestionStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ingestResult, setIngestResult] = useState<IngestResponse | null>(null);
  const [ingesting, setIngesting] = useState(false);
  const [symbols, setSymbols] = useState<string[]>([]);

  const [assets, setAssets] = useState<AssetWithPrice[]>([]);
  const [assetsLoading, setAssetsLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [deleteConfirm, setDeleteConfirm] = useState<DeleteConfirm | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [reingesting, setReingesting] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      const data = await dataApi.getStatus();
      setStatus(data);
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const fetchAssets = useCallback(async () => {
    setAssetsLoading(true);
    try {
      const data = await dataApi.getAssetsWithPrices();
      setAssets(data.assets);
      setCurrentPage(1);
    } catch {
      // silently ignore — table will stay empty
    } finally {
      setAssetsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    fetchAssets();
    const interval = setInterval(fetchStatus, 30_000);
    return () => clearInterval(interval);
  }, [fetchAssets]);

  const handleIngest = async () => {
    setIngesting(true);
    setIngestResult(null);
    try {
      const result = await dataApi.triggerIngestion({
        symbols,
        timeframes: DEFAULT_TIMEFRAMES,
        provider: 'yfinance',
      });
      setIngestResult(result);
      await fetchStatus();
      await fetchAssets();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIngesting(false);
    }
  };

  const handleReingest = async (symbol: string) => {
    setReingesting(symbol);
    try {
      await dataApi.triggerIngestion({
        symbols: [symbol],
        timeframes: DEFAULT_TIMEFRAMES,
        provider: 'yfinance',
      });
      await fetchAssets();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setReingesting(null);
    }
  };

  const handleDeleteConfirmed = async () => {
    if (!deleteConfirm) return;
    const { symbol } = deleteConfirm;
    setDeleteConfirm(null);
    setDeleting(symbol);
    try {
      await dataApi.deleteAsset(symbol);
      await fetchAssets();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setDeleting(null);
    }
  };

  const totalPages = Math.max(1, Math.ceil(assets.length / PAGE_SIZE));
  const pagedAssets = assets.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Dashboard</h1>
        <p className="text-slate-400 text-sm mt-1">Data ingestion status and pipeline health</p>
      </div>

      {error && <ErrorAlert message={error} />}

      {loading ? (
        <Spinner />
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <MetricCard label="Pipeline Status" value={status?.status ?? '—'} />
            <MetricCard label="Active Jobs" value={status?.active_jobs ?? 0} />
            <MetricCard label="Scheduled Jobs" value={status?.scheduled_jobs.length ?? 0} />
            <MetricCard
              label="Last Run"
              value={status?.last_run ? new Date(status.last_run).toLocaleTimeString() : 'Never'}
            />
          </div>

          <div className="card">
            <h2 className="text-slate-200 font-semibold mb-4">Manual Ingestion</h2>
            <div className="flex flex-col gap-3">
              <div>
                <label className="metric-label block mb-1">Search and add symbols</label>
                <TickerSearch selected={symbols} onChange={setSymbols} />
              </div>
              <div>
                <button
                  onClick={handleIngest}
                  disabled={ingesting || symbols.length === 0}
                  className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {ingesting ? 'Ingesting…' : 'Trigger Ingestion'}
                </button>
              </div>
            </div>

            {ingestResult && (
              <div className="mt-4 p-3 bg-surface-900 rounded-lg border border-slate-700 text-sm">
                <div className="flex items-center gap-2 mb-1">
                  <StatusBadge status={ingestResult.status} />
                  <span className="text-slate-300">{ingestResult.message}</span>
                </div>
                <p className="text-slate-500 font-mono text-xs">Job ID: {ingestResult.job_id}</p>
              </div>
            )}
          </div>

          <div className="card">
            <h2 className="text-slate-200 font-semibold mb-3">Ingested Assets</h2>

            {assetsLoading ? (
              <Spinner />
            ) : assets.length === 0 ? (
              <p className="text-slate-500 text-sm">No assets ingested yet.</p>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-slate-500 border-b border-slate-700">
                        <th className="text-left pb-2 font-medium">Company Name</th>
                        <th className="text-left pb-2 font-medium">Ticker</th>
                        <th className="text-right pb-2 font-medium">Latest Close Price</th>
                        <th className="text-left pb-2 font-medium pl-6">Latest Update</th>
                        <th className="text-right pb-2 font-medium">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {pagedAssets.map((asset) => (
                        <tr key={asset.id} className="border-b border-slate-800 text-slate-300 hover:bg-slate-800/30 transition-colors">
                          <td className="py-2.5">{asset.name ?? '—'}</td>
                          <td className="py-2.5 font-mono font-semibold text-brand-400">{asset.symbol}</td>
                          <td className="py-2.5 text-right font-mono">
                            {asset.latest_close != null
                              ? `$${asset.latest_close.toFixed(2)}`
                              : <span className="text-slate-600">—</span>
                            }
                          </td>
                          <td className="py-2.5 text-slate-400 text-xs pl-6">
                            {asset.latest_update
                              ? new Date(asset.latest_update).toLocaleDateString(undefined, {
                                  year: 'numeric', month: 'short', day: 'numeric',
                                })
                              : <span className="text-slate-600">—</span>
                            }
                          </td>
                          <td className="py-2.5 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <button
                                onClick={() => handleReingest(asset.symbol)}
                                disabled={reingesting === asset.symbol || !!deleting}
                                className="px-2.5 py-1 text-xs rounded bg-brand-500/15 text-brand-400 border border-brand-500/30 hover:bg-brand-500/25 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                              >
                                {reingesting === asset.symbol ? 'Ingesting…' : 'Re-ingest'}
                              </button>
                              <button
                                onClick={() => setDeleteConfirm({ symbol: asset.symbol })}
                                disabled={!!deleting || !!reingesting}
                                className="px-2.5 py-1 text-xs rounded bg-red-500/10 text-red-400 border border-red-500/30 hover:bg-red-500/20 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                              >
                                {deleting === asset.symbol ? 'Deleting…' : 'Delete'}
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {totalPages > 1 && (
                  <div className="mt-4 flex items-center justify-between text-sm text-slate-400">
                    <span>
                      Page {currentPage} of {totalPages} &middot; {assets.length} stocks
                    </span>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                        disabled={currentPage === 1}
                        className="px-3 py-1 rounded border border-slate-700 hover:border-slate-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                      >
                        Previous
                      </button>
                      <button
                        onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                        disabled={currentPage === totalPages}
                        className="px-3 py-1 rounded border border-slate-700 hover:border-slate-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          {status && status.scheduled_jobs.length > 0 && (
            <div className="card">
              <h2 className="text-slate-200 font-semibold mb-3">Scheduled Jobs</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-slate-500 border-b border-slate-700">
                      <th className="text-left pb-2 font-medium">Job ID</th>
                      <th className="text-left pb-2 font-medium">Name</th>
                      <th className="text-left pb-2 font-medium">Next Run</th>
                    </tr>
                  </thead>
                  <tbody>
                    {status.scheduled_jobs.map((job) => (
                      <tr key={job.id} className="border-b border-slate-800 text-slate-300">
                        <td className="py-2 font-mono text-xs text-slate-400">{job.id}</td>
                        <td className="py-2">{job.name}</td>
                        <td className="py-2 font-mono text-xs">{job.next_run ?? 'N/A'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="card max-w-sm w-full mx-4 space-y-4">
            <h3 className="text-slate-100 font-semibold text-base">Delete {deleteConfirm.symbol}?</h3>
            <p className="text-slate-400 text-sm">
              This will permanently delete <span className="text-slate-200 font-mono">{deleteConfirm.symbol}</span> and all its historical price data. This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="px-4 py-1.5 text-sm rounded border border-slate-600 text-slate-300 hover:border-slate-400 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteConfirmed}
                className="px-4 py-1.5 text-sm rounded bg-red-600 text-white hover:bg-red-500 transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
