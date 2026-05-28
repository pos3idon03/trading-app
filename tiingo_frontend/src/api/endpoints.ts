import { enqueueAndWait } from '../hooks/useMlJob';
import { api } from './client';
import type {
  FundamentalsCoverageResponse,
  FundamentalsMetricsResponse,
  FundamentalsPeriodType,
  IngestionStatus,
  Instrument,
  Job,
  MacroObservationsResponse,
  MacroSeries,
  NewsArticle,
  AssetOverviewResponse,
  MacroOverviewResponse,
  OHLCVQueryResponse,
  PerformanceResponse,
  StockKpisResponse,
  TickerSearchResponse,
} from './types';
import type {
  BacktestResultsResponse,
  BacktestRunRequest,
  BacktestRunResponse,
  StrategyCatalogResponse,
} from './backtestTypes';

import type {
  MlBacktestResultsResponse,
  MlDataPreviewRequest,
  MlDataPreviewResponse,
  MlHyperparameterSearchRequest,
  MlHyperparameterSearchResponse,
  MlLabelSearchRequest,
  MlLabelSearchResponse,
  MlModelCatalogResponse,
  MlRunRequest,
  MlRunResponse,
  MlSavedModel,
  MlSavedModelsResponse,
  MlThresholdSearchRequest,
  MlThresholdSearchResponse,
  MlTrainRequest,
  MlTrainResponse,
  MlTrainingExportRequest,
  MlTrainingExportResponse,
  MlWorkbookExportRequest,
  MlWorkbookExportResponse,
} from './mlBacktestTypes';

import type {
  FoundationBacktestResultsResponse,
  FoundationModelCatalogResponse,
  FoundationPreviewRequest,
  FoundationPreviewResponse,
  FoundationRunRequest,
  FoundationRunJobResult,
} from './foundationBacktestTypes';

import type {
  CreateDeploymentRequest,
  EvaluateDeploymentResponse,
  EnqueueJobResponse,
  ExecutionActivityEvent,
  ExecutionEvaluationsResponse,
  ExecutionOrdersResponse,
  ExecutionStatus,
  PortfolioResponse,
  RiskConfig,
  TradingDeployment,
  TradingDeploymentsResponse,
} from './executionTypes';

export const ingestionApi = {
  getStatus: () => api.get<IngestionStatus>('/ingestion/status').then((r) => r.data),
  listInstruments: (activeOnly = false) =>
    api.get<Instrument[]>('/instruments', { params: { active_only: activeOnly } }).then((r) => r.data),
  searchInstruments: (query: string, limit = 10) =>
    api
      .get<TickerSearchResponse>('/instruments/search', { params: { query, limit } })
      .then((r) => r.data),
  searchDbInstruments: (query: string, assetTypes?: string[], limit = 20) =>
    api
      .get<Instrument[]>('/instruments/db-search', {
        params: { query, limit, asset_type: assetTypes },
      })
      .then((r) => r.data),
  createInstrument: (body: {
    symbol: string;
    asset_type?: string;
    name?: string;
    exchange?: string;
    tiingo_ticker?: string;
    auto_ingest?: boolean;
  }) =>
    api.post<Instrument>('/instruments', body).then((r) => r.data),
  ingestAsset: (symbol: string) =>
    api.post<{ job_id: string }>('/ingestion/asset/ingest', { symbol }).then((r) => r.data),
  patchInstrument: (symbol: string, body: { is_active?: boolean }) =>
    api.patch<Instrument>(`/instruments/${symbol}`, body).then((r) => r.data),
  deleteInstrument: (symbol: string) => api.delete(`/instruments/${symbol}`),
  backfillOhlcv: (body: Record<string, unknown>) =>
    api.post<{ job_id: string }>('/ingestion/ohlcv/backfill', body).then((r) => r.data),
  getCoverage: (symbol: string, timeframe = '1d', effective = false) =>
    api
      .get(`/ingestion/ohlcv/coverage/${symbol}`, { params: { timeframe, effective } })
      .then((r) => r.data),
  runNews: (body: Record<string, unknown>) =>
    api.post<{ job_id: string }>('/ingestion/news/run', body).then((r) => r.data),
  listNews: (limit = 50) =>
    api.get<{ articles: NewsArticle[] }>('/ingestion/news', { params: { limit } }).then((r) => r.data),
  runFundamentals: (body: Record<string, unknown>) =>
    api.post<{ job_id: string }>('/ingestion/fundamentals/run', body).then((r) => r.data),
  getFundamentalsEntitlement: () =>
    api.get('/ingestion/fundamentals/entitlement').then((r) => r.data),
  listFundamentalsCoverage: () =>
    api
      .get<FundamentalsCoverageResponse>('/ingestion/fundamentals/coverage')
      .then((r) => r.data),
  getFundamentals: (
    symbol: string,
    params?: {
      period_type?: FundamentalsPeriodType;
      metric_names?: string;
      order?: 'asc' | 'desc';
      limit?: number;
      all?: boolean;
    },
  ) =>
    api
      .get<FundamentalsMetricsResponse>(`/ingestion/fundamentals/${symbol}`, { params })
      .then((r) => r.data),
  streamStart: (symbols: string[]) =>
    api.post('/ingestion/stream/start', { symbols }).then((r) => r.data),
  streamStop: () => api.post('/ingestion/stream/stop').then((r) => r.data),
  streamStatus: () => api.get('/ingestion/stream/status').then((r) => r.data),
  listJobs: (params?: { status?: string; limit?: number }) =>
    api.get<Job[]>('/ingestion/jobs', { params }).then((r) => r.data),
  listActiveJobs: () => api.get<Job[]>('/ingestion/jobs/active').then((r) => r.data),
  getJob: (id: string) => api.get<Job>(`/ingestion/jobs/${id}`).then((r) => r.data),
  listMacroSeries: (params?: { ingestedOnly?: boolean; query?: string; limit?: number }) =>
    api
      .get<MacroSeries[]>('/ingestion/macro/series', {
        params: {
          ingested_only: params?.ingestedOnly,
          query: params?.query,
          limit: params?.limit,
        },
      })
      .then((r) => r.data),
  macroBackfill: (seriesIds: string[]) =>
    api.post<{ job_id: string }>('/ingestion/macro/backfill', { series_ids: seriesIds }).then((r) => r.data),
  macroAlfredBackfill: (seriesIds: string[]) =>
    api.post<{ job_id: string }>('/ingestion/macro/alfred-backfill', { series_ids: seriesIds }).then((r) => r.data),
  macroRefresh: () => api.post<{ job_id: string }>('/ingestion/macro/refresh').then((r) => r.data),
  macroSeedCatalog: () =>
    api.post<{ job_id: string }>('/ingestion/macro/seed').then((r) => r.data),
  macroObservations: (
    seriesId: string,
    params?: {
      limit?: number;
      order?: 'asc' | 'desc';
      start?: string;
      end?: string;
      all?: boolean;
    },
  ) =>
    api
      .get<MacroObservationsResponse>(`/ingestion/macro/observations/${seriesId}`, { params })
      .then((r) => r.data),
};

export const marketDataApi = {
  getOhlcv: (
    symbol: string,
    params?: {
      timeframe?: string;
      source?: string;
      start?: string;
      end?: string;
      limit?: number;
    },
  ) =>
    api
      .get<OHLCVQueryResponse>(`/market-data/ohlcv/${symbol}`, { params })
      .then((r) => r.data),
  getPerformance: (symbol: string) =>
    api
      .get<PerformanceResponse>(`/market-data/performance/${symbol}`)
      .then((r) => r.data),
  getKpis: (symbol: string) =>
    api.get<StockKpisResponse>(`/market-data/kpis/${symbol}`).then((r) => r.data),
  getAssetOverview: (assetType: 'stock' | 'etf' | 'crypto') =>
    api
      .get<AssetOverviewResponse>('/market-data/overview/assets', {
        params: { asset_type: assetType },
      })
      .then((r) => r.data),
  getMacroOverview: (category = 'all') =>
    api
      .get<MacroOverviewResponse>('/market-data/overview/macro', {
        params: { category },
      })
      .then((r) => r.data),
};

export const backtestApi = {
  listStrategies: () =>
    api.get<StrategyCatalogResponse>('/backtest/strategies').then((r) => r.data),
  run: (body: BacktestRunRequest) =>
    api.post<BacktestRunResponse>('/backtest/run', body).then((r) => r.data),
  getResults: (id: string) =>
    api.get<BacktestResultsResponse>(`/backtest/${id}/results`).then((r) => r.data),
};

export const mlBacktestApi = {
  listModels: () =>
    api.get<MlModelCatalogResponse>('/backtest/ml/models').then((r) => r.data),
  listSavedModels: () =>
    api.get<MlSavedModelsResponse>('/backtest/ml/saved-models').then((r) => r.data),
  getSavedModel: (id: string) =>
    api.get<MlSavedModel>(`/backtest/ml/saved-models/${id}`).then((r) => r.data),
  deleteSavedModel: (id: string) =>
    api.delete(`/backtest/ml/saved-models/${id}`).then(() => undefined),
  dataPreview: (body: MlDataPreviewRequest, onProgress?: (job: Job) => void) =>
    enqueueAndWait<MlDataPreviewResponse>(
      () => api.post<{ job_id: string }>('/backtest/ml/data-preview', body).then((r) => r.data),
      onProgress,
    ),
  labelSearch: (body: MlLabelSearchRequest, onProgress?: (job: Job) => void) =>
    enqueueAndWait<MlLabelSearchResponse>(
      () => api.post<{ job_id: string }>('/backtest/ml/label-search', body).then((r) => r.data),
      onProgress,
    ).then((result) => ({
      results: result.results ?? [],
    })),
  thresholdSearch: (body: MlThresholdSearchRequest, onProgress?: (job: Job) => void) =>
    enqueueAndWait<MlThresholdSearchResponse>(
      () => api.post<{ job_id: string }>('/backtest/ml/threshold-search', body).then((r) => r.data),
      onProgress,
    ).then((result) => ({
      results: result.results ?? [],
    })),
  hyperparameterSearch: (body: MlHyperparameterSearchRequest, onProgress?: (job: Job) => void) =>
    enqueueAndWait<MlHyperparameterSearchResponse>(
      () => api.post<{ job_id: string }>('/backtest/ml/hyperparameter-search', body).then((r) => r.data),
      onProgress,
    ),
  trainingDataExport: (body: MlTrainingExportRequest, onProgress?: (job: Job) => void) =>
    enqueueAndWait<MlTrainingExportResponse>(
      () => api.post<{ job_id: string }>('/backtest/ml/training-data-export', body).then((r) => r.data),
      onProgress,
    ),
  workbookExport: (body: MlWorkbookExportRequest, onProgress?: (job: Job) => void) =>
    enqueueAndWait<MlWorkbookExportResponse>(
      () => api.post<{ job_id: string }>('/backtest/ml/workbook-export', body).then((r) => r.data),
      onProgress,
    ),
  train: (body: MlTrainRequest, onProgress?: (job: Job) => void) =>
    enqueueAndWait<MlTrainResponse>(
      () => api.post<{ job_id: string }>('/backtest/ml/train', body).then((r) => r.data),
      onProgress,
    ),
  run: (body: MlRunRequest, onProgress?: (job: Job) => void) =>
    enqueueAndWait<MlRunResponse>(
      () => api.post<{ job_id: string }>('/backtest/ml/run', body).then((r) => r.data),
      onProgress,
    ).then((result) => ({
      id: result.run_id ?? result.id,
      symbol: result.symbol,
      model_type: result.model_type,
      status: result.status,
      metrics: result.metrics ?? null,
    })),
  getResults: (id: string) =>
    api.get<MlBacktestResultsResponse>(`/backtest/ml/${id}/results`).then((r) => r.data),
};

export const foundationBacktestApi = {
  listModels: () =>
    api.get<FoundationModelCatalogResponse>('/backtest/foundation/models').then((r) => r.data),
  preview: (body: FoundationPreviewRequest, onProgress?: (job: Job) => void) =>
    enqueueAndWait<FoundationPreviewResponse>(
      () => api.post<{ job_id: string }>('/backtest/foundation/preview', body).then((r) => r.data),
      onProgress,
    ),
  run: (body: FoundationRunRequest, onProgress?: (job: Job) => void) =>
    enqueueAndWait<FoundationRunJobResult>(
      () => api.post<{ job_id: string }>('/backtest/foundation/run', body).then((r) => r.data),
      onProgress,
    ),
  getResults: (id: string) =>
    api
      .get<FoundationBacktestResultsResponse>(`/backtest/foundation/${id}/results`)
      .then((r) => r.data),
};

export const executionApi = {
  getStatus: () => api.get<ExecutionStatus>('/execution/status').then((r) => r.data),
  getRiskConfig: () => api.get<RiskConfig>('/execution/risk-config').then((r) => r.data),
  setKillSwitch: (enabled: boolean) =>
    api.post<{ kill_switch_enabled: boolean }>('/execution/kill-switch', { enabled }).then((r) => r.data),
  getPortfolio: () => api.get<PortfolioResponse>('/execution/portfolio').then((r) => r.data),
  listDeployments: () =>
    api.get<TradingDeploymentsResponse>('/execution/deployments').then((r) => r.data),
  createDeployment: (body: CreateDeploymentRequest) =>
    api.post<TradingDeployment>('/execution/deployments', body).then((r) => r.data),
  activateDeployment: (id: string) =>
    api.post<TradingDeployment>(`/execution/deployments/${id}/activate`).then((r) => r.data),
  pauseDeployment: (id: string) =>
    api.post<TradingDeployment>(`/execution/deployments/${id}/pause`).then((r) => r.data),
  stopDeployment: (id: string) =>
    api.post<TradingDeployment>(`/execution/deployments/${id}/stop`).then((r) => r.data),
  evaluateDeployment: (id: string) =>
    api
      .post<EvaluateDeploymentResponse>(`/execution/deployments/${id}/evaluate`)
      .then((r) => r.data),
  enqueueEvaluateAll: () =>
    api.post<EnqueueJobResponse>('/execution/evaluate-all/enqueue').then((r) => r.data),
  listOrders: (params?: { deployment_id?: string; symbol?: string; status?: string }) =>
    api.get<ExecutionOrdersResponse>('/execution/orders', { params }).then((r) => r.data),
  listEvaluations: (params?: { deployment_id?: string; symbol?: string; limit?: number }) =>
    api.get<ExecutionEvaluationsResponse>('/execution/evaluations', { params }).then((r) => r.data),
};

export function executionActivityWsUrl(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/api/v1/execution/ws`;
}
