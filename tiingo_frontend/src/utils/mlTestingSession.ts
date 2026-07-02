import type { BacktestMetrics } from '../api/backtestTypes';
import type { MlParams, MlSummary } from '../api/mlBacktestTypes';
import type { DateRangeValue } from '../constants/timeframes';
import {
  DEFAULT_LABEL_MODE_BY_MODEL,
  defaultWalkForwardParams,
} from './mlBacktestConfig';
import {
  applyNoiseReductionDefaults,
  buildSimplifiedMlParams,
  resolveMacroSeriesForAsset,
} from './mlNoiseReductionPreset';

export const ML_TESTING_SESSION_VERSION = 1;
export const ML_TESTING_SESSION_KEY_PREFIX = 'ml-testing:v1:';
export const ML_TESTING_HYDRATE_KEY = 'ml-testing-hydrate-config';

export interface MlTestingConfigSnapshot {
  modelType: string;
  mlParams: MlParams;
  dateRange: DateRangeValue;
  timeframe: string;
  initialCash: number;
  commissionBps: number;
}

export interface MlTestingRun {
  clientId: string;
  backendRunId?: string;
  config: MlTestingConfigSnapshot;
  status: 'running' | 'completed' | 'failed';
  metrics?: BacktestMetrics | null;
  mlSummary?: MlSummary | null;
  error?: string;
  starred?: boolean;
  createdAt: string;
}

export interface MlTestingSession {
  version: number;
  symbol: string;
  timeframe: string;
  draftConfig: MlTestingConfigSnapshot;
  runs: MlTestingRun[];
}

export interface MlTestingDraftDefaults {
  symbol: string;
  timeframe: string;
  dateRange: DateRangeValue;
  modelType?: string;
  mlParams?: Partial<MlParams>;
  initialCash?: number;
  commissionBps?: number;
  assetType?: string;
}

export function createDefaultDraftConfig(
  defaults: MlTestingDraftDefaults,
): MlTestingConfigSnapshot {
  const modelType = defaults.modelType ?? 'ml_gradient_boosting';
  const assetType = defaults.assetType ?? 'equity';
  const labelMode = DEFAULT_LABEL_MODE_BY_MODEL[modelType] ?? 'binary';
  const simplified = buildSimplifiedMlParams({
    featureMode: defaults.mlParams?.feature_mode ?? 'prices_only',
    includeNewsSentiment: Boolean(defaults.mlParams?.include_news_sentiment),
    modelType,
    labelMode,
    timeframe: defaults.timeframe,
    assetType,
  });
  return {
    modelType,
    mlParams: applyNoiseReductionDefaults({
      ...simplified,
      ...defaultWalkForwardParams(defaults.timeframe, assetType),
      ...defaults.mlParams,
      macro_series_ids:
        defaults.mlParams?.macro_series_ids ?? resolveMacroSeriesForAsset(assetType),
    }),
    dateRange: defaults.dateRange,
    timeframe: defaults.timeframe,
    initialCash: defaults.initialCash ?? 10_000,
    commissionBps: defaults.commissionBps ?? 5,
  };
}

export function sessionStorageKey(symbol: string, timeframe: string): string {
  return `${ML_TESTING_SESSION_KEY_PREFIX}${symbol.toUpperCase()}:${timeframe}`;
}

export function createEmptySession(defaults: MlTestingDraftDefaults): MlTestingSession {
  return {
    version: ML_TESTING_SESSION_VERSION,
    symbol: defaults.symbol.toUpperCase(),
    timeframe: defaults.timeframe,
    draftConfig: createDefaultDraftConfig(defaults),
    runs: [],
  };
}

export function parseMlTestingSession(raw: string): MlTestingSession | null {
  try {
    const parsed = JSON.parse(raw) as MlTestingSession;
    if (parsed.version !== ML_TESTING_SESSION_VERSION) {
      return null;
    }
    if (!parsed.symbol || !parsed.timeframe || !parsed.draftConfig) {
      return null;
    }
    return {
      ...parsed,
      runs: Array.isArray(parsed.runs) ? parsed.runs : [],
    };
  } catch {
    return null;
  }
}

export function loadMlTestingSession(
  symbol: string,
  timeframe: string,
  storage: Storage = localStorage,
): MlTestingSession | null {
  const raw = storage.getItem(sessionStorageKey(symbol, timeframe));
  if (!raw) {
    return null;
  }
  const session = parseMlTestingSession(raw);
  if (!session) {
    return null;
  }
  if (session.symbol.toUpperCase() !== symbol.toUpperCase()) {
    return null;
  }
  return session;
}

export function saveMlTestingSession(
  session: MlTestingSession,
  storage: Storage = localStorage,
): void {
  storage.setItem(
    sessionStorageKey(session.symbol, session.timeframe),
    JSON.stringify(session),
  );
}

export function appendMlTestingRun(
  session: MlTestingSession,
  run: MlTestingRun,
): MlTestingSession {
  return { ...session, runs: [run, ...session.runs] };
}

export function updateMlTestingRun(
  session: MlTestingSession,
  clientId: string,
  patch: Partial<MlTestingRun>,
): MlTestingSession {
  return {
    ...session,
    runs: session.runs.map((row) =>
      row.clientId === clientId ? { ...row, ...patch } : row,
    ),
  };
}

export function deleteMlTestingRun(
  session: MlTestingSession,
  clientId: string,
): MlTestingSession {
  return {
    ...session,
    runs: session.runs.filter((row) => row.clientId !== clientId),
  };
}

export function toggleMlTestingRunStar(
  session: MlTestingSession,
  clientId: string,
): MlTestingSession {
  return {
    ...session,
    runs: session.runs.map((row) =>
      row.clientId === clientId ? { ...row, starred: !row.starred } : row,
    ),
  };
}

export function newClientRunId(): string {
  return `run-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}
