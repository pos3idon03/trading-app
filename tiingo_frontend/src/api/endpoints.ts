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
  OHLCVQueryResponse,
  PerformanceResponse,
  StockKpisResponse,
  TickerSearchResponse,
} from './types';

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
  getCoverage: (symbol: string, timeframe = '1d') =>
    api.get(`/ingestion/ohlcv/coverage/${symbol}`, { params: { timeframe } }).then((r) => r.data),
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
};
