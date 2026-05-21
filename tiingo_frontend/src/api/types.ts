export interface Instrument {
  id: number;
  symbol: string;
  tiingo_ticker?: string;
  name?: string;
  asset_type: string;
  exchange?: string;
  currency: string;
  is_active: boolean;
  metadata?: Record<string, unknown>;
  job_id?: string;
}

export interface TickerSearchResult {
  symbol: string;
  name: string;
  asset_type: string;
  exchange?: string;
  tiingo_ticker?: string;
}

export interface TickerSearchResponse {
  results: TickerSearchResult[];
  count: number;
}

export interface IngestionStatus {
  scheduler_jobs: { id: string; name: string; next_run: string | null }[];
  api_usage: Record<string, number>;
  stream_status: { running: boolean; symbols: string[]; last_bar_time: Record<string, string> };
  instrument_count: number;
  active_instrument_count: number;
}

export interface Job {
  id: string;
  job_type: string;
  status: string;
  progress: number;
  params?: Record<string, unknown>;
  error_message?: string;
  result?: Record<string, unknown>;
  started_at?: string;
  finished_at?: string;
  created_at: string;
}

export interface NewsArticle {
  id: number;
  published_at: string;
  title: string;
  url: string;
  description?: string;
  tickers: string[];
  tags: string[];
}

export interface MacroSeries {
  series_id: string;
  title: string;
  frequency?: string;
  category: string;
  is_enabled: boolean;
}

export interface OHLCVBar {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  div_cash?: number;
  split_factor?: number;
  source: string;
}

export interface OHLCVQueryResponse {
  symbol: string;
  instrument_id: number;
  timeframe: string;
  source: string;
  records: OHLCVBar[];
  count: number;
}

export interface MacroObservation {
  obs_date: string;
  value: number | null;
}

export interface MacroObservationsResponse {
  series_id: string;
  observations: MacroObservation[];
  count: number;
}

export interface FundamentalsCoverageItem {
  symbol: string;
  name?: string;
  metric_count: number;
  first_report_date: string;
  latest_report_date: string;
  last_ingested_at: string;
}

export interface FundamentalsCoverageResponse {
  items: FundamentalsCoverageItem[];
  count: number;
}

export interface FundamentalMetric {
  time: string;
  metric_name: string;
  value: number;
  period?: string | null;
  statement_type?: string | null;
}

export interface FundamentalsMetricsResponse {
  symbol: string;
  period_type: string;
  metrics: FundamentalMetric[];
  count: number;
}

export type FundamentalsPeriodType = 'quarterly' | 'annual';

export interface PerformancePeriod {
  period: string;
  change_pct: number | null;
  price_change_pct: number | null;
  dividend_return_pct: number | null;
  total_return_pct: number | null;
  example_investment: number;
  example_outcome: number | null;
  example_dividend_income: number | null;
}

export interface PerformanceResponse {
  symbol: string;
  currency: string;
  as_of: string | null;
  periods: PerformancePeriod[];
}

export interface StockKpiItem {
  key: string;
  label: string;
  value: number | null;
  format: 'ratio' | 'percent' | 'currency' | 'perShare';
}

export interface StockKpisResponse {
  symbol: string;
  as_of: string | null;
  price: number | null;
  kpis: StockKpiItem[];
}

export type SeriesSource = 'macro' | 'instrument';

export interface DashboardSeriesRef {
  source: SeriesSource;
  id: string;
  label: string;
  assetType?: string;
}
