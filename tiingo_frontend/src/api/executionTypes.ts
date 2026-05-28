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
  last_signal: string | null;
  last_error: string | null;
  last_blocked_reason?: string | null;
  last_probability?: number | null;
  last_outcome?: string | null;
  activated_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TradingDeploymentsResponse {
  deployments: TradingDeployment[];
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

export interface PortfolioResponse {
  account: AccountSnapshot;
  positions: PositionSnapshot[];
}

export interface EvaluateDeploymentResponse {
  deployment_id: string;
  skipped: boolean;
  signal: string | null;
  bar_time: string | null;
  probability: number | null;
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
