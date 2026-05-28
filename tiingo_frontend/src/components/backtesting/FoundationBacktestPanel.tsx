import { useCallback, useEffect, useMemo, useState } from 'react';
import { foundationBacktestApi, marketDataApi } from '../../api/endpoints';
import type {
  FoundationBacktestResultsResponse,
  FoundationModelCatalogItem,
  FoundationPreviewResponse,
} from '../../api/foundationBacktestTypes';
import type { OHLCVBar } from '../../api/types';
import type { DateRangeValue } from '../../constants/timeframes';
import { buildOhlcvQuery } from '../../constants/timeframes';
import ErrorAlert from '../ErrorAlert';
import Spinner from '../Spinner';
import BacktestMetricsCards from '../BacktestMetricsCards';
import BacktestPerformanceLabels from './BacktestPerformanceLabels';
import BacktestEquityChart from '../charts/BacktestEquityChart';
import OhlcvTimelineChart from '../charts/OhlcvTimelineChart';
import FoundationForecastChart from './FoundationForecastChart';
import FoundationScopeBanner from './FoundationScopeBanner';
import { formatBacktestPct, sortTradesByExit } from '../../utils/backtestData';
import {
  SIGNAL_MODE_OPTIONS,
  TARGET_SERIES_OPTIONS,
  mergeFoundationParams,
  scalarFoundationParams,
  formatForecastPct,
} from '../../utils/foundationBacktestConfig';
import type { Job } from '../../api/types';

interface FoundationBacktestPanelProps {
  symbol: string;
  dateRange: DateRangeValue;
  decisionTimeframe: string;
}

function extractErrorMessage(err: unknown, fallback = 'Request failed.'): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const resp = (err as { response?: { data?: { detail?: unknown }; status?: number } }).response;
    const detail = resp?.data?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
    if (resp?.status === 503) {
      return typeof detail === 'string'
        ? detail
        : 'Foundation models are unavailable. Enable FOUNDATION_MODELS_ENABLED and install dependencies.';
    }
  }
  if (err instanceof Error && err.message) {
    return err.message;
  }
  return fallback;
}

export default function FoundationBacktestPanel({
  symbol,
  dateRange,
  decisionTimeframe,
}: FoundationBacktestPanelProps) {
  const [models, setModels] = useState<FoundationModelCatalogItem[]>([]);
  const [modelType, setModelType] = useState('foundation_timesfm_2_5');
  const [runParams, setRunParams] = useState<Record<string, unknown>>({});
  const [initialCash, setInitialCash] = useState(10_000);
  const [commissionBps, setCommissionBps] = useState(5);
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [jobProgress, setJobProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<FoundationPreviewResponse | null>(null);
  const [results, setResults] = useState<FoundationBacktestResultsResponse | null>(null);
  const [chartRecords, setChartRecords] = useState<OHLCVBar[]>([]);
  const [chartError, setChartError] = useState<string | null>(null);

  const selectedModel = useMemo(
    () => models.find((item) => item.id === modelType),
    [models, modelType],
  );

  const mergedParams = useMemo(
    () => mergeFoundationParams(selectedModel, runParams),
    [selectedModel, runParams],
  );

  const ohlcvQuery = useMemo(
    () => buildOhlcvQuery(dateRange, decisionTimeframe),
    [dateRange, decisionTimeframe],
  );

  useEffect(() => {
    let cancelled = false;
    setLoadingCatalog(true);
    setCatalogError(null);
    foundationBacktestApi
      .listModels()
      .then((catalog) => {
        if (cancelled) return;
        const items = catalog.models ?? [];
        setModels(items);
        if (items.length > 0) {
          setModelType(items[0].id);
          setRunParams(items[0].params ?? {});
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setCatalogError(extractErrorMessage(err, 'Could not load foundation model catalog.'));
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingCatalog(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleModelChange = (nextId: string) => {
    setModelType(nextId);
    const item = models.find((m) => m.id === nextId);
    if (item) {
      setRunParams(item.params ?? {});
    }
  };

  const updateParam = (key: string, value: number | string) => {
    setRunParams((prev) => ({ ...prev, [key]: value }));
  };

  const buildRunBody = useCallback(
    () => ({
      symbol,
      model_type: modelType,
      params: {
        ...scalarFoundationParams(mergedParams),
        target_series: String(mergedParams.target_series ?? 'close'),
        signal_mode: String(mergedParams.signal_mode ?? 'next_point'),
      },
      timeframe: decisionTimeframe,
      start: ohlcvQuery.start,
      end: ohlcvQuery.end,
      initial_cash: initialCash,
      commission_bps: commissionBps,
    }),
    [symbol, modelType, mergedParams, decisionTimeframe, ohlcvQuery, initialCash, commissionBps],
  );

  const loadCharts = useCallback(
    async (run: FoundationBacktestResultsResponse) => {
      setChartError(null);
      try {
        const data = await marketDataApi.getOhlcv(symbol, {
          timeframe: decisionTimeframe,
          start: ohlcvQuery.start,
          end: ohlcvQuery.end,
        });
        setChartRecords(data.bars ?? []);
      } catch (err) {
        setChartError(extractErrorMessage(err, 'Failed to load OHLCV chart.'));
        setChartRecords([]);
      }
      void run;
    },
    [symbol, decisionTimeframe, ohlcvQuery],
  );

  const handlePreview = async () => {
    setPreviewing(true);
    setError(null);
    setPreview(null);
    try {
      const body = buildRunBody();
      const response = await foundationBacktestApi.preview(
        {
          symbol: body.symbol,
          model_type: body.model_type,
          params: body.params,
          timeframe: body.timeframe,
          start: body.start,
          end: body.end,
        },
        (job: Job) => setJobProgress(job.progress ?? null),
      );
      setPreview(response);
    } catch (err) {
      setError(extractErrorMessage(err, 'Forecast preview failed.'));
    } finally {
      setPreviewing(false);
      setJobProgress(null);
    }
  };

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    setResults(null);
    try {
      const jobResult = await foundationBacktestApi.run(buildRunBody(), (job: Job) =>
        setJobProgress(job.progress ?? null),
      );
      const full = await foundationBacktestApi.getResults(jobResult.run_id);
      setResults(full);
      await loadCharts(full);
    } catch (err) {
      setError(extractErrorMessage(err, 'Foundation backtest failed.'));
    } finally {
      setRunning(false);
      setJobProgress(null);
    }
  };

  if (loadingCatalog) {
    return (
      <div className="flex justify-center py-12">
        <Spinner />
      </div>
    );
  }

  if (catalogError) {
    return <ErrorAlert message={catalogError} />;
  }

  const summary = results?.foundation_summary;
  const walkMeta = summary?.walk_forward;

  return (
    <div className="space-y-6">
      <FoundationScopeBanner
        contextLength={walkMeta?.context_length ?? Number(mergedParams.context_length)}
        forecastHorizon={walkMeta?.forecast_horizon ?? Number(mergedParams.forecast_horizon)}
        warmupBars={walkMeta?.warmup_bars}
      />

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <label className="space-y-1 text-sm">
          <span className="text-slate-400">Foundation model</span>
          <select
            value={modelType}
            onChange={(e) => handleModelChange(e.target.value)}
            className="w-full bg-surface-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
          >
            {models.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-1 text-sm">
          <span className="text-slate-400">Target series</span>
          <select
            value={String(mergedParams.target_series ?? 'close')}
            onChange={(e) => updateParam('target_series', e.target.value)}
            className="w-full bg-surface-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
          >
            {TARGET_SERIES_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-1 text-sm">
          <span className="text-slate-400">Signal mode</span>
          <select
            value={String(mergedParams.signal_mode ?? 'next_point')}
            onChange={(e) => updateParam('signal_mode', e.target.value)}
            className="w-full bg-surface-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
          >
            {SIGNAL_MODE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-1 text-sm">
          <span className="text-slate-400">Context length</span>
          <input
            type="number"
            value={Number(mergedParams.context_length ?? 128)}
            onChange={(e) => updateParam('context_length', Number(e.target.value))}
            className="w-full bg-surface-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
          />
        </label>

        <label className="space-y-1 text-sm">
          <span className="text-slate-400">Forecast horizon</span>
          <input
            type="number"
            value={Number(mergedParams.forecast_horizon ?? 5)}
            onChange={(e) => updateParam('forecast_horizon', Number(e.target.value))}
            className="w-full bg-surface-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
          />
        </label>

        <label className="space-y-1 text-sm">
          <span className="text-slate-400">Buy return threshold</span>
          <input
            type="number"
            step="0.001"
            value={Number(mergedParams.buy_return_threshold ?? 0.01)}
            onChange={(e) => updateParam('buy_return_threshold', Number(e.target.value))}
            className="w-full bg-surface-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
          />
        </label>

        <label className="space-y-1 text-sm">
          <span className="text-slate-400">Sell return threshold</span>
          <input
            type="number"
            step="0.001"
            value={Number(mergedParams.sell_return_threshold ?? -0.01)}
            onChange={(e) => updateParam('sell_return_threshold', Number(e.target.value))}
            className="w-full bg-surface-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
          />
        </label>

        <label className="space-y-1 text-sm">
          <span className="text-slate-400">Initial cash</span>
          <input
            type="number"
            value={initialCash}
            onChange={(e) => setInitialCash(Number(e.target.value))}
            className="w-full bg-surface-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
          />
        </label>

        <label className="space-y-1 text-sm">
          <span className="text-slate-400">Commission (bps)</span>
          <input
            type="number"
            value={commissionBps}
            onChange={(e) => setCommissionBps(Number(e.target.value))}
            className="w-full bg-surface-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
          />
        </label>
      </div>

      {selectedModel?.description && (
        <p className="text-xs text-slate-500">{selectedModel.description}</p>
      )}

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          onClick={() => void handlePreview()}
          disabled={previewing || running}
          className="px-4 py-2 rounded-lg bg-surface-800 text-slate-100 text-sm font-medium hover:bg-surface-700 disabled:opacity-50"
        >
          {previewing ? 'Previewing…' : 'Preview forecast'}
        </button>
        <button
          type="button"
          onClick={() => void handleRun()}
          disabled={running || previewing}
          className="px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-500 disabled:opacity-50"
        >
          {running ? 'Running backtest…' : 'Run foundation backtest'}
        </button>
        {jobProgress != null && (
          <span className="text-sm text-slate-400 self-center">Job progress: {jobProgress}%</span>
        )}
      </div>

      {error && <ErrorAlert message={error} />}

      {preview && (
        <FoundationForecastChart
          contextPoints={preview.context_points}
          forecastPoints={preview.forecast_points}
        />
      )}

      {results && (
        <div className="space-y-6 border-t border-slate-800 pt-6">
          <BacktestPerformanceLabels metrics={results.metrics} />
          <BacktestMetricsCards metrics={results.metrics} />

          {summary && (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-sm">
              <div className="rounded-lg border border-slate-800 bg-surface-900/50 p-3">
                <p className="text-slate-500 text-xs">Forecast MAE</p>
                <p className="text-slate-100 font-medium">
                  {summary.forecast_metrics.mae?.toFixed(4) ?? '—'}
                </p>
              </div>
              <div className="rounded-lg border border-slate-800 bg-surface-900/50 p-3">
                <p className="text-slate-500 text-xs">Forecast MAPE</p>
                <p className="text-slate-100 font-medium">
                  {summary.forecast_metrics.mape != null
                    ? `${summary.forecast_metrics.mape.toFixed(2)}%`
                    : '—'}
                </p>
              </div>
              <div className="rounded-lg border border-slate-800 bg-surface-900/50 p-3">
                <p className="text-slate-500 text-xs">Directional accuracy</p>
                <p className="text-slate-100 font-medium">
                  {formatForecastPct(summary.forecast_metrics.directional_accuracy)}
                </p>
              </div>
              <div className="rounded-lg border border-slate-800 bg-surface-900/50 p-3">
                <p className="text-slate-500 text-xs">Signals</p>
                <p className="text-slate-100 font-medium text-xs">
                  buy {summary.signal_counts.buy ?? 0} · sell {summary.signal_counts.sell ?? 0}{' '}
                  · hold {summary.signal_counts.hold ?? 0}
                </p>
              </div>
            </div>
          )}

          {summary?.forecast_samples && summary.forecast_samples.length > 0 && (
            <FoundationForecastChart
              contextPoints={[]}
              forecastPoints={summary.forecast_samples}
              title="Walk-forward forecast samples"
            />
          )}

          <BacktestEquityChart
            strategyCurve={results.equity_curve}
            benchmarkCurve={results.benchmark_equity_curve}
          />

          {chartError && <ErrorAlert message={chartError} />}
          {chartRecords.length > 0 && (
            <OhlcvTimelineChart records={chartRecords} symbol={symbol} />
          )}

          {results.trades.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-slate-500 border-b border-slate-800">
                  <tr>
                    <th className="py-2 pr-4">Entry</th>
                    <th className="py-2 pr-4">Exit</th>
                    <th className="py-2 pr-4">Return</th>
                  </tr>
                </thead>
                <tbody>
                  {sortTradesByExit(results.trades).map((trade, index) => (
                    <tr key={`${trade.entry_date}-${index}`} className="border-b border-slate-800/60">
                      <td className="py-2 pr-4 text-slate-300">{trade.entry_date}</td>
                      <td className="py-2 pr-4 text-slate-300">{trade.exit_date}</td>
                      <td className="py-2 pr-4 text-slate-300">
                        {formatBacktestPct(trade.return_pct)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
