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

export interface AssetWithPrice {
  id: number;
  symbol: string;
  name: string | null;
  asset_type: string;
  exchange: string | null;
  currency: string;
  is_active: boolean;
  latest_close: number | null;
  latest_update: string | null;
}

export interface AssetWithPriceListResponse {
  assets: AssetWithPrice[];
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
  model_type?: 'vasicek' | 'merton';
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
  /** Worst allowed avg OOS max drawdown (negative decimal, e.g. -0.25). */
  max_drawdown_cap?: number;
}

export type CombinationMode = 'and' | 'majority' | 'weighted';

export interface ComboStrategyEntry {
  strategy_name: string;
  strategy_params: Record<string, unknown>;
  weight?: number;
}

export interface ComboBacktestRequest {
  symbol?: string;
  asset_id?: number;
  simulation_id?: number;
  strategies: ComboStrategyEntry[];
  combination_mode: CombinationMode;
  threshold?: number;
  timeframe: string;
  start_date: string;
  end_date: string;
  initial_capital?: number;
}

export type ComboMatrixMetric =
  | 'sharpe_ratio'
  | 'sortino_ratio'
  | 'total_return'
  | 'profit_factor';

export interface ComboMatrixRequest {
  symbol?: string;
  asset_id?: number;
  strategies: string[];
  combination_mode: CombinationMode;
  threshold?: number;
  metric: ComboMatrixMetric;
  timeframe: string;
  start_date: string;
  end_date: string;
  initial_capital?: number;
  strategy_params?: Record<string, Record<string, number>>;
}

export interface ComboMatrixResponse {
  asset_id: number;
  strategies: string[];
  metric: string;
  combination_mode: string;
  values: (number | null)[][];
  duration_ms: number;
}

export interface OptimizationSummary {
  params: Record<string, number>;
  avg_oos_metric: number;
  avg_oos_max_drawdown?: number | null;
}

export interface OptimizationResponse {
  optimization_id?: number;
  asset_id: number;
  strategy_name: string;
  status: string;
  optimize_metric?: string;
  n_splits?: number;
  best_params?: Record<string, number>;
  best_metric?: number;
  best_avg_oos_max_drawdown?: number | null;
  all_results?: OptimizationSummary[];
  full_period_metrics?: BacktestMetrics;
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
  macro_score: number;
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
  stock_connected?: boolean;
  crypto_connected?: boolean;
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

export interface LiveStrategySignalItem {
  strategy: string;
  label: string;
  group: string;
  signal: 'BUY' | 'SELL' | 'NEUTRAL';
  indicator_value: number | null;
  indicator_label: string | null;
  params: Record<string, unknown> | null;
  signal_timeline?: SignalPoint[];
}

export interface StrategySignalsResponse {
  symbol: string;
  timeframe: string;
  bar_count: number;
  strategies: LiveStrategySignalItem[];
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

export interface ChartOverlayRequest {
  symbol?: string;
  asset_id?: number;
  strategy_name: string;
  timeframe: string;
  start_date: string;
  end_date: string;
  strategy_params?: Record<string, unknown>;
}

export interface ChartOverlayTradeEntry {
  entry_time: string;
  exit_time: string | null;
  direction: string;
  entry_price: number;
  exit_price: number | null;
  pnl: number | null;
  return_pct: number | null;
}

export interface ChartOverlayResponse {
  strategy_name: string;
  trade_log: ChartOverlayTradeEntry[];
  indicator_series: Record<string, string | number | null>[];
  duration_ms: number;
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

export interface TradeRecord {
  entry_time: string;
  exit_time: string;
  direction: string;
  entry_price: number;
  exit_price: number;
  pnl: number;
  return_pct: number;
}

export interface StrategyMonthlyState {
  strategy_name: string;
  position: 'Buy' | 'Neutral' | 'Sell';
  indicators: Record<string, number | null>;
}

export interface ComboMonthlyRow {
  month: string;
  combined_position: 'Buy' | 'Sell';
  strategies: StrategyMonthlyState[];
}

export interface SignalPoint {
  time: string;
  signal: 'Buy' | 'Neutral' | 'Sell';
}

export interface ComboStrategySignal {
  strategy_name: string;
  trade_log: TradeRecord[];
  indicator_series: Record<string, string | number | null>[];
  equity_curve: { time: string; value: number }[];
  buy_hold_curve?: { time: string; value: number }[];
  signal_timeline: SignalPoint[];
}

export interface ComboSignalsResponse {
  strategies: ComboStrategySignal[];
}

export interface BacktestResponse {
  backtest_id?: number;
  asset_id: number;
  strategy_name: string;
  strategy_params?: Record<string, unknown>;
  status: string;
  metrics?: BacktestMetrics;
  equity_curve?: { time: string; value: number }[];
  trade_log?: TradeRecord[];
  buy_hold_curve?: { time: string; value: number }[];
  indicator_series?: Record<string, string | number | null>[];
  duration_ms?: number;
  error_message?: string;
  monthly_breakdown?: ComboMonthlyRow[];
}

// ---------------------------------------------------------------------------
// Strategy Builder
// ---------------------------------------------------------------------------

export type AlgoTimeframe = '1m' | '5m' | '15m' | '30m' | '1h' | '3h' | '1d' | '1w';

export interface StrategyRecord {
  id: number;
  asset_id: number;
  symbol: string;
  asset_name: string | null;
  is_active: boolean;
  // Monte Carlo thresholds (BUY / SELL)
  mc_buy_prob_positive: number | null;
  mc_sell_prob_positive: number | null;
  // AI Agent thresholds (BUY / SELL per score)
  ai_buy_conviction: number | null;
  ai_sell_conviction: number | null;
  ai_buy_sentiment: number | null;
  ai_sell_sentiment: number | null;
  ai_buy_macro: number | null;
  ai_sell_macro: number | null;
  // Signal configuration
  combination_mode: 'all' | 'majority' | 'any';
  algo_timeframe: AlgoTimeframe;
  // Auto-trading lifecycle
  auto_trading_enabled: boolean;
  auto_trading_started: boolean;
  // Position sizing
  max_amount_per_position: number | null;
  max_pct_of_capital: number | null;
  created_at: string;
  updated_at: string;
}

export interface UpdateThresholdsRequest {
  mc_buy_prob_positive?: number | null;
  mc_sell_prob_positive?: number | null;
  ai_buy_conviction?: number | null;
  ai_sell_conviction?: number | null;
  ai_buy_sentiment?: number | null;
  ai_sell_sentiment?: number | null;
  ai_buy_macro?: number | null;
  ai_sell_macro?: number | null;
  combination_mode?: 'all' | 'majority' | 'any';
  algo_timeframe?: AlgoTimeframe;
  auto_trading_enabled?: boolean;
}

export interface UpdatePositionSizingRequest {
  max_amount_per_position?: number | null;
  max_pct_of_capital?: number | null;
}

export interface AutoTradingAssetRow {
  strategy_id: number;
  asset_id: number;
  symbol: string;
  asset_name: string | null;
  asset_type: string;
  // Latest MC value
  mc_prob_positive: number | null;
  // MC thresholds
  mc_buy_prob_positive: number | null;
  mc_sell_prob_positive: number | null;
  // Latest AI values
  ai_conviction: number | null;
  ai_sentiment: number | null;
  ai_macro: number | null;
  // AI thresholds
  ai_buy_conviction: number | null;
  ai_sell_conviction: number | null;
  ai_buy_sentiment: number | null;
  ai_sell_sentiment: number | null;
  ai_buy_macro: number | null;
  ai_sell_macro: number | null;
  // Config
  combination_mode: 'all' | 'majority' | 'any';
  algo_timeframe: AlgoTimeframe;
  auto_trading_started: boolean;
  // Position sizing
  max_amount_per_position: number | null;
  max_pct_of_capital: number | null;
}

export interface MonteCarloSummary {
  simulation_id: number;
  prob_positive_return: number;
  mean_max_drawdown: number;
  p5: number;
  p25: number;
  p50: number;
  p75: number;
  p95: number;
  mean_terminal: number;
  std_terminal: number;
  cached: boolean;
}

export interface AIAgentSummary {
  analysis_id: number;
  bias: string | null;
  conviction_score: number | null;
  sentiment_score: number | null;
  macro_score: number | null;
  fundamental_summary: string | null;
  macro_summary: string | null;
  reasoning: string | null;
  key_risk: string | null;
  created_at: string | null;
}

export interface FinancialsSummary {
  revenue_growth: number | null;
  free_cash_flow: number | null;
  current_ratio: number | null;
  pe_ttm: number | null;
  pe_forward: number | null;
  pb_ratio: number | null;
  eps_ttm: number | null;
  eps_forward: number | null;
  market_cap: number | null;
  fetched_at: string | null;
  is_stale: boolean;
}

export interface AlgoStrategySummary {
  algo_attachment_id: number;
  strategy_name: string;
  params: Record<string, unknown> | null;
  added_at: string;
}

export interface StrategyFullResponse {
  strategy_id: number;
  asset_id: number;
  symbol: string;
  asset_name: string | null;
  is_active: boolean;
  created_at: string;
  // MC thresholds (BUY / SELL)
  mc_buy_prob_positive: number | null;
  mc_sell_prob_positive: number | null;
  // AI thresholds (BUY / SELL per score)
  ai_buy_conviction: number | null;
  ai_sell_conviction: number | null;
  ai_buy_sentiment: number | null;
  ai_sell_sentiment: number | null;
  ai_buy_macro: number | null;
  ai_sell_macro: number | null;
  // Configuration
  combination_mode: 'all' | 'majority' | 'any';
  algo_timeframe: AlgoTimeframe;
  auto_trading_enabled: boolean;
  auto_trading_started: boolean;
  max_amount_per_position: number | null;
  max_pct_of_capital: number | null;
  // Data sections
  monte_carlo: MonteCarloSummary | null;
  ai_agents: AIAgentSummary | null;
  financials: FinancialsSummary | null;
  algo_strategies: AlgoStrategySummary[];
  monte_carlo_error: string | null;
  ai_agents_error: string | null;
  financials_error: string | null;
}

export interface CreateStrategyRequest {
  asset_id: number;
}

export interface AttachAlgoRequest {
  asset_id: number;
  strategy_name: string;
  params?: Record<string, unknown> | null;
}

export interface DetachAlgoRequest {
  strategy_id: number;
  algo_attachment_id: number;
}

// ── Execution monitoring (live auto-trading) ──────────────────────────────────

export type CriteriaSignal = 'BUY' | 'SELL' | 'NEUTRAL';

export interface CriterionEvaluation {
  label: string;
  value: number | null;
  buyThreshold: number | null;
  sellThreshold: number | null;
  signal: CriteriaSignal;
}

export interface AttachedAlgoSignal {
  strategy: string;
  label: string;
  signal: 'BUY' | 'SELL' | 'NEUTRAL';
  /** Set when this signal belongs to a combo backtest group */
  comboGroup?: string;
  indicatorValue?: number | null;
  indicatorLabel?: string | null;
  params?: Record<string, unknown> | null;
  signalTimeline?: SignalPoint[];
}

export interface ComboGroupSignal {
  /** e.g. "combo:majority" */
  comboName: string;
  combinationMode: string;
  signal: CriteriaSignal;
}

/** Indicator fields carried on execution monitors for activity logging. */
export type ExecutionIndicatorSnapshot = Pick<
  IndicatorSnapshotResponse,
  | 'close_price'
  | 'rsi'
  | 'macd'
  | 'macd_signal'
  | 'macd_histogram'
  | 'bb_upper'
  | 'bb_middle'
  | 'bb_lower'
  | 'vwap'
  | 'bb_percent'
>;

export interface ExecutionAssetMonitor {
  strategyId: number;
  symbol: string;
  assetName: string | null;
  assetType: string;
  combinationMode: 'all' | 'majority' | 'any';
  algoTimeframe: AlgoTimeframe;
  // Live criteria snapshot (from AutoTradingAssetRow values + thresholds)
  criteria: CriterionEvaluation[];
  // Overall combined signal
  overallSignal: CriteriaSignal;
  // Attached algo strategy signals (expanded: individual strategies within combos are listed)
  algoSignals: AttachedAlgoSignal[];
  // Per-combo combined signal (one entry per attached combo backtest)
  comboSignals: ComboGroupSignal[];
  // Latest price
  latestPrice: number | null;
  priceUpdatedAt: string | null;
  /** ISO timestamp when indicators/strategy signals were last fetched for this asset. */
  lastLivePollAt: string | null;
  indicatorSnapshot: ExecutionIndicatorSnapshot | null;
  // Transactions
  orders: OrderItem[];
  ordersTotal: number;
  ordersPage: number;
  // Loading / error state
  loading: boolean;
  error: string | null;
}
