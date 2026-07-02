export type CombineMode = 'unanimous' | 'majority' | 'weighted';

export interface EnsembleLeg {
  strategy_id: string;
  signal_timeframe?: string;
  params: Record<string, number>;
  weight: number;
}

export interface EnsembleParams {
  combine_mode: CombineMode;
  threshold: number;
  legs: EnsembleLeg[];
}

export interface StrategyParamConstraint {
  min: number;
  max: number;
}

export interface StrategyCatalogItem {
  id: string;
  label: string;
  description: string;
  params: Record<string, unknown>;
  constraints: Record<string, StrategyParamConstraint>;
  ensemble_eligible?: boolean;
}

export interface StrategyCatalogResponse {
  strategies: StrategyCatalogItem[];
}

export interface BacktestMetrics {
  total_return_pct?: number | null;
  benchmark_return_pct?: number | null;
  alpha_pct?: number | null;
  cagr_pct?: number | null;
  max_drawdown_pct?: number | null;
  sharpe_ratio?: number | null;
  sortino_ratio?: number | null;
  profit_factor?: number | null;
  calmar_ratio?: number | null;
  win_rate_pct?: number | null;
  trade_count: number;
  final_equity?: number | null;
  initial_cash?: number | null;
}

export interface BacktestEquityPoint {
  date: string;
  equity: number;
  cash: number;
  shares: number;
  drawdown_pct: number;
}

export interface BacktestTrade {
  entry_date: string;
  exit_date: string;
  entry_price: number;
  exit_price: number;
  shares: number;
  pnl: number;
  pnl_pct: number;
  exit_reason?: string;
}

export interface BacktestRunRequest {
  symbol: string;
  strategy: string;
  params?: Record<string, unknown>;
  timeframe?: string;
  signal_timeframe?: string;
  start?: string;
  end?: string;
  initial_cash?: number;
  commission_bps?: number;
}

export interface BacktestRunResponse {
  id: string;
  symbol: string;
  strategy: string;
  status: string;
  metrics?: BacktestMetrics | null;
}

export interface BacktestResultsResponse {
  id: string;
  symbol: string;
  strategy: string;
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
  error_message?: string | null;
  created_at: string;
  finished_at?: string | null;
}
