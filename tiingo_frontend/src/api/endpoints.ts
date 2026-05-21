import { api } from './client';
import type {
  IngestionStatus,
  Instrument,
  Job,
  MacroObservationsResponse,
  MacroSeries,
  NewsArticle,
  OHLCVQueryResponse,
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
  createInstrument: (body: {
    symbol: string;
    asset_type?: string;
    name?: string;
    exchange?: string;
    tiingo_ticker?: string;
  }) =>
    api.post<Instrument>('/instruments', body).then((r) => r.data),
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
  getFundamentals: (symbol: string) =>
    api.get(`/ingestion/fundamentals/${symbol}`).then((r) => r.data),
  streamStart: (symbols: string[]) =>
    api.post('/ingestion/stream/start', { symbols }).then((r) => r.data),
  streamStop: () => api.post('/ingestion/stream/stop').then((r) => r.data),
  streamStatus: () => api.get('/ingestion/stream/status').then((r) => r.data),
  listJobs: () => api.get<Job[]>('/ingestion/jobs').then((r) => r.data),
  getJob: (id: string) => api.get<Job>(`/ingestion/jobs/${id}`).then((r) => r.data),
  listMacroSeries: () => api.get<MacroSeries[]>('/ingestion/macro/series').then((r) => r.data),
  macroBackfill: (seriesIds: string[]) =>
    api.post<{ job_id: string }>('/ingestion/macro/backfill', { series_ids: seriesIds }).then((r) => r.data),
  macroRefresh: () => api.post<{ job_id: string }>('/ingestion/macro/refresh').then((r) => r.data),
  macroObservations: (seriesId: string, params?: { limit?: number; order?: 'asc' | 'desc' }) =>
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
};
