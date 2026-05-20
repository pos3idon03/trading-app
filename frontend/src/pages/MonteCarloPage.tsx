import React, { useCallback, useEffect, useState } from 'react';
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
import type {
  AssetItem,
  BacktestMetrics,
  ChartOverlayTradeEntry,
  ComboStrategySignal,
  DistributionPoint,
  McBacktestResponse,
  McBacktestPreset,
  McBacktestTimeframe,
  McModelType,
  SimulationResponse,
} from '../api/types';
import MetricCard from '../components/MetricCard';
import MetricQualityBar from '../components/MetricQualityBar';
import StatusBadge from '../components/StatusBadge';
import Spinner from '../components/Spinner';
import ErrorAlert from '../components/ErrorAlert';
import BacktestEquityCurve from '../components/BacktestEquityCurve';
import McProbPositiveChart from '../components/McProbPositiveChart';
import McBacktestProbSuggestions from '../components/McBacktestProbSuggestions';
import McBacktestComboSection, {
  comboConfigToRequestPayload,
  DEFAULT_MC_COMBO_CONFIG,
  type McComboConfig,
  validateMcComboConfig,
} from '../components/McBacktestComboSection';
import { ComboSignalTimeline } from '../components/ComboSignalTimeline';
import OverlayTradeTable from '../components/OverlayTradeTable';
import MonteCarloBacktestOptimizeTab from '../components/MonteCarloBacktestOptimizeTab';
import { formatAssetOptionLabel } from '../utils/assetDisplay';
import { fmt, fmtPct } from '../utils/formatting';
import {
  defaultCalibrationDaysForTimeframe,
  defaultDatesForTimeframe,
  INTRADAY_CALIBRATION_DAY_OPTIONS,
  INTRADAY_MAX_LOOKBACK_DAYS,
  isIntradayTimeframe,
} from '../utils/backtestDates';
import { MC_MODEL_OPTIONS } from '../constants/monteCarlo';

type TabId = 'simulation' | 'backtest' | 'optimize';

const PERCENTILE_COLORS: Record<string, string> = {
  '5': '#ef4444',
  '25': '#f97316',
  '50': '#22c55e',
  '75': '#3b82f6',
  '95': '#a855f7',
};

const TIMEFRAME_OPTIONS: { value: McBacktestTimeframe; label: string }[] = [
  { value: '5m', label: '5 Min' },
  { value: '15m', label: '15 Min' },
  { value: '30m', label: '30 Min' },
  { value: '1h', label: '1 Hour' },
  { value: '4h', label: '4 Hours' },
  { value: '1d', label: 'Daily' },
  { value: '1w', label: 'Weekly' },
];

const SELECT_CLS =
  'bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500';

function useAssets() {
  const [assets, setAssets] = useState<AssetItem[]>([]);
  useEffect(() => {
    dataApi.getAssets().then((resp) => {
      setAssets(resp.assets.filter((a) => a.is_active));
    });
  }, []);
  return assets;
}

function TabBar({ active, onChange }: { active: TabId; onChange: (t: TabId) => void }) {
  const cls = (t: TabId) =>
    `px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
      active === t
        ? 'bg-surface-800 text-slate-100 border-b-2 border-brand-500'
        : 'text-slate-400 hover:text-slate-200'
    }`;
  return (
    <div className="flex gap-1 border-b border-slate-700">
      <button type="button" className={cls('simulation')} onClick={() => onChange('simulation')}>
        Simulation
      </button>
      <button type="button" className={cls('backtest')} onClick={() => onChange('backtest')}>
        Backtest
      </button>
      <button type="button" className={cls('optimize')} onClick={() => onChange('optimize')}>
        Optimize
      </button>
    </div>
  );
}

function TickerSelect({
  assets,
  value,
  onChange,
}: {
  assets: AssetItem[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label className="metric-label block mb-1">Ticker</label>
      <select className={SELECT_CLS} value={value} onChange={(e) => onChange(e.target.value)} disabled={assets.length === 0}>
        {assets.length === 0 && <option value="">Loading…</option>}
        {assets.map((a) => (
          <option key={a.id} value={a.symbol}>
            {formatAssetOptionLabel(a)}
          </option>
        ))}
      </select>
    </div>
  );
}

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

function McBacktestMetricsGrid({ metrics }: { metrics: BacktestMetrics }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      <MetricCard
        label="Total Return"
        value={fmtPct(metrics.total_return)}
        positive={(metrics.total_return ?? 0) > 0}
        negative={(metrics.total_return ?? 0) < 0}
      />
      <MetricQualityBar label="Sharpe Ratio" value={metrics.sharpe_ratio} formattedValue={fmt(metrics.sharpe_ratio, 3)} kind="sharpe" />
      <MetricQualityBar label="Sortino Ratio" value={metrics.sortino_ratio} formattedValue={fmt(metrics.sortino_ratio, 3)} kind="sortino" />
      <MetricCard label="Max Drawdown" value={fmtPct(metrics.max_drawdown)} negative />
      <MetricCard
        label="Win Rate"
        value={fmtPct(metrics.win_rate)}
        positive={(metrics.win_rate ?? 0) > 0.5}
      />
      <MetricQualityBar
        label="Profit Factor"
        value={metrics.profit_factor}
        formattedValue={fmt(metrics.profit_factor, 2)}
        kind="profit_factor"
      />
      <MetricCard label="# Trades" value={metrics.num_trades ?? '—'} />
    </div>
  );
}

function MonteCarloSimulationTab({ assets }: { assets: AssetItem[] }) {
  const [symbol, setSymbol] = useState('');
  const [numPaths, setNumPaths] = useState(1000);
  const [horizonSteps, setHorizonSteps] = useState(252);
  const [calibrationYears, setCalibrationYears] = useState(10);
  const [modelType, setModelType] = useState<McModelType>('merton');
  const [showDistribution, setShowDistribution] = useState(false);
  const [result, setResult] = useState<SimulationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (assets.length > 0 && !symbol) setSymbol(assets[0].symbol);
  }, [assets, symbol]);

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
      {error && <ErrorAlert message={error} />}

      <div className="card">
        <h2 className="text-slate-200 font-semibold mb-4">Configuration</h2>
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="metric-label block mb-1">Model</label>
            <select
              className={SELECT_CLS}
              value={modelType}
              onChange={(e) => setModelType(e.target.value as McModelType)}
            >
              {MC_MODEL_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          {modelType === 'blended' && (
            <p className="text-slate-500 text-xs w-full mb-2">
              Blended stats weight Merton (trend) and OU deviation (reversion) by ADX.
              Percentile paths show Merton only.
            </p>
          )}
          <TickerSelect assets={assets} value={symbol} onChange={setSymbol} />
          <div>
            <label className="metric-label block mb-1">Paths</label>
            <select className={SELECT_CLS} value={numPaths} onChange={(e) => setNumPaths(Number(e.target.value))}>
              {[100, 500, 1000, 5000, 10000].map((v) => (
                <option key={v} value={v}>{v.toLocaleString()}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="metric-label block mb-1">Horizon (trading days)</label>
            <select className={SELECT_CLS} value={horizonSteps} onChange={(e) => setHorizonSteps(Number(e.target.value))}>
              {[21, 63, 126, 252, 504].map((v) => (
                <option key={v} value={v}>{v} days</option>
              ))}
            </select>
          </div>
          <div>
            <label className="metric-label block mb-1">Calibration Window</label>
            <select className={SELECT_CLS} value={calibrationYears} onChange={(e) => setCalibrationYears(Number(e.target.value))}>
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
              onChange={(e) => setShowDistribution(e.target.checked)}
            />
            <label htmlFor="show-dist" className="metric-label cursor-pointer select-none">
              Return Distribution
            </label>
          </div>
          <button onClick={runSimulation} disabled={loading || !symbol} className="btn-primary disabled:opacity-50">
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

function MonteCarloBacktestTab({
  assets,
  preset,
  onPresetApplied,
}: {
  assets: AssetItem[];
  preset: McBacktestPreset | null;
  onPresetApplied: () => void;
}) {
  const dailyDefaults = defaultDatesForTimeframe('1d');
  const [symbol, setSymbol] = useState('');
  const [startDate, setStartDate] = useState(dailyDefaults.start);
  const [endDate, setEndDate] = useState(dailyDefaults.end);
  const [timeframe, setTimeframe] = useState<McBacktestTimeframe>('1d');
  const [modelType, setModelType] = useState<McModelType>('merton');
  const [calibrationYears, setCalibrationYears] = useState(10);
  const [calibrationDays, setCalibrationDays] = useState(30);
  const [numPaths, setNumPaths] = useState(500);
  const [buyPct, setBuyPct] = useState('65');
  const [sellPct, setSellPct] = useState('40');
  const [probSmoothingBars, setProbSmoothingBars] = useState(0);
  const [entryConfirmationBars, setEntryConfirmationBars] = useState(1);
  const [minHoldBars, setMinHoldBars] = useState(0);
  const [cooldownBars, setCooldownBars] = useState(0);
  const [ouMaWindow, setOuMaWindow] = useState(20);
  const [adxPeriod, setAdxPeriod] = useState(14);
  const [adxTrendThreshold, setAdxTrendThreshold] = useState(25);
  const [regimeTimeframe, setRegimeTimeframe] = useState<McBacktestTimeframe | ''>('');
  const [structureTimeframe, setStructureTimeframe] = useState<McBacktestTimeframe | ''>('');
  const [mtfGateEnabled, setMtfGateEnabled] = useState(true);
  const [regimeMinTrendWeight, setRegimeMinTrendWeight] = useState(30);
  const [thresholdMode, setThresholdMode] = useState<'static' | 'ml_dynamic' | 'suggested_percentile'>('static');
  const [regimeMode, setRegimeMode] = useState<'adx' | 'ml'>('adx');
  const [useSurrogate, setUseSurrogate] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [comboConfig, setComboConfig] = useState<McComboConfig>(DEFAULT_MC_COMBO_CONFIG);
  const [result, setResult] = useState<McBacktestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastThresholds, setLastThresholds] = useState({ buy: 0.65, sell: 0.4 });

  useEffect(() => {
    if (assets.length > 0 && !symbol) setSymbol(assets[0].symbol);
  }, [assets, symbol]);

  useEffect(() => {
    if (!preset) return;
    setSymbol(preset.symbol);
    setModelType(preset.modelType);
    setTimeframe(preset.timeframe);
    setStartDate(preset.startDate);
    setEndDate(preset.endDate);
    setCalibrationYears(preset.calibrationYears);
    setCalibrationDays(
      preset.calibrationDays ??
        (isIntradayTimeframe(preset.timeframe)
          ? defaultCalibrationDaysForTimeframe(preset.timeframe)
          : 30),
    );
    setNumPaths(preset.numPaths);
    setBuyPct(preset.buyPct);
    setSellPct(preset.sellPct);
    setProbSmoothingBars(preset.probSmoothingBars ?? 0);
    setEntryConfirmationBars(preset.entryConfirmationBars ?? 1);
    setMinHoldBars(preset.minHoldBars ?? 0);
    setCooldownBars(preset.cooldownBars ?? 0);
    setOuMaWindow(preset.ouMaWindow ?? 20);
    setAdxPeriod(preset.adxPeriod ?? 14);
    setAdxTrendThreshold(preset.adxTrendThreshold ?? 25);
    if (preset.comboEnabled) {
      setComboConfig({
        enabled: true,
        mode: preset.combinationMode ?? 'and',
        threshold: preset.comboThreshold ?? 0.5,
        mcLegWeight: preset.mcLegWeight ?? 1.0,
        entries: (preset.algoStrategies ?? []).map((s) => ({
          id: `${s.strategy_name}-${Math.random().toString(36).slice(2, 7)}`,
          strategy_name: s.strategy_name,
          weight: s.weight ?? 1.0,
          timeframe: (s.timeframe ?? preset.timeframe) as McBacktestTimeframe,
        })),
        paramsMap: Object.fromEntries(
          (preset.algoStrategies ?? []).map((s) => [s.strategy_name, s.strategy_params ?? {}]),
        ),
      });
    } else {
      setComboConfig(DEFAULT_MC_COMBO_CONFIG);
    }
    onPresetApplied();
  }, [preset, onPresetApplied]);

  const handleTimeframeChange = (tf: McBacktestTimeframe) => {
    setTimeframe(tf);
    const dates = defaultDatesForTimeframe(tf);
    setStartDate(dates.start);
    setEndDate(dates.end);
    if (isIntradayTimeframe(tf)) {
      setCalibrationDays(defaultCalibrationDaysForTimeframe(tf));
    }
  };

  const parseThreshold = (raw: string): number | null => {
    const v = parseFloat(raw);
    if (Number.isNaN(v) || v < 0 || v > 100) return null;
    return v / 100;
  };

  const runBacktest = async () => {
    if (!symbol) return;
    const buy = parseThreshold(buyPct);
    const sell = parseThreshold(sellPct);
    if (buy === null || sell === null) {
      setError('Thresholds must be numbers between 0 and 100');
      return;
    }
    if (sell >= buy) {
      setError('Thresholds must satisfy: Sell < Buy');
      return;
    }
    const comboError = validateMcComboConfig(comboConfig);
    if (comboError) {
      setError(comboError);
      return;
    }

    setLoading(true);
    setError(null);
    setLastThresholds({ buy, sell });
    try {
      const resp = await simulationApi.runBacktest({
        symbol,
        timeframe,
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate).toISOString(),
        model_type: modelType,
        ...(isIntradayTimeframe(timeframe)
          ? { calibration_days: calibrationDays }
          : { calibration_years: calibrationYears }),
        num_paths: numPaths,
        buy_threshold: buy,
        sell_threshold: sell,
        initial_capital: 1000,
        prob_smoothing_bars: probSmoothingBars,
        entry_confirmation_bars: entryConfirmationBars,
        min_hold_bars: minHoldBars,
        cooldown_bars: cooldownBars,
        ou_ma_window: ouMaWindow,
        adx_period: adxPeriod,
        adx_trend_threshold: adxTrendThreshold,
        ...(regimeTimeframe
          ? {
              regime_timeframe: regimeTimeframe,
              mtf_gate_enabled: mtfGateEnabled,
              regime_min_trend_weight: regimeMinTrendWeight / 100,
            }
          : {}),
        ...(structureTimeframe ? { structure_timeframe: structureTimeframe } : {}),
        threshold_mode: thresholdMode,
        regime_mode: regimeMode,
        use_surrogate: useSurrogate,
        ...comboConfigToRequestPayload(comboConfig),
      });
      setResult(resp);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const applySuggestedThresholds = (buy: string, sell: string) => {
    setBuyPct(buy);
    setSellPct(sell);
  };

  const overlayTrades: ChartOverlayTradeEntry[] = (result?.trade_log ?? []).map((t) => ({
    entry_time: t.entry_time,
    exit_time: t.exit_time ?? null,
    direction: t.direction,
    entry_price: t.entry_price,
    exit_price: t.exit_price ?? null,
    pnl: t.pnl,
    return_pct: t.return_pct,
  }));

  const comboTimelineStrategies: ComboStrategySignal[] = [
    ...(result?.combo_signals ?? []),
    ...(result?.combined_signal_timeline?.length
      ? [{
          strategy_name: 'combo:combined',
          trade_log: [],
          indicator_series: [],
          equity_curve: [],
          signal_timeline: result.combined_signal_timeline,
        }]
      : []),
  ];

  return (
    <div className="space-y-6">
      {error && <ErrorAlert message={error} />}

      <div className="card">
        <h2 className="text-slate-200 font-semibold mb-4">Backtest Configuration</h2>
        <p className="text-slate-400 text-xs mb-4">
          Walk-forward MC: at each bar, recalibrate on the rolling window ending at that close,
          simulate one step ahead, and trade when prob. positive return crosses your thresholds.
          Starting capital: $1,000.
        </p>
        <p className="text-slate-500 text-xs mb-4">
          Entry % applies when flat (buy if prob ≥ entry). Exit % applies when long (sell if prob &lt; exit).
          Between exit and entry while flat = wait. While long, prob above exit = hold.
          {modelType === 'blended' && (
            <> Blended: ADX-weighted Merton (trend) + OU deviation (reversion). High ADX favors trend.</>
          )}
        </p>
        <div className="flex flex-wrap gap-4 items-end mb-4">
          <TickerSelect assets={assets} value={symbol} onChange={setSymbol} />
          <div>
            <label className="metric-label block mb-1">Start Date</label>
            <input type="date" className={SELECT_CLS} value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </div>
          <div>
            <label className="metric-label block mb-1">End Date</label>
            <input type="date" className={SELECT_CLS} value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </div>
          <div>
            <label className="metric-label block mb-1">Timeframe</label>
            <select className={SELECT_CLS} value={timeframe} onChange={(e) => handleTimeframeChange(e.target.value as McBacktestTimeframe)}>
              {TIMEFRAME_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="metric-label block mb-1">Model</label>
            <select className={SELECT_CLS} value={modelType} onChange={(e) => setModelType(e.target.value as McModelType)}>
              {MC_MODEL_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="metric-label block mb-1">Calibration Window</label>
            {isIntradayTimeframe(timeframe) ? (
              <select
                className={SELECT_CLS}
                value={calibrationDays}
                onChange={(e) => setCalibrationDays(Number(e.target.value))}
              >
                {INTRADAY_CALIBRATION_DAY_OPTIONS.map((v) => (
                  <option key={v} value={v}>{v} days</option>
                ))}
              </select>
            ) : (
              <select className={SELECT_CLS} value={calibrationYears} onChange={(e) => setCalibrationYears(Number(e.target.value))}>
                {[1, 2, 3, 5, 7, 10, 15, 20].map((v) => (
                  <option key={v} value={v}>{v} {v === 1 ? 'year' : 'years'}</option>
                ))}
              </select>
            )}
          </div>
          <div>
            <label className="metric-label block mb-1">Paths</label>
            <select className={SELECT_CLS} value={numPaths} onChange={(e) => setNumPaths(Number(e.target.value))}>
              {[100, 500, 1000].map((v) => (
                <option key={v} value={v}>{v.toLocaleString()}</option>
              ))}
            </select>
          </div>
        </div>
        {isIntradayTimeframe(timeframe) && (
          <p className="text-slate-500 text-xs mb-4">
            Intraday bars are resampled from stored 5m data (up to {INTRADAY_MAX_LOOKBACK_DAYS} days).
            Use a calibration window within that range.
          </p>
        )}
        <div className="flex flex-wrap gap-4 items-end mb-4">
          <div>
            <label className="metric-label block mb-1">Entry % (prob ≥)</label>
            <input type="number" min={0} max={100} className={`${SELECT_CLS} w-24`} value={buyPct} onChange={(e) => setBuyPct(e.target.value)} />
          </div>
          <div>
            <label className="metric-label block mb-1">Exit % (prob &lt;)</label>
            <input type="number" min={0} max={100} className={`${SELECT_CLS} w-24`} value={sellPct} onChange={(e) => setSellPct(e.target.value)} />
          </div>
          <button
            type="button"
            className="text-slate-400 text-xs underline mb-2"
            onClick={() => setShowAdvanced((v) => !v)}
          >
            {showAdvanced ? 'Hide entry timing filters' : 'Entry timing filters (smoothing, hold, cooldown)'}
          </button>
        </div>
        {showAdvanced && (
          <div className="flex flex-wrap gap-4 items-end mb-4 border border-slate-700 rounded-lg p-4">
            <div>
              <label className="metric-label block mb-1">Prob smoothing (bars)</label>
              <input type="number" min={0} max={20} className={`${SELECT_CLS} w-24`} value={probSmoothingBars} onChange={(e) => setProbSmoothingBars(Number(e.target.value))} />
            </div>
            <div>
              <label className="metric-label block mb-1">Entry confirmation (bars)</label>
              <input type="number" min={1} max={10} className={`${SELECT_CLS} w-24`} value={entryConfirmationBars} onChange={(e) => setEntryConfirmationBars(Number(e.target.value))} />
            </div>
            <div>
              <label className="metric-label block mb-1">Min hold (bars)</label>
              <input type="number" min={0} max={50} className={`${SELECT_CLS} w-24`} value={minHoldBars} onChange={(e) => setMinHoldBars(Number(e.target.value))} />
            </div>
            <div>
              <label className="metric-label block mb-1">Cooldown after sell (bars)</label>
              <input type="number" min={0} max={50} className={`${SELECT_CLS} w-24`} value={cooldownBars} onChange={(e) => setCooldownBars(Number(e.target.value))} />
            </div>
            {(modelType === 'ou_deviation' || modelType === 'blended') && (
              <>
                <div>
                  <label className="metric-label block mb-1">OU MA window (bars)</label>
                  <input type="number" min={5} max={200} className={`${SELECT_CLS} w-24`} value={ouMaWindow} onChange={(e) => setOuMaWindow(Number(e.target.value))} />
                </div>
                {modelType === 'blended' && (
                  <>
                    <div>
                      <label className="metric-label block mb-1">ADX period</label>
                      <input type="number" min={5} max={50} className={`${SELECT_CLS} w-24`} value={adxPeriod} onChange={(e) => setAdxPeriod(Number(e.target.value))} />
                    </div>
                    <div>
                      <label className="metric-label block mb-1">ADX trend threshold</label>
                      <input type="number" min={10} max={60} className={`${SELECT_CLS} w-24`} value={adxTrendThreshold} onChange={(e) => setAdxTrendThreshold(Number(e.target.value))} />
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        )}
        <div className="mb-4 border border-brand-500/40 rounded-lg p-4 bg-surface-900/50">
          <h3 className="text-slate-200 font-medium text-sm mb-1">Multi-timeframe &amp; ML</h3>
          <p className="text-slate-500 text-xs mb-3">
            Higher timeframe regime filters entries. Threshold mode adapts buy/sell levels per bar (Backtest tab only).
          </p>
          <div className="flex flex-wrap gap-4 items-end">
            <div>
              <label className="metric-label block mb-1">Regime TF (4H/1D)</label>
              <select
                className={SELECT_CLS}
                value={regimeTimeframe}
                onChange={(e) => setRegimeTimeframe(e.target.value as McBacktestTimeframe | '')}
              >
                <option value="">Same as execution</option>
                {TIMEFRAME_OPTIONS.filter((o) => o.value !== timeframe).map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="metric-label block mb-1">Structure TF</label>
              <select
                className={SELECT_CLS}
                value={structureTimeframe}
                onChange={(e) => setStructureTimeframe(e.target.value as McBacktestTimeframe | '')}
              >
                <option value="">None</option>
                {TIMEFRAME_OPTIONS.filter((o) => o.value !== timeframe).map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="metric-label block mb-1">Min regime trend %</label>
              <input
                type="number"
                min={0}
                max={100}
                className={`${SELECT_CLS} w-24`}
                value={regimeMinTrendWeight}
                onChange={(e) => setRegimeMinTrendWeight(Number(e.target.value))}
                disabled={!regimeTimeframe}
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-300 pb-1">
              <input
                type="checkbox"
                checked={mtfGateEnabled}
                onChange={(e) => setMtfGateEnabled(e.target.checked)}
                disabled={!regimeTimeframe}
              />
              MTF entry gate
            </label>
            <div>
              <label className="metric-label block mb-1">Threshold mode</label>
              <select
                className={SELECT_CLS}
                value={thresholdMode}
                onChange={(e) => setThresholdMode(e.target.value as typeof thresholdMode)}
              >
                <option value="static">Static (use Entry/Exit % above)</option>
                <option value="suggested_percentile">Walk-forward percentiles</option>
                <option value="ml_dynamic">ML dynamic (server model)</option>
              </select>
            </div>
            <div>
              <label className="metric-label block mb-1">Regime mode</label>
              <select
                className={SELECT_CLS}
                value={regimeMode}
                onChange={(e) => setRegimeMode(e.target.value as 'adx' | 'ml')}
              >
                <option value="adx">ADX (blended model)</option>
                <option value="ml">ML regime (blended + server model)</option>
              </select>
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-300 pb-1">
              <input
                type="checkbox"
                checked={useSurrogate}
                onChange={(e) => setUseSurrogate(e.target.checked)}
              />
              MC surrogate (faster)
            </label>
          </div>
          {modelType !== 'blended' && regimeMode === 'ml' && (
            <p className="text-amber-500/90 text-xs mt-2">
              ML regime applies to the Blended model. Use Model = Blended, or Regime TF with Merton for trend gating.
            </p>
          )}
        </div>
        <McBacktestComboSection
          config={comboConfig}
          onChange={setComboConfig}
          execTimeframe={timeframe}
        />
        <button onClick={runBacktest} disabled={loading || !symbol} className="btn-primary disabled:opacity-50">
          {loading ? 'Running backtest…' : 'Run Backtest'}
        </button>
      </div>

      {loading && <Spinner label="Running walk-forward MC backtest…" />}

      {result && !loading && (
        <>
          <div className="flex items-center gap-3 flex-wrap">
            <StatusBadge status={result.status} />
            <span className="text-slate-400 text-sm">
              {result.symbol} &bull; {result.bars_evaluated} bars &bull; {result.duration_ms}ms
            </span>
          </div>

          {result.error_message && <ErrorAlert message={result.error_message} />}

          {result.metrics && <McBacktestMetricsGrid metrics={result.metrics} />}

          {result.zone_stats && result.zone_stats.bars_with_prob > 0 && (
            <div className="card">
              <h3 className="text-slate-200 font-semibold text-sm mb-2">
                Prob distribution &amp; suggested thresholds
              </h3>
              <p className="text-slate-500 text-xs mb-3">
                Share of bars where prob was in each threshold zone ({result.zone_stats.bars_with_prob} bars with data).
              </p>
              <div className="flex flex-wrap gap-6 text-sm">
                <span className="text-green-400">
                  Entry zone (≥ {Math.round(lastThresholds.buy * 100)}%): {result.zone_stats.entry_zone_pct}%
                </span>
                <span className="text-slate-400">
                  Middle: {result.zone_stats.middle_zone_pct}%
                </span>
                <span className="text-red-400">
                  Exit zone (&lt; {Math.round(lastThresholds.sell * 100)}%): {result.zone_stats.exit_zone_pct}%
                </span>
              </div>
              {(result.signal_log?.length ?? 0) > 0 && (
                <McBacktestProbSuggestions
                  zoneStats={result.zone_stats}
                  signalLog={result.signal_log!}
                  entryConfirmationBars={entryConfirmationBars}
                  onApplySuggested={applySuggestedThresholds}
                />
              )}
            </div>
          )}

          {(result.equity_curve ?? []).length > 0 && (
            <div className="card">
              <BacktestEquityCurve
                bare
                syncId="mc-backtest"
                data={result.equity_curve!}
                gradientId="mc-backtest-equity"
                executionLog={result.execution_log}
                buyHoldData={result.buy_hold_curve}
              />
              {(result.signal_log?.length ?? 0) > 0 && (
                <McProbPositiveChart
                  signalLog={result.signal_log!}
                  buyThreshold={lastThresholds.buy}
                  sellThreshold={lastThresholds.sell}
                  syncId="mc-backtest"
                />
              )}
              {overlayTrades.length > 0 && <OverlayTradeTable trades={overlayTrades} />}
            </div>
          )}

          {comboTimelineStrategies.length > 0 && (
            <div className="card">
              <h3 className="text-slate-200 font-semibold text-sm mb-3">Combo signal timeline</h3>
              <ComboSignalTimeline
                strategies={comboTimelineStrategies}
                syncId="mc-backtest-combo"
                alignmentTimeframe={timeframe}
                intraday={isIntradayTimeframe(timeframe)}
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function MonteCarloPage() {
  const assets = useAssets();
  const [activeTab, setActiveTab] = useState<TabId>('simulation');
  const [backtestPreset, setBacktestPreset] = useState<McBacktestPreset | null>(null);

  const handleApplyPreset = (preset: McBacktestPreset) => {
    setBacktestPreset(preset);
    setActiveTab('backtest');
  };
  const clearPreset = useCallback(() => setBacktestPreset(null), []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Monte Carlo Simulation</h1>
        <p className="text-slate-400 text-sm mt-1">
          Forward path simulation, walk-forward prob-positive backtesting, and backtest param optimization
        </p>
      </div>

      <TabBar active={activeTab} onChange={setActiveTab} />
      {activeTab === 'simulation' && <MonteCarloSimulationTab assets={assets} />}
      {activeTab === 'backtest' && (
        <MonteCarloBacktestTab
          assets={assets}
          preset={backtestPreset}
          onPresetApplied={clearPreset}
        />
      )}
      {activeTab === 'optimize' && (
        <MonteCarloBacktestOptimizeTab assets={assets} onApplyPreset={handleApplyPreset} />
      )}
    </div>
  );
}
