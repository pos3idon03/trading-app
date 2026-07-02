import { useCallback, useEffect, useState } from 'react';
import type { MlBacktestResultsResponse } from '../api/mlBacktestTypes';
import type { DateRangeValue } from '../constants/timeframes';
import {
  appendMlTestingRun,
  createEmptySession,
  deleteMlTestingRun,
  loadMlTestingSession,
  newClientRunId,
  saveMlTestingSession,
  toggleMlTestingRunStar,
  updateMlTestingRun,
  type MlTestingConfigSnapshot,
  type MlTestingRun,
  type MlTestingSession,
} from '../utils/mlTestingSession';

interface UseMlTestingSessionOptions {
  symbol: string;
  timeframe: string;
  dateRange: DateRangeValue;
  modelType: string;
  assetType?: string;
}

export function useMlTestingSession({
  symbol,
  timeframe,
  dateRange,
  modelType,
  assetType = 'equity',
}: UseMlTestingSessionOptions) {
  const [session, setSession] = useState<MlTestingSession | null>(null);

  useEffect(() => {
    if (!symbol) {
      setSession(null);
      return;
    }
    const existing = loadMlTestingSession(symbol, timeframe);
    if (existing) {
      setSession(existing);
      return;
    }
    setSession(
      createEmptySession({
        symbol,
        timeframe,
        dateRange,
        modelType,
        assetType,
      }),
    );
  }, [symbol, timeframe, assetType]);

  const updateSession = useCallback(
    (updater: (prev: MlTestingSession) => MlTestingSession) => {
      setSession((prev) => {
        if (!prev) {
          return prev;
        }
        const next = updater(prev);
        saveMlTestingSession(next);
        return next;
      });
    },
    [],
  );

  const setDraftConfig = useCallback(
    (draftConfig: MlTestingConfigSnapshot) => {
      updateSession((prev) => ({ ...prev, draftConfig }));
    },
    [updateSession],
  );

  const addPendingRun = useCallback(
    (config: MlTestingConfigSnapshot): string => {
      const clientId = newClientRunId();
      const run: MlTestingRun = {
        clientId,
        config,
        status: 'running',
        createdAt: new Date().toISOString(),
      };
      updateSession((prev) => appendMlTestingRun(prev, run));
      return clientId;
    },
    [updateSession],
  );

  const completeRun = useCallback(
    (clientId: string, results: MlBacktestResultsResponse) => {
      updateSession((prev) =>
        updateMlTestingRun(prev, clientId, {
          status: 'completed',
          backendRunId: results.id,
          metrics: results.metrics,
          mlSummary: results.ml_summary ?? null,
          error: undefined,
        }),
      );
    },
    [updateSession],
  );

  const failRun = useCallback(
    (clientId: string, error: string) => {
      updateSession((prev) =>
        updateMlTestingRun(prev, clientId, {
          status: 'failed',
          error,
        }),
      );
    },
    [updateSession],
  );

  const removeRun = useCallback(
    (clientId: string) => {
      updateSession((prev) => deleteMlTestingRun(prev, clientId));
    },
    [updateSession],
  );

  const starRun = useCallback(
    (clientId: string) => {
      updateSession((prev) => toggleMlTestingRunStar(prev, clientId));
    },
    [updateSession],
  );

  const loadConfigFromRun = useCallback(
    (clientId: string) => {
      updateSession((prev) => {
        const run = prev.runs.find((row) => row.clientId === clientId);
        if (!run) {
          return prev;
        }
        return { ...prev, draftConfig: run.config };
      });
    },
    [updateSession],
  );

  return {
    session,
    draftConfig: session?.draftConfig ?? null,
    runs: session?.runs ?? [],
    setDraftConfig,
    addPendingRun,
    completeRun,
    failRun,
    removeRun,
    starRun,
    loadConfigFromRun,
  };
}
