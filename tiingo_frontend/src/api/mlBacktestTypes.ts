import type { BacktestEquityPoint, BacktestMetrics, BacktestTrade } from './backtestTypes';

export type FundamentalPeriodType = 'quarterly' | 'annual';
export type MlLabelMode = 'binary' | 'ternary' | 'meta_label';
export type MlLabelMethod = 'endpoint' | 'mean';
export type MlRunMode = 'walk_forward' | 'inference';
export type MlExitPolicy = 'signal_only' | 'label_horizon' | 'atr_bracket' | 'combined';

export interface MlParamConstraint {
  min: number;
  max: number;
}

export interface MlModelCatalogItem {
  id: string;
  label: string;
  description: string;
  params: Record<string, unknown>;
  constraints: Record<string, MlParamConstraint>;
  supports_hyperparameter_search?: boolean;
}

export interface MlModelCatalogResponse {
  models: MlModelCatalogItem[];
}

export interface MlParams {
  feature_mode: string;
  macro_series_ids?: string[];
  macro_publication_lag_days?: Record<string, number>;
  fundamental_metrics?: string[];
  fundamental_period_type?: FundamentalPeriodType;
  context_timeframes?: string[];
  strategy_feature_ids?: string[];
  strategy_feature_params?: Record<string, Record<string, unknown>>;
  label_mode?: MlLabelMode;
  label_threshold?: number;
  label_method?: MlLabelMethod;
  label_horizon: number;
  warmup_bars?: number;
  train_bars: number;
  test_bars: number;
  step_bars: number;
  buy_threshold: number;
  sell_threshold: number;
  min_class_probability?: number;
  random_forest_estimators?: number;
  gradient_boosting_max_iter?: number;
  knn_neighbors?: number;
  xgboost_estimators?: number;
  xgboost_max_depth?: number;
  xgboost_learning_rate?: number;
  model_id?: string;
  inference_eval_scope?: 'holdout' | 'in_sample';
  include_news_sentiment?: boolean;
  slippage_bps?: number;
  base_strategy_id?: string;
  base_strategy_params?: Record<string, unknown>;
  exit_policy?: MlExitPolicy;
  max_hold_bars?: number;
  atr_period?: number;
  profit_atr_mult?: number;
  stop_atr_mult?: number;
  max_horizon_bars?: number;
  meta_gate_threshold?: number;
  denoise_method?: 'none' | 'kalman' | 'wavelet';
  include_cross_sectional_factors?: boolean;
  include_metadata_features?: boolean;
  dynamic_indicator_selection?: boolean;
  indicator_groups?: string[];
  correlation_prune_threshold?: number;
  sizing_method?: 'fixed_fraction' | 'kelly' | 'hrp';
  kelly_fraction?: number;
  hrp_lookback_bars?: number;
  rebalance_frequency?: number;
  hrp_linkage_method?: 'single' | 'ward';
  lstm_seq_length?: number;
  lstm_hidden_size?: number;
  lstm_num_layers?: number;
  lstm_epochs?: number;
  lstm_dropout?: number;
  lstm_learning_rate?: number;
  lstm_batch_size?: number;
  technical_pca_enabled?: boolean;
  technical_pca_variance_threshold?: number;
  macro_features_mode?: 'full' | 'changes_only';
  macro_pca_enabled?: boolean;
  macro_pca_variance_threshold?: number;
  macro_pca_input_mode?: 'changes_only' | 'all_macro';
  fundamental_features_mode?: 'full' | 'growth_only';
  fundamental_pca_enabled?: boolean;
  fundamental_pca_variance_threshold?: number;
  fundamental_pca_input_mode?: 'kpi_only' | 'all_fundamental' | 'growth_only';
}

export interface MlUniverseDefinition {
  id: number;
  name: string;
  source?: string | null;
  description?: string | null;
}

export interface MlRunRequest {
  symbol: string;
  model_type: string;
  params?: Partial<MlParams>;
  symbols?: string[];
  universe_id?: number;
  timeframe?: string;
  start?: string;
  end?: string;
  initial_cash?: number;
  commission_bps?: number;
}

export interface MlFeatureImportanceItem {
  name: string;
  value: number;
}

export interface MlRocCurve {
  class_label: string;
  fpr: number[];
  tpr: number[];
  auc?: number | null;
}

export interface MlShapImportanceItem {
  class_label: string;
  feature: string;
  mean_abs_shap: number;
}

export interface MlShapInteractionItem {
  feature_a: string;
  feature_b: string;
  strength: number;
}

export interface MlPartialDependenceCurve {
  feature: string;
  grid: number[];
  p_up: number[];
}

export interface MlShapSliceFeature {
  feature: string;
  mean_abs_shap: number;
}

export interface MlShapTradeSlices {
  winners_top_decile: MlShapSliceFeature[];
  losers_bottom_decile: MlShapSliceFeature[];
}

export interface MlTreeRules {
  format: string;
  content: string;
  max_depth: number;
}

export interface MlSummary {
  feature_mode: string;
  model_type: string;
  label_mode?: MlLabelMode | string;
  oos_window_count: number;
  mean_oos_accuracy?: number | null;
  signal_counts: Record<string, number>;
  feature_names: string[];
  macro_series_ids?: string[];
  macro_warnings?: string[];
  fundamental_metrics?: string[];
  fundamental_period_type?: FundamentalPeriodType;
  fundamental_warnings?: string[];
  survivorship_warnings?: string[];
  context_timeframes?: string[];
  strategy_feature_ids?: string[];
  run_mode?: MlRunMode | string | null;
  model_id?: string | null;
  precision?: number | null;
  recall?: number | null;
  f1?: number | null;
  f1_macro?: number | null;
  confusion_matrix?: number[][];
  confusion_labels?: number[];
  window_accuracies?: number[];
  feature_importance?: MlFeatureImportanceItem[];
  roc_curves?: MlRocCurve[];
  auc_scores?: Record<string, number | null>;
  shap_importance?: MlShapImportanceItem[];
  coefficient_importance?: MlFeatureImportanceItem[];
  shap_interactions?: MlShapInteractionItem[];
  partial_dependence?: MlPartialDependenceCurve[];
  shap_slices?: MlShapTradeSlices | null;
  tree_rules?: MlTreeRules | null;
  simulation_start_bar_index?: number | null;
  simulation_start_date?: string | null;
  pre_oos_bars_excluded?: number | null;
  evaluation_start_bar_index?: number | null;
  evaluation_start_date?: string | null;
  evaluation_reason?: 'first_trade' | 'simulation_start' | string | null;
  evaluation_scope?: 'holdout' | 'in_sample' | 'walk_forward_oos' | string | null;
  holdout_bars?: number | null;
  holdout_start_date?: string | null;
  holdout_end_date?: string | null;
  train_end_date?: string | null;
}

export interface MlRunResponse {
  id: string;
  run_id?: string;
  symbol: string;
  model_type: string;
  status: string;
  metrics?: BacktestMetrics | null;
}

export interface MlBacktestResultsResponse {
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
  ml_summary?: MlSummary | null;
  error_message?: string | null;
  created_at: string;
  finished_at?: string | null;
}

export interface MlTrainRequest {
  symbol: string;
  model_type: string;
  params?: Partial<MlParams>;
  timeframe?: string;
  start?: string;
  end?: string;
  name?: string;
}

export interface MlTrainResponse {
  id: string;
  name: string;
  model_type: string;
  feature_mode: string;
  train_metrics: Record<string, unknown>;
  feature_schema: Record<string, unknown>;
  created_at: string;
}

export interface MlSavedModel {
  id: string;
  name: string;
  model_type: string;
  feature_mode: string;
  feature_schema: Record<string, unknown>;
  hyperparams: Record<string, unknown>;
  train_metrics?: Record<string, unknown> | null;
  symbol?: string | null;
  timeframe?: string | null;
  created_at: string;
}

export interface MlSavedModelsResponse {
  models: MlSavedModel[];
}

export interface MlCompareResult {
  featureMode: string;
  label: string;
  run?: MlBacktestResultsResponse | null;
  error?: string | null;
}

export interface MlDataPreviewRequest {
  symbol: string;
  params?: Partial<MlParams>;
  timeframe?: string;
  start?: string;
  end?: string;
}

export interface MlMacroCoverage {
  series_id: string;
  total_observations: number;
  with_release_date: number;
  release_date_pct: number;
}

export interface MlLabelPreview {
  label_mode: string;
  label_horizon: number;
  label_threshold?: number | null;
  class_distribution: Record<string, number>;
}

export interface MlWalkForwardReadiness {
  total_bars: number;
  warmup_bars: number;
  valid_feature_rows: number;
  labeled_rows: number;
  trainable_rows: number;
  structural_folds: number;
  viable_folds: number;
  train_bars: number;
  test_bars: number;
  step_bars: number;
  label_horizon: number;
  readiness_issues?: string[];
}

export interface MlDataPreviewResponse {
  decision_timeframe: string;
  bar_counts: Record<string, number>;
  warmup_bars_excluded: number;
  macro_coverage: MlMacroCoverage[];
  fundamental_metrics: string[];
  context_timeframes: string[];
  strategy_feature_ids: string[];
  include_news_sentiment?: boolean;
  feature_names?: string[];
  feature_count?: number;
  feature_groups?: Record<string, string[]>;
  always_included_features?: string[];
  label_preview: MlLabelPreview;
  walk_forward_readiness?: MlWalkForwardReadiness;
  warnings: string[];
}

export interface MlModelLabelSearchConfig {
  model_type: string;
  label_mode: MlLabelMode;
}

export interface MlLabelSearchRequest {
  symbol: string;
  params?: Partial<MlParams>;
  timeframe?: string;
  start?: string;
  end?: string;
  label_mode?: MlLabelMode;
  horizons?: number[];
  thresholds?: number[];
  model_type?: string;
  model_configs?: MlModelLabelSearchConfig[];
}

export interface MlLabelSearchResult {
  label_key: string;
  model_type?: string;
  model_label?: string;
  label_mode: string;
  label_horizon: number;
  label_threshold?: number | null;
  accuracy?: number | null;
  f1_macro?: number | null;
  oos_window_count: number;
  class_distribution: Record<string, number>;
}

export interface MlLabelSearchResponse {
  results: MlLabelSearchResult[];
}

export interface MlThresholdSearchRequest {
  symbol: string;
  model_type: string;
  params?: Partial<MlParams>;
  timeframe?: string;
  start?: string;
  end?: string;
  buy_thresholds?: number[];
  sell_thresholds?: number[];
}

export interface MlThresholdSearchResult {
  buy_threshold?: number | null;
  sell_threshold?: number | null;
  min_class_probability?: number | null;
  signal_counts: Record<string, number>;
  accuracy?: number | null;
  precision?: number | null;
  recall?: number | null;
  f1?: number | null;
  f1_macro?: number | null;
  profit_factor?: number | null;
  total_return_pct?: number | null;
  max_drawdown_pct?: number | null;
  sharpe_ratio?: number | null;
  trade_count?: number | null;
  alpha_pct?: number | null;
}

export interface MlThresholdSearchResponse {
  results: MlThresholdSearchResult[];
}

export interface MlHyperparameterSearchRequest {
  symbol: string;
  model_type: string;
  params?: Partial<MlParams>;
  timeframe?: string;
  start?: string;
  end?: string;
}

export interface MlHyperparameterSearchResponse {
  best_params: Record<string, unknown>;
  best_score?: number | null;
  tuned?: boolean;
}

export type MlTrainingExportScope = 'all_labeled' | 'sample' | 'oos_only';

export interface MlTrainingExportRequest {
  symbol: string;
  model_type: string;
  params?: Partial<MlParams>;
  timeframe?: string;
  start?: string;
  end?: string;
  scope?: MlTrainingExportScope;
  sample_size?: number;
}

export interface MlTrainingExportResponse {
  filename: string;
  row_count: number;
  warnings: string[];
  content_base64: string;
}

export type MlExportFormat = 'training_only' | 'full_workbook';

export interface MlWorkbookExportRequest {
  symbol: string;
  model_type: string;
  params?: Partial<MlParams>;
  timeframe?: string;
  start?: string;
  end?: string;
  training_scope?: MlTrainingExportScope;
  sample_size?: number;
  run_id?: string;
  data_preview?: MlDataPreviewResponse | null;
  label_search_results?: MlLabelSearchResult[];
  threshold_search_results?: MlThresholdSearchResult[];
  compare_results?: MlCompareResult[];
  config_snapshot?: Record<string, unknown>;
}

export interface MlWorkbookSheet {
  name: string;
  row_count: number;
}

export interface MlWorkbookExportResponse {
  filename: string;
  row_count: number;
  warnings: string[];
  content_base64: string;
  sheets: MlWorkbookSheet[];
}

export type MlWizardStep =
  | 'universe'
  | 'data_prep'
  | 'labeling'
  | 'model'
  | 'signals'
  | 'run'
  | 'results';

export const ML_WIZARD_STEPS: { id: MlWizardStep; label: string }[] = [
  { id: 'universe', label: 'Universe' },
  { id: 'data_prep', label: 'Data Prep' },
  { id: 'labeling', label: 'Labeling' },
  { id: 'model', label: 'Model' },
  { id: 'signals', label: 'Signals' },
  { id: 'run', label: 'Run' },
  { id: 'results', label: 'Results' },
];
