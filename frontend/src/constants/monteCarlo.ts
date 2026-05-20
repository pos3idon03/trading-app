import type { CombinationMode } from '../api/types';

export const DEFAULT_MC_SIM_GRID: Record<string, number[]> = {
  num_paths: [500, 1000, 5000],
  calibration_years: [5, 10, 15],
};

export const MC_SIM_OPTIMIZE_METRICS = [
  { value: 'prob_positive_return', label: 'Prob. Positive Return' },
  { value: 'p50', label: 'Median Terminal (P50)' },
  { value: 'mean_terminal', label: 'Mean Terminal' },
  { value: 'p5', label: '5th Percentile Terminal' },
  { value: 'mean_max_drawdown', label: 'Mean Max Drawdown' },
  { value: 'std_terminal', label: 'Std Dev (Terminal)' },
];

export const MC_HORIZON_OPTIONS = [21, 63, 126, 252, 504];

/** Default grid for MC backtest walk-forward optimization (thresholds as %). */
export const DEFAULT_MC_BACKTEST_GRID: Record<string, number[]> = {
  buy_threshold: [52, 55, 58],
  sell_threshold: [45, 48, 50],
  num_paths: [500, 1000],
  calibration_years: [5, 10],
};

/** Must match backend mc_backtest_optimizer.MAX_COMBOS */
export const MC_MAX_PARAM_COMBOS = 150;

export const MC_BACKTEST_OPTIMIZE_METRICS = [
  { value: 'sortino_ratio', label: 'Sortino Ratio' },
  { value: 'sharpe_ratio', label: 'Sharpe Ratio' },
  { value: 'excess_return', label: 'Excess Return vs Buy & Hold' },
  { value: 'total_return', label: 'Total Return' },
  { value: 'profit_factor', label: 'Profit Factor' },
  { value: 'win_rate', label: 'Win Rate' },
];

export type McModelType = 'vasicek' | 'merton' | 'ou_deviation' | 'blended';

export const MC_MODEL_OPTIONS: { value: McModelType; label: string; description?: string }[] = [
  { value: 'merton', label: 'Merton Jump-Diffusion', description: 'Trend / drift from recent returns' },
  { value: 'vasicek', label: 'Vasicek + Jump', description: 'Mean-reverting with dynamic theta' },
  { value: 'ou_deviation', label: 'OU Deviation', description: 'Mean reversion to rolling MA (log deviation)' },
  {
    value: 'blended',
    label: 'Blended (ADX)',
    description: 'ADX-weighted Merton + OU reversion; high ADX favors trend',
  },
];

export const MC_COMBINATION_MODES: {
  value: CombinationMode;
  label: string;
  description: string;
}[] = [
  {
    value: 'and',
    label: 'AND (Unanimous)',
    description:
      'Enter when every leg is Buy; exit when every leg is Sell. Mixed or Neutral legs hold the current position.',
  },
  {
    value: 'or',
    label: 'OR (Any)',
    description:
      'Enter when any leg is Buy; exit when any leg is Sell. If one leg is Sell and another Buy on the same bar, exit (Sell wins).',
  },
  {
    value: 'majority',
    label: 'Majority Vote',
    description:
      'More Buy than Sell votes wins (Neutral abstains). Ties keep the current combined position.',
  },
  {
    value: 'weighted',
    label: 'Weighted',
    description:
      'Weighted Buy vs Sell votes (Neutral abstains). In the hold band between thresholds, position is unchanged.',
  },
];
