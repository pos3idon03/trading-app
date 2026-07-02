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

export interface NewsSentiment {
  label: string;
  score_positive: number;
  score_negative: number;
  score_neutral: number;
  confidence: number;
  model_name?: string;
  model_version?: string;
  source?: string;
}

export interface NewsSentimentRefined {
  label: string;
  refined_label?: string;
  refined_confidence: number;
  rationale?: string | null;
  citations?: { title?: string | null; url?: string | null }[];
  source?: string;
}

export interface NewsEffectiveSentiment {
  label: string;
  confidence: number;
  source: string;
}

export interface NewsArticle {
  id: number;
  published_at: string;
  title: string;
  url: string;
  description?: string;
  tickers: string[];
  tags: string[];
  sentiment?: NewsSentiment | null;
  sentiment_refined?: NewsSentimentRefined | null;
  effective_label?: string | null;
  effective_sentiment?: NewsEffectiveSentiment | null;
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

export interface MetricGrowth {
  latest_period?: string | null;
  yoy: number | null;
  qoq: number | null;
  cagr: number | null;
}

export interface AssetOverviewRow {
  symbol: string;
  name?: string | null;
  as_of?: string | null;
  pe_ratio?: number | null;
  dividend_yield?: number | null;
  debt_equity?: number | null;
  current_ratio?: number | null;
  eps_ttm?: number | null;
  revenue_growth?: MetricGrowth | null;
  ebitda_growth?: MetricGrowth | null;
  ocf_growth?: MetricGrowth | null;
  price_change_6m?: number | null;
  performance?: Record<string, number | null> | null;
}

export interface AssetOverviewResponse {
  asset_type: string;
  as_of: string | null;
  rows: AssetOverviewRow[];
}

export interface MacroOverviewRow {
  series_id: string;
  title: string;
  category: string;
  frequency?: string | null;
  change_1m: number | null;
  change_3m: number | null;
  change_6m: number | null;
  change_ytd: number | null;
  ma50_position: string;
  ma200_position: string;
}

export interface MacroOverviewResponse {
  category: string;
  as_of: string | null;
  rows: MacroOverviewRow[];
}

export interface MacroBriefResponse {
  as_of: string | null;
  situation: string | null;
  outlook: string | null;
  situation_phase?: MacroCyclePhase | null;
  outlook_phase?: MacroCyclePhase | null;
  generated_at: string | null;
  available: boolean;
  message?: string | null;
}

export interface MarketSentimentPoint {
  recorded_at: string;
  score: number;
  article_count: number;
  bullish_count: number;
  bearish_count: number;
  neutral_count: number;
}

export interface MarketSentimentResponse {
  window_hours: number;
  current_score: number;
  current_article_count: number;
  points: MarketSentimentPoint[];
  available: boolean;
  message?: string | null;
}

export type MacroCyclePhase =
  | 'Expansion'
  | 'Peak'
  | 'Slowdown'
  | 'Recession'
  | 'Trough'
  | 'Stagnation';

export type SeriesSource = 'macro' | 'instrument';

export interface DashboardSeriesRef {
  source: SeriesSource;
  id: string;
  label: string;
  assetType?: string;
}
