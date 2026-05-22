import { useCallback, useEffect, useMemo, useState } from 'react';
import { backtestApi, ingestionApi, marketDataApi } from '../../api/endpoints';
import type {
  BacktestResultsResponse,
  EnsembleParams,
  StrategyCatalogItem,
} from '../../api/backtestTypes';
import type { OHLCVBar } from '../../api/types';
import type { DateRangeValue } from '../../constants/timeframes';
import { OHLCV_TIMEFRAMES, buildOhlcvQuery } from '../../constants/timeframes';
import ErrorAlert from '../ErrorAlert';
import Spinner from '../Spinner';
import BacktestMetricsCards from '../BacktestMetricsCards';
import BacktestPerformanceLabels from './BacktestPerformanceLabels';
import BacktestEquityChart from '../charts/BacktestEquityChart';
import BacktestStrategyTrendChart from '../charts/BacktestStrategyTrendChart';
import OhlcvTimelineChart from '../charts/OhlcvTimelineChart';
import EnsembleConfigForm from './EnsembleConfigForm';
import { formatBacktestPct, sortTradesByExit } from '../../utils/backtestData';
import {
  apiRangeFromOhlcvQuery,
  chartDateRange,
  collectResultSignalTimeframes,
  effectiveSignalTimeframe,
} from '../../utils/multitimeframeBacktest';
import {
  ensembleResultsTitle,
  parseEnsembleLegs,
  strategyTrendChartMode,
  strategyTrendTitle,
} from '../../utils/backtestStrategyTrend';
import {
  ENSEMBLE_STRATEGY_ID,
  defaultEnsembleParams,
  isEnsembleParams,
  parseEnsembleParams,
} from '../../utils/ensembleConfig';
import {
  buildCoverageWarnings,
  parseEffectiveCoverage,
  warmupRequirementBars,
  type OhlcvCoverageResponse,
} from '../../utils/backtestCoverage';

interface AlgosBacktestPanelProps {
  symbol: string;
  dateRange: DateRangeValue;
  decisionTimeframe: string;
}

function extractErrorMessage(err: unknown, fallback = 'Backtest failed.'): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const resp = (err as { response?: { data?: { detail?: unknown } } }).response;
    const detail = resp?.data?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail
        .map((item) =>
          typeof item === 'object' && item && 'msg' in item ? String(item.msg) : String(item),
        )
        .join('; ');
    }
  }
  if (err instanceof Error && err.message) {
    return err.message;
  }
  return fallback;
}

function scalarParams(params: Record<string, unknown>): Record<string, number> {
  const result: Record<string, number> = {};
  for (const [key, value] of Object.entries(params)) {
    if (typeof value === 'number') {
      result[key] = value;
    }
  }
  return result;
}

export default function AlgosBacktestPanel({
  symbol,
  dateRange,
  decisionTimeframe,
}: AlgosBacktestPanelProps) {
  const [strategies, setStrategies] = useState<StrategyCatalogItem[]>([]);
  const [strategyId, setStrategyId] = useState('sma_crossover');
  const [signalTimeframe, setSignalTimeframe] = useState(decisionTimeframe);
  const [runParams, setRunParams] = useState<Record<string, unknown>>({});
  const [initialCash, setInitialCash] = useState(10_000);
  const [commissionBps, setCommissionBps] = useState(0);
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chartError, setChartError] = useState<string | null>(null);
  const [results, setResults] = useState<BacktestResultsResponse | null>(null);
  const [chartRecords, setChartRecords] = useState<OHLCVBar[]>([]);
  const [signalChartRecords, setSignalChartRecords] = useState<Record<string, OHLCVBar[]>>({});
  const [coverageByTf, setCoverageByTf] = useState<Record<string, OhlcvCoverageResponse | null>>({});

  const selectedStrategy = useMemo(
    () => strategies.find((item) => item.id === strategyId),
    [strategies, strategyId],
  );

  const legStrategies = useMemo(
    () => strategies.filter((item) => item.ensemble_eligible),
    [strategies],
  );

  const ensembleParams = useMemo(() => {
    if (strategyId !== ENSEMBLE_STRATEGY_ID) return null;
    return isEnsembleParams(runParams) ? runParams : parseEnsembleParams(runParams);
  }, [runParams, strategyId]);

  useEffect(() => {
    let cancelled = false;
    setLoadingCatalog(true);
    backtestApi
      .listStrategies()
      .then((data) => {
        if (cancelled) return;
        setStrategies(data.strategies);
        const first = data.strategies[0];
        if (first) {
          setStrategyId(first.id);
          if (first.id === ENSEMBLE_STRATEGY_ID) {
            setRunParams(defaultEnsembleParams(data.strategies) as unknown as Record<string, unknown>);
          } else {
            setRunParams(scalarParams(first.params));
          }
        }
      })
      .catch(() => {
        if (!cancelled) setError('Failed to load strategy catalog.');
      })
      .finally(() => {
        if (!cancelled) setLoadingCatalog(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    setSignalTimeframe(decisionTimeframe);
  }, [decisionTimeframe]);

  useEffect(() => {
    if (!selectedStrategy) return;
    if (strategyId === ENSEMBLE_STRATEGY_ID) {
      setRunParams(defaultEnsembleParams(strategies) as unknown as Record<string, unknown>);
      return;
    }
    setRunParams(scalarParams(selectedStrategy.params));
  }, [strategyId, strategies, selectedStrategy]);

  const signalCoverageRequirements = useMemo(() => {
    const requirements: Record<string, number> = {};
    if (strategyId === ENSEMBLE_STRATEGY_ID && ensembleParams) {
      for (const leg of ensembleParams.legs) {
        const tf = effectiveSignalTimeframe(leg.signal_timeframe, decisionTimeframe);
        if (tf === decisionTimeframe) continue;
        requirements[tf] = Math.max(
          requirements[tf] ?? 0,
          warmupRequirementBars(leg.strategy_id, leg.params),
        );
      }
      return requirements;
    }
    const tf = effectiveSignalTimeframe(signalTimeframe, decisionTimeframe);
    if (tf !== decisionTimeframe) {
      requirements[tf] = warmupRequirementBars(strategyId, scalarParams(runParams));
    }
    return requirements;
  }, [strategyId, ensembleParams, decisionTimeframe, signalTimeframe, runParams]);

  useEffect(() => {
    if (!symbol) {
      setCoverageByTf({});
      return;
    }

    const timeframes = Object.keys(signalCoverageRequirements);
    if (timeframes.length === 0) {
      setCoverageByTf({});
      return;
    }

    let cancelled = false;
    Promise.all(
      timeframes.map(async (timeframe) => {
        const raw = await ingestionApi.getCoverage(symbol, timeframe, true);
        return [timeframe, parseEffectiveCoverage(raw)] as const;
      }),
    )
      .then((entries) => {
        if (cancelled) return;
        setCoverageByTf(Object.fromEntries(entries));
      })
      .catch(() => {
        if (!cancelled) setCoverageByTf({});
      });

    return () => {
      cancelled = true;
    };
  }, [symbol, signalCoverageRequirements]);

  const coverageWarnings = useMemo(
    () => buildCoverageWarnings(coverageByTf, dateRange, signalCoverageRequirements),
    [coverageByTf, dateRange, signalCoverageRequirements],
  );

  const loadResultCharts = useCallback(
    async (full: BacktestResultsResponse, standaloneSignalTf: string) => {
      const range = chartDateRange(full, dateRange);
      const decisionQuery = buildOhlcvQuery(decisionTimeframe, range);
      const decisionData = await marketDataApi.getOhlcv(symbol, decisionQuery);
      setChartRecords(decisionData.records);

      const timeframes = collectResultSignalTimeframes(full, standaloneSignalTf, decisionTimeframe);
      const byTimeframe: Record<string, OHLCVBar[]> = {
        [decisionTimeframe]: decisionData.records,
      };

      await Promise.all(
        timeframes
          .filter((timeframe) => timeframe !== decisionTimeframe)
          .map(async (timeframe) => {
            const data = await marketDataApi.getOhlcv(symbol, buildOhlcvQuery(timeframe, range));
            byTimeframe[timeframe] = data.records;
          }),
      );

      setSignalChartRecords(byTimeframe);
    },
    [symbol, dateRange, decisionTimeframe],
  );

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    setChartError(null);
    setResults(null);
    setChartRecords([]);
    setSignalChartRecords({});
    try {
      const ohlcvQuery = buildOhlcvQuery(decisionTimeframe, dateRange);
      const paramsPayload =
        strategyId === ENSEMBLE_STRATEGY_ID && ensembleParams
          ? {
              ...ensembleParams,
              legs: ensembleParams.legs.map((leg) => ({
                ...leg,
                signal_timeframe: effectiveSignalTimeframe(leg.signal_timeframe, decisionTimeframe),
              })),
            }
          : runParams;

      const run = await backtestApi.run({
        symbol,
        strategy: strategyId,
        params: paramsPayload,
        timeframe: decisionTimeframe,
        signal_timeframe:
          strategyId !== ENSEMBLE_STRATEGY_ID && signalTimeframe !== decisionTimeframe
            ? signalTimeframe
            : undefined,
        initial_cash: initialCash,
        commission_bps: commissionBps,
        ...apiRangeFromOhlcvQuery(ohlcvQuery),
      });
      const full = await backtestApi.getResults(run.id);
      setResults(full);
      try {
        await loadResultCharts(full, signalTimeframe);
      } catch (chartErr: unknown) {
        setChartError(
          extractErrorMessage(chartErr, 'Price chart data could not be loaded.'),
        );
      }
    } catch (err: unknown) {
      setError(extractErrorMessage(err));
    } finally {
      setRunning(false);
    }
  };

  const handleEnsembleChange = (value: EnsembleParams) => {
    setRunParams(value as unknown as Record<string, unknown>);
  };

  if (loadingCatalog) {
    return (
      <div className="flex justify-center py-12">
        <Spinner />
      </div>
    );
  }

  const scalarStrategyParams = scalarParams(runParams);

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-slate-800 bg-surface-900 p-4 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          <label className="space-y-1 text-sm">
            <span className="text-slate-400">Strategy</span>
            <select
              value={strategyId}
              onChange={(e) => setStrategyId(e.target.value)}
              className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
            >
              {strategies.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>

          {strategyId !== ENSEMBLE_STRATEGY_ID && (
            <label className="space-y-1 text-sm">
              <span className="text-slate-400">Signal timeframe</span>
              <select
                value={signalTimeframe}
                onChange={(e) => setSignalTimeframe(e.target.value)}
                className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
              >
                {OHLCV_TIMEFRAMES.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
          )}

          {strategyId === ENSEMBLE_STRATEGY_ID && ensembleParams && (
            <EnsembleConfigForm
              value={ensembleParams}
              onChange={handleEnsembleChange}
              legStrategies={legStrategies}
              decisionTimeframe={decisionTimeframe}
            />
          )}

          {selectedStrategy &&
            strategyId !== ENSEMBLE_STRATEGY_ID &&
            Object.entries(selectedStrategy.params as Record<string, number>).map(([key, defaultValue]) => {
              const constraint = selectedStrategy.constraints[key];
              return (
                <label key={key} className="space-y-1 text-sm">
                  <span className="text-slate-400">{key.replace(/_/g, ' ')}</span>
                  <input
                    type="number"
                    value={scalarStrategyParams[key] ?? defaultValue}
                    min={constraint?.min}
                    max={constraint?.max}
                    onChange={(e) =>
                      setRunParams((prev) => ({
                        ...prev,
                        [key]: Number(e.target.value),
                      }))
                    }
                    className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
                  />
                </label>
              );
            })}

          <label className="space-y-1 text-sm">
            <span className="text-slate-400">Initial cash</span>
            <input
              type="number"
              value={initialCash}
              min={1}
              onChange={(e) => setInitialCash(Number(e.target.value))}
              className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
            />
          </label>

          <label className="space-y-1 text-sm">
            <span className="text-slate-400">Commission (bps)</span>
            <input
              type="number"
              value={commissionBps}
              min={0}
              onChange={(e) => setCommissionBps(Number(e.target.value))}
              className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
            />
          </label>
        </div>

        {selectedStrategy && (
          <p className="text-xs text-slate-500">{selectedStrategy.description}</p>
        )}

        {coverageWarnings.length > 0 && (
          <div className="rounded-lg border border-amber-800/60 bg-amber-950/30 px-3 py-2 space-y-1">
            {coverageWarnings.map((warning) => (
              <p key={warning.timeframe} className="text-xs text-amber-200/90">
                <span className="font-medium text-amber-100">{warning.timeframe}:</span>{' '}
                {warning.message}
              </p>
            ))}
          </div>
        )}

        <button
          type="button"
          onClick={handleRun}
          disabled={running || !symbol}
          className="px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white text-sm font-medium"
        >
          {running ? 'Running backtest…' : 'Run backtest'}
        </button>
      </section>

      {error && <ErrorAlert message={error} />}
      {chartError && !error && <ErrorAlert message={chartError} />}

      {running && (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      )}

      {results && !running && (
        <div className="space-y-6">
          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-slate-200">Results</h2>
            <BacktestMetricsCards metrics={results.metrics} />
            <BacktestPerformanceLabels metrics={results.metrics} />
          </section>

          <section className="space-y-3">
            <h3 className="text-sm font-medium text-slate-300">Equity curve</h3>
            <BacktestEquityChart
              strategy={results.equity_curve}
              benchmark={results.benchmark_equity_curve}
            />
          </section>

          {results.strategy === ENSEMBLE_STRATEGY_ID && chartRecords.length > 0 && (
            <section className="space-y-4">
              <h3 className="text-sm font-medium text-slate-300">
                {ensembleResultsTitle(results.params)}
              </h3>
              {parseEnsembleLegs(results.params).map((leg, index) => {
                const legTf = effectiveSignalTimeframe(leg.signal_timeframe, decisionTimeframe);
                const records = signalChartRecords[legTf] ?? chartRecords;
                return strategyTrendChartMode(leg.strategy_id) ? (
                  <div key={`${leg.strategy_id}-${index}`} className="space-y-2">
                    <h4 className="text-xs text-slate-400">
                      Leg {index + 1} ({legTf}): {strategyTrendTitle(leg.strategy_id, leg.params)}
                    </h4>
                    <BacktestStrategyTrendChart
                      strategyId={leg.strategy_id}
                      params={leg.params}
                      records={records}
                      signalTimeframe={legTf}
                    />
                  </div>
                ) : null;
              })}
            </section>
          )}

          {chartRecords.length > 0 &&
            results.strategy !== ENSEMBLE_STRATEGY_ID &&
            strategyTrendChartMode(results.strategy) && (
              <section className="space-y-3">
                <h3 className="text-sm font-medium text-slate-300">Strategy trend</h3>
                <BacktestStrategyTrendChart
                  strategyId={results.strategy}
                  params={scalarParams(results.params)}
                  records={
                    signalChartRecords[
                      effectiveSignalTimeframe(signalTimeframe, decisionTimeframe)
                    ] ?? chartRecords
                  }
                  signalTimeframe={effectiveSignalTimeframe(signalTimeframe, decisionTimeframe)}
                />
              </section>
            )}

          {chartRecords.length > 0 && (
            <section className="space-y-3">
              <h3 className="text-sm font-medium text-slate-300">Price chart with trades</h3>
              <OhlcvTimelineChart
                records={chartRecords}
                timeframe={decisionTimeframe}
                trades={results.trades}
              />
            </section>
          )}

          {results.trades.length > 0 && (
            <section className="space-y-3">
              <h3 className="text-sm font-medium text-slate-300">Trades</h3>
              <div className="overflow-x-auto border border-slate-800 rounded-lg">
                <table className="min-w-full text-sm">
                  <thead className="bg-surface-900 text-slate-400">
                    <tr>
                      <th className="px-3 py-2 text-left">Entry</th>
                      <th className="px-3 py-2 text-left">Exit</th>
                      <th className="px-3 py-2 text-right">Entry px</th>
                      <th className="px-3 py-2 text-right">Exit px</th>
                      <th className="px-3 py-2 text-right">Shares</th>
                      <th className="px-3 py-2 text-right">PnL</th>
                      <th className="px-3 py-2 text-right">PnL %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortTradesByExit(results.trades).map((trade, index) => (
                      <tr key={`${trade.entry_date}-${trade.exit_date}-${index}`} className="border-t border-slate-800">
                        <td className="px-3 py-2 text-slate-200">{trade.entry_date}</td>
                        <td className="px-3 py-2 text-slate-200">{trade.exit_date}</td>
                        <td className="px-3 py-2 text-right text-slate-300">{trade.entry_price.toFixed(2)}</td>
                        <td className="px-3 py-2 text-right text-slate-300">{trade.exit_price.toFixed(2)}</td>
                        <td className="px-3 py-2 text-right text-slate-300">{trade.shares.toFixed(2)}</td>
                        <td className={`px-3 py-2 text-right ${trade.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {trade.pnl.toFixed(2)}
                        </td>
                        <td className={`px-3 py-2 text-right ${trade.pnl_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {formatBacktestPct(trade.pnl_pct)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
