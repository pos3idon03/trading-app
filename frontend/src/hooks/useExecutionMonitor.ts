/**
 * Hook that drives live monitoring for all running auto-trading assets.
 *
 * Responsibilities:
 *  - Polls autoTradingApi.list() every ASSET_LIST_INTERVAL_MS to detect
 *    newly started / stopped assets.
 *  - For each running asset, polls live indicators + strategy signals on an
 *    interval derived from the asset's algo_timeframe.
 *  - Fetches the full strategy (attached algo list) once per asset.
 *  - Fetches orders per asset (paginated, 10 per page) and refreshes every ORDER_INTERVAL_MS.
 *  - Exposes an ExecutionAssetMonitor[] for the UI to render.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { autoTradingApi, executionApi, liveApi, strategyBuilderApi } from '../api/endpoints';
import type {
  AlgoStrategySummary,
  AutoTradingAssetRow,
  ExecutionAssetMonitor,
  ExecutionIndicatorSnapshot,
  LiveStrategySignalItem,
  OrderItem,
} from '../api/types';
import {
  buildCombinedVotes,
  buildCriteriaEvaluations,
  collectUniqueAlgoTimeframes,
  combineSignalsFromVotes,
  expandAlgoSignals,
  strategyNamesForTimeframe,
  timeframeToMs,
} from '../utils/executionSignals';
import { finestTimeframe } from '../utils/timelineAlignment';

const ASSET_LIST_INTERVAL_MS = 30_000;
const ORDER_INTERVAL_MS = 30_000;
const MIN_LIVE_POLL_MS = 60_000;
export const TRANSACTIONS_PAGE_SIZE = 10;

export interface ExecutionMonitorOptions {
  /** Cap live indicator/signal polling (e.g. 60_000 for the Live terminal page). */
  livePollMaxIntervalMs?: number;
}

export function resolveLivePollMs(
  timeframe: string,
  livePollMaxIntervalMs?: number,
): number {
  const fromTf = Math.max(timeframeToMs(timeframe), MIN_LIVE_POLL_MS);
  if (livePollMaxIntervalMs == null) return fromTf;
  return Math.max(MIN_LIVE_POLL_MS, Math.min(fromTf, livePollMaxIntervalMs));
}

function maxOrdersPage(total: number): number {
  if (total <= 0) return 1;
  return Math.ceil(total / TRANSACTIONS_PAGE_SIZE);
}

// ---------------------------------------------------------------------------
// Build monitor snapshot from accumulated per-asset data
// ---------------------------------------------------------------------------

function buildMonitor(
  asset: AutoTradingAssetRow,
  algoSummaries: AlgoStrategySummary[],
  liveByStrategy: Map<string, LiveStrategySignalItem>,
  latestPrice: number | null,
  priceUpdatedAt: string | null,
  indicatorSnapshot: ExecutionIndicatorSnapshot | null,
  lastLivePollAt: string | null,
  orders: OrderItem[],
  ordersTotal: number,
  ordersPage: number,
  loading: boolean,
  error: string | null,
): ExecutionAssetMonitor {
  const criteria = buildCriteriaEvaluations(asset);
  const { algoSignals, comboSignals } = expandAlgoSignals(algoSummaries, liveByStrategy);
  const votes = buildCombinedVotes(criteria, algoSignals, comboSignals);
  const overallSignal = combineSignalsFromVotes(votes, asset.combination_mode);

  return {
    strategyId: asset.strategy_id,
    symbol: asset.symbol,
    assetName: asset.asset_name,
    assetType: asset.asset_type,
    combinationMode: asset.combination_mode,
    algoTimeframe: asset.algo_timeframe,
    criteria,
    overallSignal,
    combinedVoteCount: votes.length,
    algoSignals,
    comboSignals,
    latestPrice,
    priceUpdatedAt,
    indicatorSnapshot,
    lastLivePollAt,
    orders,
    ordersTotal,
    ordersPage,
    loading,
    error,
  };
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useExecutionMonitor(options: ExecutionMonitorOptions = {}) {
  const { livePollMaxIntervalMs } = options;
  const [monitors, setMonitors] = useState<ExecutionAssetMonitor[]>([]);
  const [assetsLoading, setAssetsLoading] = useState(true);
  const [assetsError, setAssetsError] = useState<string | null>(null);

  // Per-asset accumulated data keyed by strategy_id
  const algoSummariesRef = useRef<Map<number, AlgoStrategySummary[]>>(new Map());
  // Maps strategy_name → full live signal item for the current poll cycle, per asset
  const liveByStrategyRef = useRef<Map<number, Map<string, LiveStrategySignalItem>>>(new Map());
  const priceRef = useRef<Map<number, { price: number | null; at: string | null }>>(new Map());
  const indicatorSnapshotRef = useRef<Map<number, ExecutionIndicatorSnapshot | null>>(new Map());
  const lastLivePollAtRef = useRef<Map<number, string | null>>(new Map());
  const ordersRef = useRef<Map<number, OrderItem[]>>(new Map());
  const ordersTotalByStrategyRef = useRef<Map<number, number>>(new Map());
  const orderPageByStrategyRef = useRef<Map<number, number>>(new Map());
  const assetsRef = useRef<AutoTradingAssetRow[]>([]);

  // Per-asset, per-timeframe poll intervals (key __indicators__ for price/indicator snapshot)
  const liveIntervalsRef = useRef<
    Map<number, Map<string, ReturnType<typeof setInterval>>>
  >(new Map());
  const orderIntervalsRef = useRef<Map<number, ReturnType<typeof setInterval>>>(new Map());
  const assetListIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ---------------------------------------------------------------------------
  // Recompute and publish monitors from current refs
  // ---------------------------------------------------------------------------

  const publishMonitors = useCallback(() => {
    const updated = assetsRef.current.map((asset) => {
      const algoSummaries = algoSummariesRef.current.get(asset.strategy_id) ?? [];
      const liveByStrategy = liveByStrategyRef.current.get(asset.strategy_id) ?? new Map();
      const priceData = priceRef.current.get(asset.strategy_id) ?? { price: null, at: null };
      const indicatorSnapshot = indicatorSnapshotRef.current.get(asset.strategy_id) ?? null;
      const lastLivePollAt = lastLivePollAtRef.current.get(asset.strategy_id) ?? null;
      const orders = ordersRef.current.get(asset.strategy_id) ?? [];
      const ordersTotal = ordersTotalByStrategyRef.current.get(asset.strategy_id) ?? 0;
      const ordersPage = orderPageByStrategyRef.current.get(asset.strategy_id) ?? 1;
      return buildMonitor(
        asset,
        algoSummaries,
        liveByStrategy,
        priceData.price,
        priceData.at,
        indicatorSnapshot,
        lastLivePollAt,
        orders,
        ordersTotal,
        ordersPage,
        false,
        null,
      );
    });
    setMonitors(updated);
  }, []);

  // ---------------------------------------------------------------------------
  // Per-asset live poll (indicators + strategy signals)
  // ---------------------------------------------------------------------------

  const pollIndicators = useCallback(
    async (asset: AutoTradingAssetRow, finestTf: string) => {
      try {
        const ind = await liveApi.getIndicators(asset.symbol, finestTf);
        priceRef.current.set(asset.strategy_id, {
          price: ind.close_price ?? null,
          at: ind.created_at ?? null,
        });
        indicatorSnapshotRef.current.set(asset.strategy_id, {
          close_price: ind.close_price,
          rsi: ind.rsi ?? null,
          macd: ind.macd ?? null,
          macd_signal: ind.macd_signal ?? null,
          macd_histogram: ind.macd_histogram ?? null,
          bb_upper: ind.bb_upper ?? null,
          bb_middle: ind.bb_middle ?? null,
          bb_lower: ind.bb_lower ?? null,
          vwap: ind.vwap ?? null,
          bb_percent: ind.bb_percent ?? null,
        });
        publishMonitors();
      } catch {
        // keep stale indicators
      }
    },
    [publishMonitors],
  );

  const pollSignalsForTimeframe = useCallback(
    async (asset: AutoTradingAssetRow, tf: string) => {
      try {
        const summaries = algoSummariesRef.current.get(asset.strategy_id) ?? [];
        const names = strategyNamesForTimeframe(
          summaries,
          tf,
          asset.algo_timeframe,
        );
        if (names.length === 0) return;

        const resp = await liveApi.getStrategySignals(asset.symbol, tf, {
          includeTimeline: true,
          timelineBars: 120,
          strategyNames: names,
        });

        const existing =
          liveByStrategyRef.current.get(asset.strategy_id) ?? new Map();
        for (const s of resp.strategies) {
          existing.set(s.strategy, s);
        }
        liveByStrategyRef.current.set(asset.strategy_id, existing);
        lastLivePollAtRef.current.set(asset.strategy_id, new Date().toISOString());
        publishMonitors();
      } catch {
        // keep stale signals
      }
    },
    [publishMonitors],
  );

  const pollLiveData = useCallback(
    async (asset: AutoTradingAssetRow) => {
      const summaries = algoSummariesRef.current.get(asset.strategy_id) ?? [];
      const timeframes = collectUniqueAlgoTimeframes(summaries, asset.algo_timeframe);
      const finestTf = finestTimeframe(timeframes);
      await Promise.allSettled([
        pollIndicators(asset, finestTf),
        ...timeframes.map((tf) => pollSignalsForTimeframe(asset, tf)),
      ]);
    },
    [pollIndicators, pollSignalsForTimeframe],
  );

  // ---------------------------------------------------------------------------
  // Per-asset order poll
  // ---------------------------------------------------------------------------

  const pollOrders = useCallback(async (asset: AutoTradingAssetRow) => {
    try {
      const page = orderPageByStrategyRef.current.get(asset.strategy_id) ?? 1;
      const offset = (page - 1) * TRANSACTIONS_PAGE_SIZE;
      const result = await executionApi.getOrders(
        asset.symbol,
        TRANSACTIONS_PAGE_SIZE,
        offset,
      );
      ordersRef.current.set(asset.strategy_id, result.orders);
      ordersTotalByStrategyRef.current.set(asset.strategy_id, result.total);
      publishMonitors();
    } catch {
      // Silently ignore
    }
  }, [publishMonitors]);

  const setOrdersPage = useCallback(
    async (strategyId: number, page: number) => {
      const asset = assetsRef.current.find((a) => a.strategy_id === strategyId);
      if (!asset) return;

      const total = ordersTotalByStrategyRef.current.get(strategyId) ?? 0;
      const maxPage = maxOrdersPage(total);
      const clamped = Math.min(Math.max(1, page), maxPage);
      orderPageByStrategyRef.current.set(strategyId, clamped);
      await pollOrders(asset);
    },
    [pollOrders],
  );

  // ---------------------------------------------------------------------------
  // Start monitoring a newly detected asset
  // ---------------------------------------------------------------------------

  const clearLiveIntervals = useCallback((strategyId: number) => {
    const tfIntervals = liveIntervalsRef.current.get(strategyId);
    if (tfIntervals) {
      for (const handle of tfIntervals.values()) clearInterval(handle);
      liveIntervalsRef.current.delete(strategyId);
    }
  }, []);

  const scheduleLivePoll = useCallback(
    (asset: AutoTradingAssetRow) => {
      clearLiveIntervals(asset.strategy_id);
      const summaries = algoSummariesRef.current.get(asset.strategy_id) ?? [];
      const timeframes = collectUniqueAlgoTimeframes(summaries, asset.algo_timeframe);
      const finestTf = finestTimeframe(timeframes);
      const tfIntervals = new Map<string, ReturnType<typeof setInterval>>();

      const indMs = resolveLivePollMs(finestTf, livePollMaxIntervalMs);
      tfIntervals.set(
        '__indicators__',
        setInterval(() => pollIndicators(asset, finestTf), indMs),
      );

      for (const tf of timeframes) {
        const ms = resolveLivePollMs(tf, livePollMaxIntervalMs);
        tfIntervals.set(
          tf,
          setInterval(() => pollSignalsForTimeframe(asset, tf), ms),
        );
      }

      liveIntervalsRef.current.set(asset.strategy_id, tfIntervals);
    },
    [clearLiveIntervals, livePollMaxIntervalMs, pollIndicators, pollSignalsForTimeframe],
  );

  const refreshLiveData = useCallback(async () => {
    await Promise.allSettled(
      assetsRef.current.map((asset) =>
        Promise.allSettled([pollLiveData(asset), pollOrders(asset)]),
      ),
    );
  }, [pollLiveData, pollOrders]);

  const startAssetMonitoring = useCallback(async (asset: AutoTradingAssetRow) => {
    // Fetch static full strategy data (attached algos + their params) once
    try {
      const full = await strategyBuilderApi.getFull(asset.strategy_id);
      algoSummariesRef.current.set(asset.strategy_id, full.algo_strategies);
    } catch {
      algoSummariesRef.current.set(asset.strategy_id, []);
    }

    // Initial fetch
    await Promise.allSettled([
      pollLiveData(asset),
      pollOrders(asset),
    ]);

    scheduleLivePoll(asset);

    // Order refresh interval
    const orderInterval = setInterval(() => pollOrders(asset), ORDER_INTERVAL_MS);
    orderIntervalsRef.current.set(asset.strategy_id, orderInterval);
  }, [pollLiveData, pollOrders, scheduleLivePoll]);

  // ---------------------------------------------------------------------------
  // Stop monitoring a removed asset
  // ---------------------------------------------------------------------------

  const stopAssetMonitoring = useCallback((strategyId: number) => {
    clearLiveIntervals(strategyId);
    const oi = orderIntervalsRef.current.get(strategyId);
    if (oi) { clearInterval(oi); orderIntervalsRef.current.delete(strategyId); }
    algoSummariesRef.current.delete(strategyId);
    liveByStrategyRef.current.delete(strategyId);
    priceRef.current.delete(strategyId);
    indicatorSnapshotRef.current.delete(strategyId);
    lastLivePollAtRef.current.delete(strategyId);
    ordersRef.current.delete(strategyId);
    ordersTotalByStrategyRef.current.delete(strategyId);
    orderPageByStrategyRef.current.delete(strategyId);
  }, [clearLiveIntervals]);

  // ---------------------------------------------------------------------------
  // Reconcile asset list: start monitoring new assets, stop removed ones
  // ---------------------------------------------------------------------------

  const reconcileAssets = useCallback(async (nextAssets: AutoTradingAssetRow[]) => {
    const prevIds = new Set(assetsRef.current.map((a) => a.strategy_id));
    const nextIds = new Set(nextAssets.map((a) => a.strategy_id));

    for (const prev of assetsRef.current) {
      if (!nextIds.has(prev.strategy_id)) {
        stopAssetMonitoring(prev.strategy_id);
      }
    }

    assetsRef.current = nextAssets;
    publishMonitors();

    const toStart = nextAssets.filter((a) => !prevIds.has(a.strategy_id));
    await Promise.allSettled(toStart.map(startAssetMonitoring));
  }, [stopAssetMonitoring, startAssetMonitoring, publishMonitors]);

  // ---------------------------------------------------------------------------
  // Asset list poll
  // ---------------------------------------------------------------------------

  const fetchAssets = useCallback(async () => {
    try {
      const rows = await autoTradingApi.list();
      const running = rows.filter((r) => r.auto_trading_started);
      await reconcileAssets(running);
      setAssetsError(null);
    } catch (e) {
      setAssetsError((e as Error).message);
    } finally {
      setAssetsLoading(false);
    }
  }, [reconcileAssets]);

  const refreshAll = useCallback(async () => {
    await fetchAssets();
    await refreshLiveData();
  }, [fetchAssets, refreshLiveData]);

  // ---------------------------------------------------------------------------
  // Mount / unmount
  // ---------------------------------------------------------------------------

  useEffect(() => {
    fetchAssets();
    assetListIntervalRef.current = setInterval(fetchAssets, ASSET_LIST_INTERVAL_MS);

    return () => {
      if (assetListIntervalRef.current) clearInterval(assetListIntervalRef.current);
      for (const strategyId of [...liveIntervalsRef.current.keys()]) {
        clearLiveIntervals(strategyId);
      }
      for (const id of orderIntervalsRef.current.values()) clearInterval(id);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    monitors,
    assetsLoading,
    assetsError,
    refresh: fetchAssets,
    refreshAll,
    refreshLiveData,
    setOrdersPage,
  };
}
