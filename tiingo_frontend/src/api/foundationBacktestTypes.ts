import type {
  BacktestEquityPoint,
  BacktestMetrics,
  BacktestTrade,
} from './backtestTypes';

export interface FoundationParamConstraint {
  min: number;
  max: number;
}

export interface FoundationModelCatalogItem {
  id: string;
  label: string;
  description: string;
  params: Record<string, unknown>;
  constraints: Record<string, FoundationParamConstraint>;
}

export interface FoundationModelCatalogResponse {
  models: FoundationModelCatalogItem[];
}

export interface FoundationRunRequest {
  symbol: string;
  model_type: string;
  params?: Record<string, unknown>;
  timeframe?: string;
  start?: string;
  end?: string;
  initial_cash?: number;
  commission_bps?: number;
}

export interface FoundationPreviewRequest {
  symbol: string;
  model_type: string;
  params?: Record<string, unknown>;
  timeframe?: string;
  start?: string;
  end?: string;
}

export interface FoundationForecastPoint {
  date: string;
  actual?: number | null;
  forecast?: number | null;
  lower?: number | null;
  upper?: number | null;
}

export interface FoundationForecastMetrics {
  mae?: number | null;
  mape?: number | null;
  directional_accuracy?: number | null;
  evaluated_points: number;
}

export interface FoundationWalkForwardMeta {
  context_length: number;
  forecast_horizon: number;
  signal_mode: string;
  target_series: string;
  bars_evaluated: number;
  warmup_bars: number;
}

export interface FoundationSummary {
  model_type: string;
  signal_counts: Record<string, number>;
  forecast_metrics: FoundationForecastMetrics;
  walk_forward: FoundationWalkForwardMeta;
  simulation_start_bar_index?: number | null;
  simulation_start_date?: string | null;
  pre_oos_bars_excluded?: number | null;
  forecast_samples: FoundationForecastPoint[];
}

export interface FoundationPreviewResponse {
  symbol: string;
  model_type: string;
  context_points: FoundationForecastPoint[];
  forecast_points: FoundationForecastPoint[];
  context_length: number;
  forecast_horizon: number;
}

export interface FoundationBacktestResultsResponse {
  id: string;
  symbol: string;
  model_type: string;
  params: Record<string, unknown>;
  timeframe: string;
  start_date?: string | null;
  end_date?: string | null;
  initial_cash: number;
  commission_bps: number;
  status: string;
  metrics?: BacktestMetrics | null;
  equity_curve: BacktestEquityPoint[];
  benchmark_equity_curve: BacktestEquityPoint[];
  trades: BacktestTrade[];
  foundation_summary?: FoundationSummary | null;
  error_message?: string | null;
  created_at: string;
  finished_at?: string | null;
}

export interface FoundationRunJobResult {
  run_id: string;
  symbol: string;
  model_type: string;
  status: string;
}
