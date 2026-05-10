import { useEffect, useState } from 'react';
import { dataApi } from '../api/endpoints';
import type { IngestionStatusResponse, IngestResponse } from '../api/types';
import MetricCard from '../components/MetricCard';
import StatusBadge from '../components/StatusBadge';
import Spinner from '../components/Spinner';
import ErrorAlert from '../components/ErrorAlert';
import TickerSearch from '../components/TickerSearch';

const DEFAULT_SYMBOLS = ['AAPL', 'MSFT', 'SPY', 'QQQ'];
const DEFAULT_TIMEFRAMES = ['1d', '1h'];

export default function Dashboard() {
  const [status, setStatus] = useState<IngestionStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ingestResult, setIngestResult] = useState<IngestResponse | null>(null);
  const [ingesting, setIngesting] = useState(false);
  const [symbols, setSymbols] = useState<string[]>(DEFAULT_SYMBOLS);

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

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30_000);
    return () => clearInterval(interval);
  }, []);

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
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIngesting(false);
    }
  };

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
    </div>
  );
}
