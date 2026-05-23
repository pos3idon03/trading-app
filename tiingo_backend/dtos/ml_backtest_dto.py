from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from dtos.backtest_dto import (
    BacktestEquityPointDTO,
    BacktestMetricsDTO,
    BacktestTradeDTO,
)


class MlParamConstraintDTO(BaseModel):
    min: float
    max: float


class MlModelCatalogItemDTO(BaseModel):
    id: str
    label: str
    description: str
    params: dict[str, Any]
    constraints: dict[str, MlParamConstraintDTO] = Field(default_factory=dict)
    supports_hyperparameter_search: bool = False


class MlModelCatalogResponse(BaseModel):
    models: list[MlModelCatalogItemDTO]


class MlFeatureImportanceItemDTO(BaseModel):
    name: str
    value: float


class MlRocCurveDTO(BaseModel):
    class_label: str
    fpr: list[float] = Field(default_factory=list)
    tpr: list[float] = Field(default_factory=list)
    auc: Optional[float] = None


class MlShapImportanceItemDTO(BaseModel):
    class_label: str
    feature: str
    mean_abs_shap: float


class MlRunRequest(BaseModel):
    symbol: str
    model_type: str
    params: dict[str, Any] = Field(default_factory=dict)
    timeframe: str = "1d"
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    initial_cash: float = Field(default=10_000.0, gt=0)
    commission_bps: float = Field(default=0.0, ge=0, le=1000)


class MlSummaryDTO(BaseModel):
    feature_mode: str
    model_type: str
    label_mode: str = "binary"
    oos_window_count: int
    mean_oos_accuracy: Optional[float] = None
    signal_counts: dict[str, int] = Field(default_factory=dict)
    feature_names: list[str] = Field(default_factory=list)
    macro_series_ids: list[str] = Field(default_factory=list)
    macro_warnings: list[str] = Field(default_factory=list)
    fundamental_metrics: list[str] = Field(default_factory=list)
    fundamental_period_type: str = "quarterly"
    fundamental_warnings: list[str] = Field(default_factory=list)
    context_timeframes: list[str] = Field(default_factory=list)
    strategy_feature_ids: list[str] = Field(default_factory=list)
    run_mode: Optional[str] = None
    model_id: Optional[str] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1: Optional[float] = None
    f1_macro: Optional[float] = None
    confusion_matrix: list[list[int]] = Field(default_factory=list)
    confusion_labels: list[int] = Field(default_factory=list)
    window_accuracies: list[float] = Field(default_factory=list)
    feature_importance: list[MlFeatureImportanceItemDTO] = Field(default_factory=list)
    roc_curves: list[MlRocCurveDTO] = Field(default_factory=list)
    auc_scores: dict[str, float | None] = Field(default_factory=dict)
    shap_importance: list[MlShapImportanceItemDTO] = Field(default_factory=list)
    simulation_start_bar_index: Optional[int] = None
    simulation_start_date: Optional[str] = None
    pre_oos_bars_excluded: Optional[int] = None


class MlRunResponse(BaseModel):
    id: UUID
    symbol: str
    model_type: str
    status: str
    metrics: Optional[BacktestMetricsDTO] = None


class MlBacktestResultsResponse(BaseModel):
    id: UUID
    symbol: str
    model_type: str
    params: dict[str, Any]
    timeframe: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    initial_cash: float
    commission_bps: float
    status: str
    metrics: Optional[BacktestMetricsDTO] = None
    equity_curve: list[BacktestEquityPointDTO] = Field(default_factory=list)
    benchmark_equity_curve: list[BacktestEquityPointDTO] = Field(default_factory=list)
    trades: list[BacktestTradeDTO] = Field(default_factory=list)
    ml_summary: Optional[MlSummaryDTO] = None
    error_message: Optional[str] = None
    created_at: datetime
    finished_at: Optional[datetime] = None


class MlTrainRequest(BaseModel):
    symbol: str
    model_type: str
    params: dict[str, Any] = Field(default_factory=dict)
    timeframe: str = "1d"
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    name: Optional[str] = None


class MlTrainResponse(BaseModel):
    id: UUID
    name: str
    model_type: str
    feature_mode: str
    train_metrics: dict[str, Any] = Field(default_factory=dict)
    feature_schema: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class MlSavedModelDTO(BaseModel):
    id: UUID
    name: str
    model_type: str
    feature_mode: str
    feature_schema: dict[str, Any] = Field(default_factory=dict)
    hyperparams: dict[str, Any] = Field(default_factory=dict)
    train_metrics: Optional[dict[str, Any]] = None
    created_at: datetime


class MlSavedModelsResponse(BaseModel):
    models: list[MlSavedModelDTO]


class MlDataPreviewRequest(BaseModel):
    symbol: str
    params: dict[str, Any] = Field(default_factory=dict)
    timeframe: str = "1d"
    start: Optional[datetime] = None
    end: Optional[datetime] = None


class MlMacroCoverageDTO(BaseModel):
    series_id: str
    total_observations: int
    with_release_date: int
    release_date_pct: float


class MlLabelPreviewDTO(BaseModel):
    label_mode: str
    label_horizon: int
    label_threshold: Optional[float] = None
    class_distribution: dict[str, int] = Field(default_factory=dict)


class MlDataPreviewResponse(BaseModel):
    decision_timeframe: str
    bar_counts: dict[str, int] = Field(default_factory=dict)
    warmup_bars_excluded: int
    macro_coverage: list[MlMacroCoverageDTO] = Field(default_factory=list)
    fundamental_metrics: list[str] = Field(default_factory=list)
    context_timeframes: list[str] = Field(default_factory=list)
    strategy_feature_ids: list[str] = Field(default_factory=list)
    label_preview: MlLabelPreviewDTO
    warnings: list[str] = Field(default_factory=list)


class MlLabelSearchRequest(BaseModel):
    symbol: str
    params: dict[str, Any] = Field(default_factory=dict)
    timeframe: str = "1d"
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    label_mode: str = "binary"
    horizons: list[int] = Field(default_factory=lambda: [2, 4, 6, 8, 10])
    thresholds: list[float] = Field(default_factory=lambda: [0.01, 0.02])
    model_type: Optional[str] = None
    model_types: Optional[list[str]] = None


class MlLabelSearchResultDTO(BaseModel):
    label_key: str
    model_type: str = "ml_logistic"
    model_label: str = "Logistic Regression"
    label_mode: str
    label_horizon: int
    label_threshold: Optional[float] = None
    accuracy: Optional[float] = None
    f1_macro: Optional[float] = None
    oos_window_count: int = 0
    class_distribution: dict[str, int] = Field(default_factory=dict)


class MlLabelSearchResponse(BaseModel):
    results: list[MlLabelSearchResultDTO] = Field(default_factory=list)


class MlThresholdSearchRequest(BaseModel):
    symbol: str
    model_type: str
    params: dict[str, Any] = Field(default_factory=dict)
    timeframe: str = "1d"
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    buy_thresholds: list[float] = Field(default_factory=lambda: [0.52, 0.55, 0.58, 0.6])
    sell_thresholds: list[float] = Field(default_factory=lambda: [0.4, 0.42, 0.45, 0.48])


class MlThresholdSearchResultDTO(BaseModel):
    buy_threshold: Optional[float] = None
    sell_threshold: Optional[float] = None
    min_class_probability: Optional[float] = None
    signal_counts: dict[str, int] = Field(default_factory=dict)
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1: Optional[float] = None
    f1_macro: Optional[float] = None


class MlThresholdSearchResponse(BaseModel):
    results: list[MlThresholdSearchResultDTO] = Field(default_factory=list)


class MlHyperparameterSearchRequest(BaseModel):
    symbol: str
    model_type: str
    params: dict[str, Any] = Field(default_factory=dict)
    timeframe: str = "1d"
    start: Optional[datetime] = None
    end: Optional[datetime] = None


class MlHyperparameterSearchResponse(BaseModel):
    best_params: dict[str, Any] = Field(default_factory=dict)
    best_score: Optional[float] = None
    tuned: bool = False


class MlTrainingExportRequest(BaseModel):
    symbol: str
    model_type: str = "ml_logistic"
    params: dict[str, Any] = Field(default_factory=dict)
    timeframe: str = "1d"
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    scope: str = "all_labeled"
    sample_size: int = Field(default=500, ge=1, le=10_000)


class MlTrainingExportResponse(BaseModel):
    filename: str
    row_count: int
    warnings: list[str] = Field(default_factory=list)
    content_base64: str


class MlJobAcceptedResponse(BaseModel):
    job_id: UUID
    status: str = "accepted"
    run_id: Optional[UUID] = None
