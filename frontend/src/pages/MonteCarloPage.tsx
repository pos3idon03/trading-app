import React, { useEffect, useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ComposedChart,
  Bar,
} from 'recharts';
import { dataApi, simulationApi } from '../api/endpoints';
import type { AssetItem, SimulationResponse, DistributionPoint } from '../api/types';
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

function buildDistributionData(
  histogram: DistributionPoint[],
  mrDensity: DistributionPoint[],
  jumpUp: DistributionPoint[],
  jumpDown: DistributionPoint[],
): Record<string, number | null>[] {
  // Merge all series onto a shared x-axis derived from histogram midpoints
  const mrMap = new Map(mrDensity.map((p) => [p.x.toFixed(6), p.density]));
  const upMap = new Map(jumpUp.map((p) => [p.x.toFixed(6), p.density]));
  const downMap = new Map(jumpDown.map((p) => [p.x.toFixed(6), p.density]));

  return histogram.map((p) => {
    const key = p.x.toFixed(6);
    return {
      x: Number(p.x.toFixed(4)),
      histogram: Number(p.density.toFixed(4)),
      mr: mrMap.has(key) ? Number(mrMap.get(key)!.toFixed(4)) : null,
      jumpUp: upMap.has(key) ? Number(upMap.get(key)!.toFixed(4)) : null,
      jumpDown: downMap.has(key) ? Number(downMap.get(key)!.toFixed(4)) : null,
    };
  });
}

export default function MonteCarloPage() {
  const [assets, setAssets] = useState<AssetItem[]>([]);
  const [symbol, setSymbol] = useState('');
  const [numPaths, setNumPaths] = useState(1000);
  const [horizonSteps, setHorizonSteps] = useState(252);
  const [calibrationYears, setCalibrationYears] = useState(10);
  const [modelType, setModelType] = useState<'vasicek' | 'merton'>('merton');
  const [showDistribution, setShowDistribution] = useState(false);
  const [result, setResult] = useState<SimulationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    dataApi.getAssets().then((resp: { assets: AssetItem[] }) => {
      const active = resp.assets.filter((a: AssetItem) => a.is_active);
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
        include_distribution: showDistribution,
        calibration_years: calibrationYears,
        model_type: modelType,
      });
      setResult(resp);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const chartData = result?.percentile_paths ? buildChartData(result.percentile_paths) : [];

  const distData =
    result?.return_distribution
      ? buildDistributionData(
          result.return_distribution.histogram,
          result.return_distribution.mr_density,
          result.return_distribution.jump_up_density,
          result.return_distribution.jump_down_density,
        )
      : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Monte Carlo Simulation</h1>
        <p className="text-slate-400 text-sm mt-1">
          {modelType === 'merton'
            ? 'Merton Jump-Diffusion (GBM + jumps) — equity-style trending paths'
            : 'Vasicek + Jump Diffusion (mean-reverting) — spreads & rates'}
        </p>
      </div>

      {error && <ErrorAlert message={error} />}

      <div className="card">
        <h2 className="text-slate-200 font-semibold mb-4">Configuration</h2>
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="metric-label block mb-1">Model</label>
            <select
              className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
              value={modelType}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
                setModelType(e.target.value as 'vasicek' | 'merton')
              }
            >
              <option value="merton">Merton Jump-Diffusion</option>
              <option value="vasicek">Vasicek + Jump</option>
            </select>
          </div>
          <div>
            <label className="metric-label block mb-1">Ticker</label>
            <select
              className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
              value={symbol}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSymbol(e.target.value)}
              disabled={assets.length === 0}
            >
              {assets.length === 0 && <option value="">Loading…</option>}
              {assets.map((a: AssetItem) => (
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
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setNumPaths(Number(e.target.value))}
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
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setHorizonSteps(Number(e.target.value))}
            >
              {[21, 63, 126, 252, 504].map((v) => (
                <option key={v} value={v}>{v} days</option>
              ))}
            </select>
          </div>
          <div>
            <label className="metric-label block mb-1">Calibration Window</label>
            <select
              className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
              value={calibrationYears}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setCalibrationYears(Number(e.target.value))}
            >
              {[1, 2, 3, 5, 7, 10, 15, 20].map((v) => (
                <option key={v} value={v}>{v} {v === 1 ? 'year' : 'years'}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2 pb-1">
            <input
              id="show-dist"
              type="checkbox"
              className="accent-brand-500 w-4 h-4 cursor-pointer"
              checked={showDistribution}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setShowDistribution(e.target.checked)}
            />
            <label htmlFor="show-dist" className="metric-label cursor-pointer select-none">
              Return Distribution
            </label>
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
          <div className="flex items-center gap-3 flex-wrap">
            <StatusBadge status={result.status} />
            <span className="text-slate-400 text-sm">
              Sim ID #{result.simulation_id} &bull; {result.duration_ms}ms
            </span>
            {result.params?.calibration_start && result.params?.calibration_end && (
              <span className="text-slate-500 text-xs">
                Calibrated on {String(result.params.calibration_start).slice(0, 10)}
                &nbsp;&rarr;&nbsp;
                {String(result.params.calibration_end).slice(0, 10)}
                &nbsp;({result.params.num_observations as number} bars)
              </span>
            )}
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

          {distData.length > 0 && (
            <div className="card">
              <h2 className="text-slate-200 font-semibold mb-1">Log-Return Distribution</h2>
              <p className="text-slate-400 text-xs mb-4">
                Histogram of simulated log-returns decomposed into mean-reverting, negative-jump and positive-jump components.
              </p>
              <ResponsiveContainer width="100%" height={380}>
                <ComposedChart data={distData} margin={{ top: 5, right: 20, bottom: 20, left: 0 }}>
                  <XAxis
                    dataKey="x"
                    stroke="#475569"
                    tick={{ fontSize: 11, fill: '#64748b' }}
                    label={{ value: 'Log-return', position: 'insideBottom', offset: -10, fill: '#64748b', fontSize: 11 }}
                    tickFormatter={(v: number | string) => Number(v).toFixed(3)}
                  />
                  <YAxis stroke="#475569" tick={{ fontSize: 11, fill: '#64748b' }} />
                  <Tooltip
                    contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                    labelStyle={{ color: '#94a3b8' }}
                    formatter={(v: number | string) => Number(v).toFixed(4)}
                  />
                  <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
                  <Bar dataKey="histogram" name="Historical log-returns" fill="#3b82f6" fillOpacity={0.5} />
                  <Line type="monotone" dataKey="mr" name={modelType === 'merton' ? 'GBM diffusion component' : 'Mean-reverting process'} stroke="#ef4444" strokeWidth={2} dot={false} connectNulls />
                  <Line type="monotone" dataKey="jumpDown" name="Negative jumps dist." stroke="#22c55e" strokeWidth={1.5} dot={false} connectNulls />
                  <Line type="monotone" dataKey="jumpUp" name="Positive jumps dist." stroke="#d946ef" strokeWidth={1.5} dot={false} connectNulls />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}
    </div>
  );
}
