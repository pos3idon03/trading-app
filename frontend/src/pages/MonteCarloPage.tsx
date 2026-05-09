import { useEffect, useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { dataApi, simulationApi } from '../api/endpoints';
import type { AssetItem, SimulationResponse } from '../api/types';
import MetricCard from '../components/MetricCard';
import StatusBadge from '../components/StatusBadge';
import Spinner from '../components/Spinner';
import ErrorAlert from '../components/ErrorAlert';

const PERCENTILE_COLORS: Record<string, string> = {
  '5': '#ef4444',
  '25': '#f97316',
  '50': '#22c55e',
  '75': '#3b82f6',
  '95': '#a855f7',
};

function buildChartData(paths: Record<string, number[]>): Record<string, number>[] {
  const len = paths['50']?.length ?? 0;
  return Array.from({ length: len }, (_, i) => {
    const point: Record<string, number> = { step: i };
    for (const [pct, values] of Object.entries(paths)) {
      point[`p${pct}`] = Number(values[i]?.toFixed(4));
    }
    return point;
  });
}

export default function MonteCarloPage() {
  const [assets, setAssets] = useState<AssetItem[]>([]);
  const [symbol, setSymbol] = useState('');
  const [numPaths, setNumPaths] = useState(1000);
  const [horizonSteps, setHorizonSteps] = useState(252);
  const [result, setResult] = useState<SimulationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    dataApi.getAssets().then((resp) => {
      const active = resp.assets.filter((a) => a.is_active);
      setAssets(active);
      if (active.length > 0) setSymbol(active[0].symbol);
    });
  }, []);

  const runSimulation = async () => {
    if (!symbol) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await simulationApi.run({
        symbol,
        timeframe: '1d',
        num_paths: numPaths,
        horizon_steps: horizonSteps,
        use_stored_params: true,
      });
      setResult(resp);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const chartData = result?.percentile_paths ? buildChartData(result.percentile_paths) : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Monte Carlo Simulation</h1>
        <p className="text-slate-400 text-sm mt-1">
          Vasicek + Jump Diffusion model &mdash; simulate future price paths
        </p>
      </div>

      {error && <ErrorAlert message={error} />}

      <div className="card">
        <h2 className="text-slate-200 font-semibold mb-4">Configuration</h2>
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="metric-label block mb-1">Ticker</label>
            <select
              className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              disabled={assets.length === 0}
            >
              {assets.length === 0 && <option value="">Loading…</option>}
              {assets.map((a) => (
                <option key={a.id} value={a.symbol}>
                  {a.symbol}{a.name ? ` — ${a.name}` : ''}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="metric-label block mb-1">Paths</label>
            <select
              className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
              value={numPaths}
              onChange={(e) => setNumPaths(Number(e.target.value))}
            >
              {[100, 500, 1000, 5000, 10000].map((v) => (
                <option key={v} value={v}>{v.toLocaleString()}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="metric-label block mb-1">Horizon (trading days)</label>
            <select
              className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
              value={horizonSteps}
              onChange={(e) => setHorizonSteps(Number(e.target.value))}
            >
              {[21, 63, 126, 252, 504].map((v) => (
                <option key={v} value={v}>{v} days</option>
              ))}
            </select>
          </div>
          <button
            onClick={runSimulation}
            disabled={loading || !symbol}
            className="btn-primary disabled:opacity-50"
          >
            {loading ? 'Simulating…' : 'Run Simulation'}
          </button>
        </div>
      </div>

      {loading && <Spinner label="Running Monte Carlo simulation…" />}

      {result && !loading && (
        <>
          <div className="flex items-center gap-3">
            <StatusBadge status={result.status} />
            <span className="text-slate-400 text-sm">
              Sim ID #{result.simulation_id} &bull; {result.duration_ms}ms
            </span>
          </div>

          {result.stats && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <MetricCard label="Median Terminal" value={result.stats.p50.toFixed(4)} />
              <MetricCard
                label="Prob. Positive Return"
                value={`${(result.stats.prob_positive_return * 100).toFixed(1)}%`}
                positive={result.stats.prob_positive_return > 0.5}
                negative={result.stats.prob_positive_return < 0.5}
              />
              <MetricCard
                label="Mean Max Drawdown"
                value={`${(result.stats.mean_max_drawdown * 100).toFixed(1)}%`}
                negative
              />
              <MetricCard label="Std Dev (terminal)" value={result.stats.std_terminal.toFixed(4)} />
            </div>
          )}

          {chartData.length > 0 && (
            <div className="card">
              <h2 className="text-slate-200 font-semibold mb-4">Path Percentile Fan Chart</h2>
              <ResponsiveContainer width="100%" height={380}>
                <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                  <XAxis
                    dataKey="step"
                    stroke="#475569"
                    tick={{ fontSize: 11, fill: '#64748b' }}
                    label={{ value: 'Trading Days', position: 'insideBottom', offset: -2, fill: '#64748b', fontSize: 11 }}
                  />
                  <YAxis stroke="#475569" tick={{ fontSize: 11, fill: '#64748b' }} />
                  <Tooltip
                    contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                    labelStyle={{ color: '#94a3b8' }}
                  />
                  <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
                  {Object.entries(PERCENTILE_COLORS).map(([pct, color]) => (
                    <Line
                      key={pct}
                      type="monotone"
                      dataKey={`p${pct}`}
                      stroke={color}
                      strokeWidth={pct === '50' ? 2.5 : 1}
                      dot={false}
                      name={`P${pct}`}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}
    </div>
  );
}
