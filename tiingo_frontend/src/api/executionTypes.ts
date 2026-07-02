export const EXECUTION_TIMEFRAMES = ['5m', '15m', '30m', '1h', '4h', '1d', '1w', '1mo'] as const;

export type ExecutionTimeframe = (typeof EXECUTION_TIMEFRAMES)[number];

export interface ExecutionStatus {
  trading_mode: string;
  alpaca_configured: boolean;
  alpaca_base_url: string;
  kill_switch_enabled: boolean;
  paper_trading_only: boolean;
  trading_mode_paper: boolean;
}

export interface RiskConfig {
  max_position_pct: number;
  max_exposure_pct: number;
  daily_loss_limit_pct: number;
  max_orders_per_minute: number;
  deployment_max_drawdown_pct: number;
  stale_data_max_missed_slots: number;
  stale_data_block_orders: boolean;
}

export interface TradingDeployment {
  id: string;
  model_id: string;
  symbol: string;
  timeframe: string;
  status: string;
  trading_mode: string;
  allocation_pct: number;
  hyperparams_snapshot: Record<string, unknown>;
  model_name?: string | null;
  model_type?: string | null;
  feature_mode?: string | null;
  last_evaluated_bar_time: string | null;
  last_evaluated_at: string | null;
  last_signal: string | null;
  last_error: string | null;
  last_blocked_reason?: string | null;
  last_probability?: number | null;
  last_outcome?: string | null;
  position_qty?: number;
  position_side?: string;
  activated_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TradingDeploymentsResponse {
  deployments: TradingDeployment[];
}

export interface ProbabilityContributor {
  feature: string;
  value: number;
  contribution: number;
}

export interface ProbabilityExplainability {
  method: string;
  base_value?: number | null;
  predicted_value?: number | null;
  top_contributors: ProbabilityContributor[];
  ordered_contributors?: ProbabilityContributor[];
  warnings?: string[];
}

export interface DeploymentOverview {
  id: string;
  model_id: string;
  symbol: string;
  timeframe: string;
  status: string;
  model_name: string | null;
  last_error: string | null;
  last_blocked_reason: string | null;
  last_signal: string | null;
  last_probability: number | null;
  buy_threshold: number | null;
  sell_threshold: number | null;
  last_explainability: ProbabilityExplainability | null;
  last_evaluated_bar_time: string | null;
  last_evaluated_at: string | null;
  current_price: number | null;
  price_updated_at: string | null;
  round_trip_count: number;
  open_position_count: number;
  order_count: number;
  open_order_count: number;
  strategy_profit: number;
  strategy_profit_pct: number | null;
  position_qty: number;
  position_side: string;
  update_status: 'current' | 'stale' | 'unknown';
  expected_latest_bar_time: string | null;
  ohlcv_latest_bar_time: string | null;
  missed_slot_count: number;
}

export interface DeploymentOverviewResponse {
  deployments: DeploymentOverview[];
}

export interface CreateDeploymentRequest {
  model_id: string;
  allocation_pct?: number;
}

export interface ExecutionOrder {
  id: string;
  deployment_id: string;
  alpaca_order_id: string | null;
  symbol: string;
  side: string;
  qty: number;
  order_type: string;
  status: string;
  signal: string;
  bar_time: string;
  filled_avg_price: number | null;
  submitted_at: string;
  filled_at: string | null;
  error_message: string | null;
  model_name?: string | null;
  model_id?: string | null;
}

export interface ExecutionOrdersResponse {
  orders: ExecutionOrder[];
}

export interface ExecutionActivityEvent {
  id: string;
  deployment_id: string;
  symbol: string;
  model_id: string | null;
  model_name: string | null;
  model_type: string | null;
  bar_time: string;
  signal: string;
  probability: number | null;
  buy_threshold: number | null;
  sell_threshold: number | null;
  position_side: string | null;
  order_intent_side: string | null;
  order_qty: number | null;
  outcome: string;
  blocked_reason: string | null;
  order_id: string | null;
  warnings: string[];
  explainability?: ProbabilityExplainability | null;
  created_at: string;
}

export interface ExecutionEvaluationsResponse {
  evaluations: ExecutionActivityEvent[];
}

export interface AccountSnapshot {
  equity: number;
  cash: number;
  buying_power: number;
  portfolio_value: number;
  status: string | null;
  currency: string | null;
}

export interface PositionSnapshot {
  symbol: string | null;
  qty: number;
  side: string | null;
  market_value: number;
  avg_entry_price: number;
  unrealized_pl: number;
  current_price: number;
}

export interface PortfolioPeriodPnl {
  amount: number;
  pct: number | null;
}

export interface PortfolioSummary {
  closed_pnl: PortfolioPeriodPnl;
  open_pnl: PortfolioPeriodPnl;
  qqq_return_pct: number | null;
  voo_return_pct: number | null;
}

export interface PortfolioPeriod {
  start: string;
  end: string;
}

export interface PortfolioPositionRow {
  symbol: string;
  source: string;
  deployment_id: string | null;
  qty: number;
  side: string;
  market_value: number;
  unrealized_pl: number;
  period_pl: number;
  current_price: number;
  avg_entry_price: number;
}

export interface PortfolioResponse {
  account: AccountSnapshot;
  positions: PositionSnapshot[];
  deployment_positions: DeploymentPositionSnapshot[];
  untracked_positions: UntrackedPositionSnapshot[];
  position_rows: PortfolioPositionRow[];
  summary: PortfolioSummary | null;
  period: PortfolioPeriod | null;
}

export interface DeploymentPositionSnapshot {
  deployment_id: string;
  symbol: string;
  model_name: string | null;
  model_id: string | null;
  qty: number;
  side: string;
  market_value: number;
  current_price: number;
  avg_entry_price?: number;
  unrealized_pl?: number;
}

export interface UntrackedPositionSnapshot {
  symbol: string;
  qty: number;
  side: string | null;
  market_value: number;
  avg_entry_price: number;
  unrealized_pl: number;
  current_price: number;
}

export interface DeleteDeploymentRequest {
  close_positions?: boolean;
}

export interface DeleteDeploymentResponse {
  deleted: boolean;
  close_positions: boolean;
  closed_qty: number;
  close_order_id: string | null;
  close_warning?: string | null;
}

export interface EvaluateDeploymentResponse {
  deployment_id: string;
  skipped: boolean;
  signal: string | null;
  bar_time: string | null;
  probability: number | null;
  explainability?: ProbabilityExplainability | null;
  warnings: string[];
  order: Record<string, unknown> | null;
  blocked_reason: string | null;
  outcome: string | null;
  error: string | null;
}

export interface EnqueueJobResponse {
  job_id: string;
  status: string;
}

export interface DeploymentRefreshResponse {
  deployment_id: string;
  results: Array<Record<string, unknown>>;
}

export interface ReconciliationResponse {
  as_of: string;
  catch_up_runs: number;
  results: Array<Record<string, unknown>>;
}

export interface DeploymentCycleEnqueueRequest {
  scheduled_at?: string | null;
}
