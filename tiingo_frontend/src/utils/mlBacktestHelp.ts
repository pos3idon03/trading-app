import { OHLCV_TIMEFRAMES } from '../constants/timeframes';

export const ML_SUPPORTED_TIMEFRAMES = new Set(
  OHLCV_TIMEFRAMES.map((item) => item.value),
);

export type MlHelpFieldKey =
  | 'decision_timeframe'
  | 'model'
  | 'feature_mode'
  | 'macro_series_ids'
  | 'fundamental_metrics'
  | 'fundamental_period_type'
  | 'label_horizon'
  | 'train_bars'
  | 'test_bars'
  | 'step_bars'
  | 'buy_threshold'
  | 'sell_threshold'
  | 'random_forest_estimators'
  | 'gradient_boosting_max_iter'
  | 'run_mode'
  | 'saved_model'
  | 'initial_cash'
  | 'commission_bps';

export const ML_FIELD_LABELS: Record<MlHelpFieldKey, string> = {
  decision_timeframe: 'Decision timeframe',
  model: 'Model',
  feature_mode: 'Feature mode',
  macro_series_ids: 'Macro series',
  fundamental_metrics: 'Fundamental metrics',
  fundamental_period_type: 'Fundamental period',
  label_horizon: 'Label horizon (bars)',
  train_bars: 'Train bars',
  test_bars: 'Test bars',
  step_bars: 'Step bars',
  buy_threshold: 'Buy threshold',
  sell_threshold: 'Sell threshold',
  random_forest_estimators: 'Random forest estimators',
  gradient_boosting_max_iter: 'Gradient boosting iterations',
  run_mode: 'Run mode',
  saved_model: 'Saved model',
  initial_cash: 'Initial cash',
  commission_bps: 'Commission (bps)',
};

export const ML_FIELD_HELP: Record<MlHelpFieldKey, string> = {
  decision_timeframe:
    'Bar size used to build features, training labels, and execute trades. Walk-forward defaults scale with the selected timeframe.',
  model:
    'Classifier trained in each walk-forward window. Logistic regression is a linear baseline; random forest captures non-linear patterns but may overfit on small samples.',
  feature_mode:
    'Prices only uses OHLCV-derived features. Prices + macro adds FRED series. Full mode also adds quarterly/annual fundamentals aligned as-of each bar using report publication dates (no look-ahead). Sparse fundamentals coverage may introduce survivorship bias.',
  macro_series_ids:
    'Ingested macroeconomic series joined to each bar. Monthly and weekly releases are forward-filled from the last observation on or before the bar date.',
  fundamental_metrics:
    'Tiingo statement metrics joined as-of report publication time. Raw levels plus YoY/QoQ changes and quarters since last report are included when history allows.',
  fundamental_period_type:
    'Quarterly uses fiscal quarter rows; annual uses FY statements or aggregated quarterly totals when native annual rows are unavailable.',
  label_horizon:
    'Number of bars ahead used to define the training target. Label is 1 when forward return over this horizon is positive, else 0. Larger values predict longer-horizon moves.',
  train_bars:
    'In-sample window size for each walk-forward fold. The model learns only on these bars before predicting the next test window.',
  test_bars:
    'Out-of-sample window where the model generates predictions that can become buy/sell signals. Backtest trades occur only on these bars.',
  step_bars:
    'How many bars the training window advances between folds. Smaller steps produce more overlapping OOS windows; larger steps reduce compute and correlation between folds.',
  buy_threshold:
    'Minimum predicted probability of an upward move required to emit a buy signal. Must be greater than the sell threshold.',
  sell_threshold:
    'Maximum predicted probability of an upward move allowed before emitting a sell signal. Values between sell and buy thresholds hold the current position.',
  random_forest_estimators:
    'Number of decision trees in the ensemble. More trees can improve stability but increase training time with diminishing returns.',
  gradient_boosting_max_iter:
    'Maximum boosting iterations for HistGradientBoostingClassifier. Higher values can improve fit but increase training time.',
  run_mode:
    'Walk-forward retrains in each fold (default). Use saved model applies a frozen trained artifact without retraining.',
  saved_model:
    'Persisted model trained via Train & save. Feature mode and schema must match the saved artifact.',
  initial_cash:
    'Starting cash balance for the simulated portfolio before any trades are executed.',
  commission_bps:
    'Commission charged per trade in basis points (1 bps = 0.01%). Applied on each buy and sell execution at the next bar open.',
};

export function mlFieldLabel(key: MlHelpFieldKey): string {
  return ML_FIELD_LABELS[key];
}

export function mlFieldHelp(key: MlHelpFieldKey): string {
  return ML_FIELD_HELP[key];
}

export function isMlTimeframeSupported(timeframe: string): boolean {
  return ML_SUPPORTED_TIMEFRAMES.has(timeframe);
}
