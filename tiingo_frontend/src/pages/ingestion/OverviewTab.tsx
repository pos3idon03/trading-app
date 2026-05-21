import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ingestionApi } from '../../api/endpoints';
import type { IngestionStatus, Job } from '../../api/types';
import Spinner from '../../components/Spinner';
import ErrorAlert from '../../components/ErrorAlert';

export default function OverviewTab() {
  const [status, setStatus] = useState<IngestionStatus | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const [s, j] = await Promise.all([ingestionApi.getStatus(), ingestionApi.listJobs()]);
      setStatus(s);
      setJobs(j.slice(0, 10));
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 30_000);
    return () => clearInterval(t);
  }, []);

  if (loading) return <div className="flex justify-center py-12"><Spinner /></div>;
  if (error) return <ErrorAlert message={error} />;

  const usage = status?.api_usage ?? {};

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Metric label="Watchlist" value={String(status?.instrument_count ?? 0)} />
        <Metric label="Active" value={String(status?.active_instrument_count ?? 0)} />
        <Metric label="Hourly API" value={`${usage.hourly_requests ?? 0} / ${usage.hourly_limit ?? 0}`} />
        <Metric label="Daily API" value={`${usage.daily_requests ?? 0} / ${usage.daily_limit ?? 0}`} />
      </div>

      <section className="bg-surface-900 border border-slate-800 rounded-xl p-4">
        <h3 className="font-semibold text-slate-200 mb-3">Live Stream</h3>
        <p className="text-sm text-slate-400">
          {status?.stream_status?.running ? 'Running' : 'Stopped'} —{' '}
          {(status?.stream_status?.symbols ?? []).join(', ') || 'no symbols'}
        </p>
      </section>

      <section className="bg-surface-900 border border-slate-800 rounded-xl p-4">
        <h3 className="font-semibold text-slate-200 mb-3">Scheduled Jobs</h3>
        <ul className="text-sm text-slate-400 space-y-1">
          {(status?.scheduler_jobs ?? []).map((j) => (
            <li key={j.id}>
              <span className="text-slate-300">{j.id}</span>
              {j.next_run && <span className="ml-2">next: {new Date(j.next_run).toLocaleString()}</span>}
            </li>
          ))}
        </ul>
      </section>

      <section className="bg-surface-900 border border-slate-800 rounded-xl p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-slate-200">Recent Jobs</h3>
          <Link to="/ingestion/jobs" className="text-sm text-brand-500 hover:text-brand-400">
            View all jobs
          </Link>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-slate-500 text-left">
              <th className="pb-2">Type</th>
              <th>Status</th>
              <th>Progress</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((j) => (
              <tr key={j.id} className="border-t border-slate-800">
                <td className="py-2 text-slate-300">{j.job_type}</td>
                <td className={j.status === 'completed' ? 'text-brand-500' : 'text-amber-400'}>{j.status}</td>
                <td className="text-slate-500">{j.progress}%</td>
                <td className="text-slate-500">{new Date(j.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-surface-900 border border-slate-800 rounded-xl p-4">
      <p className="text-xs text-slate-500 uppercase">{label}</p>
      <p className="text-xl font-bold text-slate-100 mt-1">{value}</p>
    </div>
  );
}
