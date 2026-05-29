import { useCallback, useEffect, useState } from 'react';
import { ingestionApi } from '../../api/endpoints';
import type { Job } from '../../api/types';
import Spinner from '../../components/Spinner';
import ErrorAlert from '../../components/ErrorAlert';
import { formatRedactedJobJson, redactSecretsInText } from '../../utils/redactSecrets';

type StatusFilter = 'all' | 'running' | 'failed';

function jobLabel(job: Job): string {
  const params = job.params as Record<string, unknown> | undefined;
  if (params?.symbol) return String(params.symbol);
  const symbols = params?.symbols as string[] | undefined;
  if (symbols?.length) return symbols.join(', ');
  const series = params?.series_ids as string[] | undefined;
  if (series?.length) return series.join(', ');
  return '—';
}

function statusColor(status: string): string {
  if (status === 'completed') return 'text-brand-500';
  if (status === 'running' || status === 'pending') return 'text-amber-400';
  if (status === 'cancelled') return 'text-slate-400';
  if (status === 'partial') return 'text-orange-400';
  return 'text-red-400';
}

function isCancellable(status: string): boolean {
  return status === 'pending' || status === 'running';
}

export default function JobsTab() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [filter, setFilter] = useState<StatusFilter>('all');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cancellingId, setCancellingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      let data: Job[];
      if (filter === 'running') {
        data = await ingestionApi.listActiveJobs();
      } else if (filter === 'failed') {
        data = await ingestionApi.listJobs({ status: 'failed', limit: 100 });
        const partial = await ingestionApi.listJobs({ status: 'partial', limit: 100 });
        data = [...data, ...partial];
      } else {
        data = await ingestionApi.listJobs({ limit: 100 });
      }
      setJobs(data);
      setError(null);
      return data;
    } catch (e) {
      setError((e as Error).message);
      return [];
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  useEffect(() => {
    const hasActive = jobs.some((j) => j.status === 'pending' || j.status === 'running');
    const ms = hasActive ? 3_000 : 30_000;
    const timer = setInterval(() => {
      load();
    }, ms);
    return () => clearInterval(timer);
  }, [load, jobs]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    ingestionApi.getJob(selectedId).then(setDetail).catch((e) => setError((e as Error).message));
  }, [selectedId]);

  const handleCancel = async (jobId: string) => {
    setCancellingId(jobId);
    setError(null);
    try {
      const updated = await ingestionApi.cancelJob(jobId);
      setJobs((prev) => prev.map((j) => (j.id === jobId ? updated : j)));
      if (selectedId === jobId) {
        setDetail(updated);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setCancellingId(null);
    }
  };

  if (loading && jobs.length === 0) {
    return (
      <div className="flex justify-center py-12">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {error && <ErrorAlert message={error} />}
      <p className="text-xs text-slate-500">
        Background ingestion jobs run in the ARQ worker. Polls every 3s while jobs are active.
      </p>

      <div className="flex flex-wrap gap-2">
        {(['all', 'running', 'failed'] as const).map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-lg text-sm ${
              filter === f
                ? 'bg-brand-600 text-white'
                : 'bg-surface-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            {f === 'all' ? 'All' : f === 'running' ? 'Running' : 'Failed / Partial'}
          </button>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <section className="bg-surface-900 border border-slate-800 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-surface-800 text-slate-400">
              <tr>
                <th className="text-left p-3">Type</th>
                <th className="text-left p-3">Target</th>
                <th className="text-left p-3">Status</th>
                <th className="text-left p-3 min-w-[100px]">Progress</th>
                <th className="text-right p-3 w-24">Actions</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => (
                <tr
                  key={j.id}
                  className={`border-t border-slate-800 cursor-pointer hover:bg-surface-800/50 ${
                    selectedId === j.id ? 'bg-surface-800/80' : ''
                  }`}
                  onClick={() => setSelectedId(j.id)}
                >
                  <td className="p-3 text-slate-300">{j.job_type}</td>
                  <td className="p-3 text-slate-400 font-mono text-xs">{jobLabel(j)}</td>
                  <td className={`p-3 ${statusColor(j.status)}`}>{j.status}</td>
                  <td className="p-3">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-brand-500 transition-all"
                          style={{ width: `${j.progress}%` }}
                        />
                      </div>
                      <span className="text-xs text-slate-500 w-8">{j.progress}%</span>
                    </div>
                  </td>
                  <td className="p-3 text-right">
                    {isCancellable(j.status) ? (
                      <button
                        type="button"
                        disabled={cancellingId === j.id}
                        onClick={(e) => {
                          e.stopPropagation();
                          void handleCancel(j.id);
                        }}
                        className="px-2 py-1 rounded text-xs text-red-300 hover:text-red-200 hover:bg-red-950/40 disabled:opacity-50"
                      >
                        {cancellingId === j.id ? 'Stopping…' : 'Stop'}
                      </button>
                    ) : (
                      <span className="text-xs text-slate-600">—</span>
                    )}
                  </td>
                </tr>
              ))}
              {jobs.length === 0 && (
                <tr>
                  <td colSpan={5} className="p-6 text-center text-slate-500">
                    No jobs found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </section>

        <section className="bg-surface-900 border border-slate-800 rounded-xl p-4 min-h-[200px]">
          <h3 className="font-semibold text-slate-200 mb-3">Job detail</h3>
          {!detail ? (
            <p className="text-sm text-slate-500">Select a job to view details.</p>
          ) : (
            <div className="space-y-3 text-sm">
              <div className="flex items-start justify-between gap-3">
                <p>
                  <span className="text-slate-500">ID:</span>{' '}
                  <span className="font-mono text-xs text-slate-300">{detail.id}</span>
                </p>
                {isCancellable(detail.status) && (
                  <button
                    type="button"
                    disabled={cancellingId === detail.id}
                    onClick={() => void handleCancel(detail.id)}
                    className="shrink-0 px-3 py-1.5 rounded-lg text-xs bg-red-950/50 text-red-300 hover:bg-red-950/80 disabled:opacity-50"
                  >
                    {cancellingId === detail.id ? 'Stopping…' : 'Stop job'}
                  </button>
                )}
              </div>
              <p>
                <span className="text-slate-500">Created:</span>{' '}
                {new Date(detail.created_at).toLocaleString()}
              </p>
              {detail.started_at && (
                <p>
                  <span className="text-slate-500">Started:</span>{' '}
                  {new Date(detail.started_at).toLocaleString()}
                </p>
              )}
              {detail.finished_at && (
                <p>
                  <span className="text-slate-500">Finished:</span>{' '}
                  {new Date(detail.finished_at).toLocaleString()}
                </p>
              )}
              {detail.error_message && (
                <p className="text-red-400 break-words">
                  {redactSecretsInText(detail.error_message)}
                </p>
              )}
              {detail.params && (
                <div>
                  <p className="text-slate-500 mb-1">Params</p>
                  <pre className="text-xs leading-4 bg-surface-800 p-2 rounded overflow-auto max-h-[21rem]">
                    {JSON.stringify(detail.params, null, 2)}
                  </pre>
                </div>
              )}
              {detail.result && (
                <div>
                  <p className="text-slate-500 mb-1">Result</p>
                  <pre className="text-xs bg-surface-800 p-2 rounded overflow-auto max-h-48">
                    {formatRedactedJobJson(detail.result)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
