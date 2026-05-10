export interface AssetItem {
  id: number;
  symbol: string;
  name: string | null;
  asset_type: string;
  exchange: string | null;
  currency: string;
  is_active: boolean;
}

export interface AssetListResponse {
  assets: AssetItem[];
  count: number;
}

export interface OHLCVRecord {
  time: string;
  asset_id: number;
  timeframe: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  vwap?: number;
  source: string;
}

export interface OHLCVQueryResponse {
  asset_id: number;
  symbol: string;
  timeframe: string;
  records: OHLCVRecord[];
  count: number;
}

export interface IngestRequest {
  symbols: string[];
  timeframes: string[];
  provider?: string;
  start_date?: string;
  end_date?: string;
}

export interface IngestResponse {
  job_id: string;
  status: string;
  symbols: string[];
  timeframes: string[];
  message: string;
}

export interface DeleteAssetResponse {
  symbol: string;
  deleted: boolean;
  message: string;
}

export interface IngestionStatusResponse {
  status: string;
  last_run?: string;
  active_jobs: number;
  scheduled_jobs: { id: string; name: string; next_run: string | null }[];
}

export interface SimulationStats {
  mean_terminal: number;
  std_terminal: number;
  p5: number;
  p25: number;
  p50: number;
  p75: number;
  p95: number;
  prob_positive_return: number;
  mean_max_drawdown: number;
}

export interface SimulationRequest {
  symbol: string;
  timeframe?: string;
  num_paths?: number;
  horizon_steps?: number;
  use_stored_params?: boolean;
  include_distribution?: boolean;
  calibration_years?: number;
}

export interface DistributionPoint {
  x: number;
  density: number;
}

export interface ReturnDistribution {
  histogram: DistributionPoint[];
  mr_density: DistributionPoint[];
  jump_up_density: DistributionPoint[];
  jump_down_density: DistributionPoint[];
}

export interface SimulationResponse {
  simulation_id: number;
  asset_id: number;
  status: string;
  params: Record<string, unknown>;
  stats?: SimulationStats;
  percentile_paths?: Record<string, number[]>;
  duration_ms?: number;
  return_distribution?: ReturnDistribution;
}

export interface BacktestRequest {
  symbol?: string;
  asset_id?: number;
  simulation_id?: number;
  strategy_name: string;
  timeframe: string;
  start_date: string;
  end_date: string;
  strategy_params: Record<string, unknown>;
  initial_capital?: number;
}

export interface OptimizationRequest {
  symbol?: string;
  asset_id?: number;
  strategy_name: string;
  timeframe: string;
  start_date: string;
  end_date: string;
  param_grid: Record<string, number[]>;
  n_splits?: number;
  optimize_metric?: string;
  initial_capital?: number;
}

export interface OptimizationSummary {
  params: Record<string, number>;
  avg_oos_metric: number;
}

export interface OptimizationResponse {
  optimization_id: number;
  asset_id: number;
  strategy_name: string;
  status: string;
  optimize_metric?: string;
  n_splits?: number;
  best_params?: Record<string, number>;
  best_metric?: number;
  all_results?: OptimizationSummary[];
  duration_ms?: number;
  error_message?: string;
}

export interface AgentAnalysisRequest {
  symbol: string;
  llm?: string;
}

export interface TradingSignal {
  asset: string;
  bias: 'bullish' | 'bearish' | 'neutral';
  conviction_score: number;
  fundamental_summary: string;
  macro_summary: string;
  sentiment_score: number;
  reasoning: string;
  key_risk: string;
  timestamp: string;
}

export interface AgentReports {
  fundamental?: string | null;
  macro?: string | null;
  sentiment?: string | null;
}

export interface AgentAnalysisResponse {
  analysis_id: number;
  symbol: string;
  status: string;
  signal?: TradingSignal;
  reports?: AgentReports;
  duration_ms?: number;
  error_message?: string;
  provider_used?: string | null;
}

export interface TickerSearchResult {
  symbol: string;
  name: string;
  asset_type: string;
  exchange: string | null;
}

export interface TickerSearchResponse {
  results: TickerSearchResult[];
  count: number;
}

// ── Live Trading (Phase 5) ──────────────────────────────────────────────

export interface StreamStartRequest {
  symbols: string[];
  timeframes?: string[];
}

export interface StreamStatusResponse {
  connected: boolean;
  subscribed_symbols: string[];
  last_tick_at: string | null;
  error: string | null;
  reconnect_count: number;
}

export interface IndicatorSnapshotResponse {
  symbol: string;
  timeframe: string;
  close_price: number;
  rsi: number | null;
  macd: number | null;
  macd_signal: number | null;
  macd_histogram: number | null;
  bb_upper: number | null;
  bb_middle: number | null;
  bb_lower: number | null;
  vwap: number | null;
  bb_percent: number | null;
  created_at?: string;
}

export interface TradingSignalItem {
  id: number;
  symbol: string;
  timeframe: string;
  action: 'BUY' | 'SELL' | 'HOLD';
  confidence: number;
  technical_score: number;
  risk_score: number;
  ai_score: number;
  reasoning: string | null;
  indicator_snapshot: Record<string, unknown> | null;
  risk_data: Record<string, unknown> | null;
  ai_signal: Record<string, unknown> | null;
  created_at: string;
}

export interface SignalHistoryResponse {
  signals: TradingSignalItem[];
  total: number;
}

// ── Execution (Phase 6) ─────────────────────────────────────────────────

export interface OrderItem {
  id: number;
  symbol: string;
  side: string;
  qty: number;
  order_type: string;
  limit_price: number | null;
  stop_price: number | null;
  status: string;
  alpaca_order_id: string | null;
  filled_price: number | null;
  filled_qty: number | null;
  filled_at: string | null;
  signal_id: number | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface OrderHistoryResponse {
  orders: OrderItem[];
  total: number;
}

export interface PositionItem {
  symbol: string;
  qty: number;
  market_value: number;
  avg_entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
}

export interface PortfolioResponse {
  equity: number;
  cash: number;
  buying_power: number;
  daily_pnl: number | null;
  daily_pnl_pct: number | null;
  total_positions: number;
  positions: PositionItem[];
  updated_at?: string;
}

export interface RiskConfigResponse {
  trading_mode: string;
  max_position_pct: number;
  max_exposure_pct: number;
  daily_loss_limit_pct: number;
  max_orders_per_minute: number;
  kill_switch_active: boolean;
}

export interface RiskConfigUpdateRequest {
  max_position_pct?: number;
  max_exposure_pct?: number;
  daily_loss_limit_pct?: number;
  max_orders_per_minute?: number;
}

export interface RiskEventItem {
  id: number;
  event_type: string;
  severity: string;
  symbol: string | null;
  description: string;
  details: Record<string, unknown> | null;
  created_at: string;
}

export interface RiskEventHistoryResponse {
  events: RiskEventItem[];
  total: number;
}

export interface ExecutionStatusResponse {
  trading_mode: string;
  kill_switch_active: boolean;
  stream_connected: boolean;
  subscribed_symbols: string[];
  recent_orders?: number;
  portfolio?: PortfolioResponse;
}

// ── Financials ────────────────────────────────────────────────────────────────

export interface FundamentalsOverview {
  symbol: string;
  asset_id: number;
  metrics: Record<string, number>;
  fetched_at: string | null;
}

export interface FinancialStatementRow {
  metric: string;
  values: Record<string, number>;
}

export interface FinancialStatement {
  symbol: string;
  asset_id: number;
  statement_type: string;
  periods: string[];
  rows: FinancialStatementRow[];
}

export interface CompanyOfficer {
  name: string;
  title: string;
  age?: number;
  totalPay?: number;
}

export interface CompanyProfile {
  symbol: string;
  asset_id: number;
  sector: string | null;
  industry: string | null;
  business_summary: string | null;
  website: string | null;
  country: string | null;
  employees: number | null;
  officers: CompanyOfficer[] | null;
  fetched_at: string | null;
}

export interface FinancialsIngestResponse {
  symbol: string;
  fundamentals_inserted: number;
  profile_updated: boolean;
  status: string;
}

export interface BacktestMetrics {
  sharpe_ratio?: number;
  sortino_ratio?: number;
  max_drawdown?: number;
  win_rate?: number;
  profit_factor?: number;
  total_return?: number;
  annualized_return?: number;
  num_trades?: number;
}

export interface BacktestResponse {
  backtest_id: number;
  asset_id: number;
  strategy_name: string;
  status: string;
  metrics?: BacktestMetrics;
  equity_curve?: { time: string; value: number }[];
  trade_log?: unknown[];
  duration_ms?: number;
  error_message?: string;
}
