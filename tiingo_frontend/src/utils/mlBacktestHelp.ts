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
  | 'commission_bps'
  | 'include_news_sentiment'
  | 'label_mode'
  | 'meta_gate_threshold'
  | 'base_strategy_id'
  | 'slippage_bps'
  | 'correlation_prune_threshold'
  | 'macro_features_mode'
  | 'macro_pca_enabled'
  | 'macro_pca_input_mode'
  | 'macro_pca_variance_threshold'
  | 'exit_policy'
  | 'max_hold_bars'
  | 'profit_atr_mult'
  | 'stop_atr_mult'
  | 'atr_period';

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
  include_news_sentiment: 'News sentiment features',
  label_mode: 'Label mode',
  meta_gate_threshold: 'Meta gate threshold',
  base_strategy_id: 'Meta-label base strategy',
  slippage_bps: 'Slippage (bps)',
  correlation_prune_threshold: 'Correlation prune threshold',
  macro_features_mode: 'Macro features mode',
  macro_pca_enabled: 'Macro PCA',
  macro_pca_input_mode: 'Macro PCA input mode',
  macro_pca_variance_threshold: 'Macro PCA variance threshold',
  exit_policy: 'Trade exit policy',
  max_hold_bars: 'Max hold (bars)',
  profit_atr_mult: 'Profit ATR multiple',
  stop_atr_mult: 'Stop ATR multiple',
  atr_period: 'ATR period',
};

export const ML_FIELD_HELP: Record<MlHelpFieldKey, string> = {
  decision_timeframe:
    'Bar size used to build features, training labels, and execute trades. Walk-forward defaults scale with the selected timeframe.',
  model:
    'Gradient Boosting (recommended default) captures non-linear price patterns with strong walk-forward performance. Logistic regression is a fast linear baseline; random forest is an alternative tree ensemble.',
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
    'Out-of-sample window per walk-forward fold. For saved models, the last test_bars labeled rows are reserved as a holdout set for inference evaluation.',
  step_bars:
    'How many bars the training window advances between folds. Smaller steps produce more overlapping OOS windows; larger steps reduce compute and correlation between folds.',
  buy_threshold:
    'For binary/ternary modes: minimum predicted probability of an upward move required to emit a buy. Must be greater than sell threshold. Meta-label mode uses meta gate threshold instead.',
  sell_threshold:
    'Maximum predicted probability of an upward move allowed before emitting a sell signal. Values between sell and buy thresholds hold the current position.',
  random_forest_estimators:
    'Number of decision trees in the ensemble. More trees can improve stability but increase training time with diminishing returns.',
  gradient_boosting_max_iter:
    'Maximum boosting iterations for HistGradientBoostingClassifier. Higher values can improve fit but increase training time.',
  run_mode:
    'Walk-forward retrains in each fold (default). Use saved model runs holdout inference on the last test_bars rows not seen during training.',
  saved_model:
    'Persisted model trained via Train & save. Feature mode and schema must match the saved artifact.',
  initial_cash:
    'Starting cash balance for the simulated portfolio before any trades are executed.',
  commission_bps:
    'Commission charged per trade in basis points (1 bps = 0.01%). Applied on each buy and sell execution at the next bar open.',
  include_news_sentiment:
    'Adds FinBERT sentiment aggregates in a rolling 24h window ending at each bar (plus 7-day rolling metrics) without look-ahead.',
  label_mode:
    'Binary/ternary: labels from forward returns; the model predicts direction directly. Meta-label: a base rule (crypto trend entry) marks events; labels are ATR profit/stop outcomes; the model gates whether to take each event.',
  meta_gate_threshold:
    'Meta-label only: minimum P(success) required to emit a buy on a base-rule event. Typical crypto preset: 0.65.',
  base_strategy_id:
    'Meta-label only: the algo rule that marks entry event bars. The ML model gates whether to take each event; this is separate from algo strategy features used as model inputs.',
  slippage_bps:
    'Extra execution slippage applied on simulated fills (buy pays more, sell receives less). Crypto preset often uses 5 bps on top of commission.',
  correlation_prune_threshold:
    'Drop one feature from each pair with absolute Pearson correlation above this value before each walk-forward fold. Set to 0 to disable pruning. Default 0.75 reduces redundant indicators but changes which features the model sees.',
  macro_features_mode:
    'Full includes macro levels plus changes; changes only drops non-stationary level columns. Recommended: changes only when using macro PCA.',
  macro_pca_enabled:
    'Compress correlated macro features per FRED category (rates, inflation, labor, etc.) into principal components fitted on each train fold only.',
  macro_pca_input_mode:
    'Changes only feeds stationary change columns into PCA (recommended). All macro includes levels when present in the feature matrix.',
  macro_pca_variance_threshold:
    'Retain enough principal components per macro category to explain this fraction of variance (default 0.85). Optional EWM half-life can weight recent bars more heavily.',
  exit_policy:
    'Controls when open positions close during simulation. Binary defaults to max-hold = label horizon; meta-label defaults to ATR brackets. Signal only matches legacy hold-until-sell behavior.',
  max_hold_bars:
    'Force exit at the bar open after this many sessions in a long position. Aligns trade horizon with label_horizon for binary models.',
  profit_atr_mult:
    'Take-profit distance in ATR units from entry (intrabar high). Used for meta-label training and atr_bracket/combined exit policies.',
  stop_atr_mult:
    'Stop-loss distance in ATR units from entry (intrabar low). Checked before profit on each bar.',
  atr_period:
    'ATR lookback used to size stop and target levels for bracket exits.',
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
