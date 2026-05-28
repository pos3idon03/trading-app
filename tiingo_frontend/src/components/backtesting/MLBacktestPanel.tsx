import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ingestionApi, marketDataApi, mlBacktestApi } from '../../api/endpoints';
import type { BacktestResultsResponse } from '../../api/backtestTypes';
import type {
  MlBacktestResultsResponse,
  MlCompareResult,
  MlDataPreviewResponse,
  MlLabelSearchResult,
  MlModelCatalogItem,
  MlParams,
  MlRunMode,
  MlSavedModel,
  MlThresholdSearchResult,
  MlTrainResponse,
  MlWizardStep,
} from '../../api/mlBacktestTypes';
import type { MacroSeries, OHLCVBar } from '../../api/types';
import type { DateRangeValue } from '../../constants/timeframes';
import { buildOhlcvQuery } from '../../constants/timeframes';
import ErrorAlert from '../ErrorAlert';
import FieldLabel from '../FieldLabel';
import Spinner from '../Spinner';
import BacktestMetricsCards from '../BacktestMetricsCards';
import BacktestPerformanceLabels from './BacktestPerformanceLabels';
import BacktestEquityChart from '../charts/BacktestEquityChart';
import MlConfusionMatrix from '../charts/MlConfusionMatrix';
import MlFeatureImportanceChart from '../charts/MlFeatureImportanceChart';
import MlLabelGridResults from '../charts/MlLabelGridResults';
import MlOosAccuracyChart from '../charts/MlOosAccuracyChart';
import MlRocChart from '../charts/MlRocChart';
import MlShapImportanceChart from '../charts/MlShapImportanceChart';
import OhlcvTimelineChart from '../charts/OhlcvTimelineChart';
import MlComparePanel from './MlComparePanel';
import MlTrainingExportDialog from './MlTrainingExportDialog';
import MlUniversePeriodSection from './MlUniversePeriodSection';
import MlWizardSummaryCard from './MlWizardSummaryCard';
import MlWalkForwardReadinessCard from './MlWalkForwardReadinessCard';
import MlBarCountChart from '../charts/MlBarCountChart';
import MlClassDistributionChart from '../charts/MlClassDistributionChart';
import MlMacroCoverageChart from '../charts/MlMacroCoverageChart';
import MlLabelGridHeatmap from '../charts/MlLabelGridHeatmap';
import MlLabelModelCompareChart from '../charts/MlLabelModelCompareChart';
import MlThresholdSweepChart from '../charts/MlThresholdSweepChart';
import { useMlWizard } from '../../hooks/useMlWizard';
import { useMlUniverseBarCount } from '../../hooks/useMlUniverseBarCount';
import {
  canNavigateToWizardStep,
  type MlLockedConfig,
} from '../../utils/mlWizardState';
import { buildMlWorkbookConfigSnapshot } from '../../utils/mlWorkbookExport';
import { formatBacktestPct, sortTradesByExit } from '../../utils/backtestData';
import { apiRangeFromOhlcvQuery, chartDateRange } from '../../utils/multitimeframeBacktest';
import {
  DEFAULT_FUNDAMENTAL_METRICS,
  DEFAULT_MACRO_SERIES_IDS,
  DEFAULT_ML_PARAMS,
  ML_FEATURE_MODES,
  ML_COMPARE_FEATURE_MODES,
  formatMetricPercent,
  formatHyperparameterSearchMessage,
  formatOosAccuracy,
  featureModeUsesMacro,
  fundamentalCoverageWarning,
  fundamentalEntitlementWarning,
  fundamentalMetricCoverageWarning,
  isFundamentalsEntitled,
  isGradientBoostingModel,
  isRandomForestModel,
  macroCoverageWarning,
  minimumBarsRequired,
  parseMlParams,
  pickWalkForwardParams,
  resolveWalkForwardParams,
  validateMlParams,
  validateWalkForwardParams,
  type WalkForwardParamKey,
} from '../../utils/mlBacktestConfig';
import {
  FUNDAMENTAL_GROUPS,
  metricsByGroup,
} from '../../constants/fundamentalsMetrics';
import {
  buildCoverageWarnings,
  parseEffectiveCoverage,
  type OhlcvCoverageResponse,
} from '../../utils/backtestCoverage';
import { mlFieldHelp, mlFieldLabel, type MlHelpFieldKey } from '../../utils/mlBacktestHelp';
import {
  filterRecordsFromSimulationStart,
  formatSimulationPeriodLabel,
  resolveEvaluationStartDate,
} from '../../utils/mlBacktestEvaluation';
import MlEvaluationScopeBanner from './MlEvaluationScopeBanner';
import {
  isReadinessReady,
  previewConfigFingerprint,
} from '../../utils/mlWalkForwardDiagnostics';
import { computeWalkForwardBudget } from '../../utils/mlUniverseBudget';

interface MLBacktestPanelProps {
  symbol: string;
  dateRange: DateRangeValue;
  onDateRangeChange: (value: DateRangeValue) => void;
  decisionTimeframe: string;
  wizardStep?: MlWizardStep;
  onWizardBridge?: (bridge: MlWizardBridge | null) => void;
  initialEditModelId?: string;
}

export interface MlWizardBridge {
  wizardStep: MlWizardStep;
  gateError: string | null;
  goNext: () => string | null;
  goBack: () => void;
  goToStep: (step: MlWizardStep) => boolean;
  isUniverseLocked: boolean;
  lockedConfig: MlLockedConfig;
  canNavigateToStep: (step: MlWizardStep) => boolean;
  walkForwardParams: Pick<MlParams, 'train_bars' | 'test_bars' | 'step_bars' | 'label_horizon'>;
  setWalkForwardParam: (key: WalkForwardParamKey, value: number) => void;
  resetWalkForwardDefaults: () => void;
  walkForwardValidationError: string | null;
  minimumBarsRequired: number;
  availableBarCount: number | null;
  previewViableFolds: number | null;
}

type MlNumericParamKey = Exclude<
  MlHelpFieldKey,
  | 'decision_timeframe'
  | 'model'
  | 'feature_mode'
  | 'macro_series_ids'
  | 'fundamental_metrics'
  | 'fundamental_period_type'
  | 'run_mode'
  | 'saved_model'
  | 'initial_cash'
  | 'commission_bps'
  | 'label_horizon'
  | 'train_bars'
  | 'test_bars'
  | 'step_bars'
>;

function extractErrorMessage(err: unknown, fallback = 'ML backtest failed.'): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const resp = (err as { response?: { data?: { detail?: unknown } } }).response;
    const detail = resp?.data?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail
        .map((item) =>
          typeof item === 'object' && item && 'msg' in item ? String(item.msg) : String(item),
        )
        .join('; ');
    }
  }
  if (err instanceof Error && err.message) {
    return err.message;
  }
  return fallback;
}

const STRATEGY_FEATURE_OPTIONS = [
  { id: 'rsi_reversion', label: 'RSI Mean Reversion' },
  { id: 'sma_crossover', label: 'SMA Crossover' },
  { id: 'ema_crossover', label: 'EMA Crossover' },
  { id: 'ts_momentum', label: 'Time-Series Momentum' },
];

const CONTEXT_TIMEFRAME_OPTIONS = ['1w', '1mo'];

function stepVisible(wizardStep: MlWizardStep | undefined, allowed: MlWizardStep[]): boolean {
  if (!wizardStep) return true;
  return allowed.includes(wizardStep);
}

export default function MLBacktestPanel({
  symbol,
  dateRange,
  onDateRangeChange,
  decisionTimeframe,
  wizardStep,
  onWizardBridge,
  initialEditModelId,
}: MLBacktestPanelProps) {
  const [models, setModels] = useState<MlModelCatalogItem[]>([]);
  const [modelType, setModelType] = useState('ml_logistic');
  const [mlParams, setMlParams] = useState<MlParams>(DEFAULT_ML_PARAMS);
  const [initialCash, setInitialCash] = useState(10_000);
  const [commissionBps, setCommissionBps] = useState(5);
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chartError, setChartError] = useState<string | null>(null);
  const [results, setResults] = useState<MlBacktestResultsResponse | null>(null);
  const [chartRecords, setChartRecords] = useState<OHLCVBar[]>([]);
  const [macroSeries, setMacroSeries] = useState<MacroSeries[]>([]);
  const [ingestedMacroIds, setIngestedMacroIds] = useState<Set<string>>(new Set());
  const [fundamentalsEntitlement, setFundamentalsEntitlement] = useState<Record<string, unknown> | null>(null);
  const [symbolHasFundamentals, setSymbolHasFundamentals] = useState(false);
  const [ingestedFundamentalMetrics, setIngestedFundamentalMetrics] = useState<Set<string>>(new Set());
  const [decisionCoverage, setDecisionCoverage] = useState<OhlcvCoverageResponse | null>(null);
  const [runMode, setRunMode] = useState<MlRunMode>('walk_forward');
  const [savedModels, setSavedModels] = useState<MlSavedModel[]>([]);
  const [selectedSavedModelId, setSelectedSavedModelId] = useState('');
  const [training, setTraining] = useState(false);
  const [trainResult, setTrainResult] = useState<MlTrainResponse | null>(null);
  const [comparing, setComparing] = useState(false);
  const [compareResults, setCompareResults] = useState<MlCompareResult[]>([]);
  const [dataPreview, setDataPreview] = useState<MlDataPreviewResponse | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [jobProgress, setJobProgress] = useState<number | null>(null);
  const appliedEditModelIdRef = useRef<string | null>(null);
  const [labelSearchResults, setLabelSearchResults] = useState<MlLabelSearchResult[]>([]);
  const [labelSearchLoading, setLabelSearchLoading] = useState(false);
  const [thresholdResults, setThresholdResults] = useState<MlThresholdSearchResult[]>([]);
  const [thresholdLoading, setThresholdLoading] = useState(false);
  const [hyperparamMessage, setHyperparamMessage] = useState<string | null>(null);
  const [appliedModelLabel, setAppliedModelLabel] = useState<string | null>(null);
  const walkForwardCustomizedRef = useRef(false);
  const prevModelTypeRef = useRef(modelType);
  const previewFingerprintRef = useRef<string | null>(null);
  const prevDateRangeRef = useRef(JSON.stringify(dateRange));

  const {
    barCount: availableBarCount,
    rangeStart: universeRangeStart,
    rangeEnd: universeRangeEnd,
    loading: universeBarCountLoading,
    error: universeBarCountError,
  } = useMlUniverseBarCount(symbol, decisionTimeframe, dateRange);

  const usesMacroFeatures = featureModeUsesMacro(mlParams.feature_mode);
  const usesFundamentalFeatures = mlParams.feature_mode === 'prices_macro_fundamentals';

  const selectedModel = useMemo(
    () => models.find((item) => item.id === modelType),
    [models, modelType],
  );

  const wizard = useMlWizard({
    symbol,
    decisionTimeframe,
    dateRange,
    mlParams,
    modelType,
    modelLabel: appliedModelLabel ?? selectedModel?.label,
    selectedModel,
    initialCash,
    commissionBps,
    runMode,
    availableBarCount,
  });

  const activeWizardStep = wizardStep ?? wizard.wizardStep;

  const walkForwardParams = useMemo(() => pickWalkForwardParams(mlParams), [mlParams]);

  const walkForwardBudget = useMemo(
    () =>
      availableBarCount != null && availableBarCount > 0
        ? computeWalkForwardBudget(availableBarCount, walkForwardParams)
        : null,
    [availableBarCount, walkForwardParams],
  );

  const walkForwardValidationError = useMemo(
    () => validateWalkForwardParams(walkForwardParams, availableBarCount),
    [walkForwardParams, availableBarCount],
  );

  const exportRange = useMemo(
    () => apiRangeFromOhlcvQuery(buildOhlcvQuery(decisionTimeframe, dateRange)),
    [decisionTimeframe, dateRange],
  );

  const workbookConfigSnapshot = useMemo(
    () =>
      buildMlWorkbookConfigSnapshot({
        initialCash,
        commissionBps,
        runMode,
        modelLabel: selectedModel?.label,
        appliedModelLabel,
        dateRangeStart: exportRange.start,
        dateRangeEnd: exportRange.end,
      }),
    [
      initialCash,
      commissionBps,
      runMode,
      selectedModel?.label,
      appliedModelLabel,
      exportRange.start,
      exportRange.end,
    ],
  );

  const applyResolvedWalkForwardParams = useCallback(
    (barCount?: number | null) => {
      const resolved = resolveWalkForwardParams(decisionTimeframe, barCount);
      setMlParams((prev) => ({ ...prev, ...resolved }));
    },
    [decisionTimeframe],
  );

  const setWalkForwardParam = useCallback(
    (key: WalkForwardParamKey, value: number) => {
      walkForwardCustomizedRef.current = true;
      setMlParams((prev) => ({ ...prev, [key]: value }));
      if (wizard.wizardStep === 'universe') {
        wizard.invalidateFromStep('universe');
      }
    },
    [wizard],
  );

  const resetWalkForwardDefaults = useCallback(() => {
    walkForwardCustomizedRef.current = false;
    applyResolvedWalkForwardParams(availableBarCount);
    if (wizard.wizardStep === 'universe') {
      wizard.invalidateFromStep('universe');
    }
  }, [applyResolvedWalkForwardParams, availableBarCount, wizard]);

  useEffect(() => {
    const serialized = JSON.stringify(dateRange);
    if (prevDateRangeRef.current === serialized) {
      return;
    }
    prevDateRangeRef.current = serialized;
    wizard.invalidateFromStep('universe');
  }, [dateRange, wizard]);

  const validationError = useMemo(
    () => validateMlParams(mlParams, selectedModel),
    [mlParams, selectedModel],
  );

  const minBars = useMemo(() => minimumBarsRequired(mlParams), [mlParams]);

  const barCoverageWarnings = useMemo(
    () =>
      buildCoverageWarnings(
        { [decisionTimeframe]: decisionCoverage },
        dateRange,
        { [decisionTimeframe]: minBars },
      ),
    [decisionCoverage, decisionTimeframe, dateRange, minBars],
  );

  const previewStale = useMemo(() => {
    if (!dataPreview || !previewFingerprintRef.current) {
      return false;
    }
    return previewConfigFingerprint(mlParams, dateRange) !== previewFingerprintRef.current;
  }, [dataPreview, mlParams, dateRange]);

  const labelGridBlocked = useMemo(() => {
    if (!dataPreview?.walk_forward_readiness) {
      return true;
    }
    if (previewStale) {
      return true;
    }
    return !isReadinessReady(dataPreview.walk_forward_readiness);
  }, [dataPreview, previewStale]);

  useEffect(() => {
    if (!onWizardBridge) {
      return;
    }
    onWizardBridge({
      wizardStep: wizard.wizardStep,
      gateError: wizard.gateError,
      goNext: wizard.goNext,
      goBack: wizard.goBack,
      goToStep: wizard.goToStep,
      isUniverseLocked: wizard.isUniverseLocked,
      lockedConfig: wizard.lockedConfig,
      canNavigateToStep: (step) =>
        canNavigateToWizardStep(
          step,
          wizard.wizardStep,
          wizard.completedSteps,
          wizard.gateError,
        ),
      walkForwardParams,
      setWalkForwardParam,
      resetWalkForwardDefaults,
      walkForwardValidationError,
      minimumBarsRequired: minBars,
      availableBarCount,
      previewViableFolds: dataPreview?.walk_forward_readiness?.viable_folds ?? null,
    });
    return () => onWizardBridge(null);
  }, [
    onWizardBridge,
    wizard,
    walkForwardParams,
    setWalkForwardParam,
    resetWalkForwardDefaults,
    walkForwardValidationError,
    minBars,
    availableBarCount,
    dataPreview,
  ]);

  const evaluationStartDate = useMemo(
    () => resolveEvaluationStartDate(results?.ml_summary),
    [results?.ml_summary],
  );

  const simulationChartRecords = useMemo(() => {
    if (!evaluationStartDate) {
      return chartRecords;
    }
    return filterRecordsFromSimulationStart(chartRecords, evaluationStartDate);
  }, [chartRecords, evaluationStartDate]);

  const simulationPeriodLabel = useMemo(() => {
    if (!evaluationStartDate) {
      return null;
    }
    const endDate =
      results?.equity_curve[results.equity_curve.length - 1]?.date ??
      results?.end_date ??
      null;
    return formatSimulationPeriodLabel(evaluationStartDate, endDate);
  }, [evaluationStartDate, results]);

  const portfolioMetricsCaption = useMemo(() => {
    if (!simulationPeriodLabel) {
      return null;
    }
    if (results?.ml_summary?.evaluation_reason === 'first_trade') {
      return `Evaluation period: ${simulationPeriodLabel}. Portfolio metrics reflect active trading from first entry.`;
    }
    if (results?.ml_summary?.simulation_start_date) {
      return `Evaluation period: ${simulationPeriodLabel}. Portfolio metrics reflect out-of-sample simulation only.`;
    }
    return `Evaluation period: ${simulationPeriodLabel}.`;
  }, [results?.ml_summary, simulationPeriodLabel]);

  const macroWarning = useMemo(
    () =>
      usesMacroFeatures
        ? macroCoverageWarning(mlParams.macro_series_ids ?? [], ingestedMacroIds)
        : null,
    [usesMacroFeatures, mlParams.macro_series_ids, ingestedMacroIds],
  );

  const fundamentalsEntitled = useMemo(
    () => isFundamentalsEntitled(symbol, fundamentalsEntitlement),
    [symbol, fundamentalsEntitlement],
  );

  const entitlementWarning = useMemo(
    () =>
      usesFundamentalFeatures
        ? fundamentalEntitlementWarning(symbol, fundamentalsEntitled)
        : null,
    [usesFundamentalFeatures, symbol, fundamentalsEntitled],
  );

  const fundamentalsCoverageWarningText = useMemo(
    () =>
      usesFundamentalFeatures
        ? fundamentalCoverageWarning(symbol, symbolHasFundamentals)
        : null,
    [usesFundamentalFeatures, symbol, symbolHasFundamentals],
  );

  const fundamentalMetricWarning = useMemo(
    () =>
      usesFundamentalFeatures
        ? fundamentalMetricCoverageWarning(
            mlParams.fundamental_metrics ?? [],
            ingestedFundamentalMetrics,
          )
        : null,
    [usesFundamentalFeatures, mlParams.fundamental_metrics, ingestedFundamentalMetrics],
  );

  const selectableMacroSeries = useMemo(() => {
    const ids = new Set([...DEFAULT_MACRO_SERIES_IDS, ...(mlParams.macro_series_ids ?? [])]);
    return macroSeries.filter((item) => ids.has(item.series_id));
  }, [macroSeries, mlParams.macro_series_ids]);

  useEffect(() => {
    let cancelled = false;
    setLoadingCatalog(true);
    mlBacktestApi
      .listModels()
      .then((data) => {
        if (cancelled) return;
        setModels(data.models);
        const first = data.models[0];
        if (first) {
          setModelType(first.id);
          setMlParams(parseMlParams(first.params));
        }
      })
      .catch(() => {
        if (!cancelled) setError('Failed to load ML model catalog.');
      })
      .finally(() => {
        if (!cancelled) setLoadingCatalog(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const loadSavedModels = useCallback(async () => {
    try {
      const data = await mlBacktestApi.listSavedModels();
      setSavedModels(data.models);
    } catch {
      setSavedModels([]);
    }
  }, []);

  useEffect(() => {
    void loadSavedModels();
  }, [loadSavedModels]);

  useEffect(() => {
    let cancelled = false;
    ingestionApi
      .listMacroSeries({ ingestedOnly: true, limit: 100 })
      .then((items) => {
        if (cancelled) return;
        setIngestedMacroIds(new Set(items.map((item) => item.series_id)));
      })
      .catch(() => {
        if (!cancelled) setIngestedMacroIds(new Set());
      });
    ingestionApi
      .listMacroSeries({ limit: 100 })
      .then((items) => {
        if (!cancelled) setMacroSeries(items);
      })
      .catch(() => {
        if (!cancelled) setMacroSeries([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    ingestionApi
      .getFundamentalsEntitlement()
      .then((data) => {
        if (!cancelled) setFundamentalsEntitlement(data as Record<string, unknown>);
      })
      .catch(() => {
        if (!cancelled) setFundamentalsEntitlement(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!symbol) {
      setSymbolHasFundamentals(false);
      setIngestedFundamentalMetrics(new Set());
      return;
    }

    let cancelled = false;
    ingestionApi
      .listFundamentalsCoverage()
      .then((data) => {
        if (cancelled) return;
        const item = data.items.find((row) => row.symbol.toUpperCase() === symbol.toUpperCase());
        setSymbolHasFundamentals(Boolean(item && item.metric_count > 0));
      })
      .catch(() => {
        if (!cancelled) setSymbolHasFundamentals(false);
      });

    const periodType = mlParams.fundamental_period_type ?? 'quarterly';
    ingestionApi
      .getFundamentals(symbol, { period_type: periodType, all: true, limit: 500 })
      .then((data) => {
        if (cancelled) return;
        setIngestedFundamentalMetrics(new Set(data.metrics.map((row) => row.metric_name)));
      })
      .catch(() => {
        if (!cancelled) setIngestedFundamentalMetrics(new Set());
      });

    return () => {
      cancelled = true;
    };
  }, [symbol, mlParams.fundamental_period_type]);

  useEffect(() => {
    if (!symbol) {
      setDecisionCoverage(null);
      return;
    }

    let cancelled = false;
    ingestionApi
      .getCoverage(symbol, decisionTimeframe, true)
      .then((raw) => {
        if (!cancelled) setDecisionCoverage(parseEffectiveCoverage(raw));
      })
      .catch(() => {
        if (!cancelled) setDecisionCoverage(null);
      });

    return () => {
      cancelled = true;
    };
  }, [symbol, decisionTimeframe, dateRange]);

  useEffect(() => {
    if (!selectedModel) return;

    const modelChanged = prevModelTypeRef.current !== modelType;
    prevModelTypeRef.current = modelType;

    const parsed = parseMlParams(selectedModel.params);
    const resolvedWalkForward = resolveWalkForwardParams(decisionTimeframe, availableBarCount);

    if (modelChanged) {
      walkForwardCustomizedRef.current = false;
      setMlParams((prev) => ({
        ...parsed,
        ...resolvedWalkForward,
        feature_mode: prev.feature_mode ?? parsed.feature_mode,
        macro_series_ids: prev.macro_series_ids ?? parsed.macro_series_ids,
        fundamental_metrics: prev.fundamental_metrics ?? parsed.fundamental_metrics,
        fundamental_period_type: prev.fundamental_period_type ?? parsed.fundamental_period_type,
      }));
      return;
    }

    if (walkForwardCustomizedRef.current) {
      return;
    }

    setMlParams((prev) => ({
      ...prev,
      ...resolvedWalkForward,
    }));
  }, [modelType, selectedModel, decisionTimeframe, availableBarCount]);

  const loadResultCharts = useCallback(
    async (full: MlBacktestResultsResponse) => {
      const range = chartDateRange(full as unknown as BacktestResultsResponse, dateRange);
      const decisionQuery = buildOhlcvQuery(decisionTimeframe, range);
      const decisionData = await marketDataApi.getOhlcv(symbol, decisionQuery);
      setChartRecords(decisionData.records);
    },
    [symbol, dateRange, decisionTimeframe],
  );

  const updateParam = (key: MlNumericParamKey, value: number) => {
    setMlParams((prev) => ({ ...prev, [key]: value }));
  };

  const updateFeatureMode = (featureMode: string) => {
    setMlParams((prev) => ({
      ...prev,
      feature_mode: featureMode,
      macro_series_ids:
        featureMode === 'prices_only'
          ? []
          : featureMode === 'prices_macro' || featureMode === 'prices_macro_fundamentals'
            ? prev.macro_series_ids?.length
              ? prev.macro_series_ids
              : [...DEFAULT_MACRO_SERIES_IDS]
            : prev.macro_series_ids,
      fundamental_metrics:
        featureMode === 'prices_macro_fundamentals'
          ? prev.fundamental_metrics?.length
            ? prev.fundamental_metrics
            : [...DEFAULT_FUNDAMENTAL_METRICS]
          : prev.fundamental_metrics,
      fundamental_period_type: prev.fundamental_period_type ?? 'quarterly',
    }));
  };

  const toggleFundamentalMetric = (metricCode: string) => {
    setMlParams((prev) => {
      const current = new Set(prev.fundamental_metrics ?? []);
      if (current.has(metricCode)) current.delete(metricCode);
      else current.add(metricCode);
      return { ...prev, fundamental_metrics: [...current] };
    });
  };

  const toggleMacroSeries = (seriesId: string) => {
    setMlParams((prev) => {
      const current = new Set(prev.macro_series_ids ?? []);
      if (current.has(seriesId)) current.delete(seriesId);
      else current.add(seriesId);
      return { ...prev, macro_series_ids: [...current] };
    });
  };

  const applySavedModel = (modelId: string) => {
    setSelectedSavedModelId(modelId);
    const saved = savedModels.find((item) => item.id === modelId);
    if (!saved) return;
    setModelType(saved.model_type);
    setMlParams((prev) => ({
      ...parseMlParams(saved.hyperparams),
      feature_mode: saved.feature_mode,
      model_id: saved.id,
    }));
  };

  const applyEditModel = useCallback((saved: MlSavedModel) => {
    setRunMode('walk_forward');
    setSelectedSavedModelId('');
    setModelType(saved.model_type);
    const nextParams = parseMlParams(saved.hyperparams);
    delete nextParams.model_id;
    setMlParams({
      ...nextParams,
      feature_mode: saved.feature_mode,
    });
  }, []);

  useEffect(() => {
    if (!initialEditModelId || appliedEditModelIdRef.current === initialEditModelId) {
      return;
    }

    const saved = savedModels.find((item) => item.id === initialEditModelId);
    if (saved) {
      applyEditModel(saved);
      appliedEditModelIdRef.current = initialEditModelId;
      return;
    }

    let cancelled = false;
    mlBacktestApi
      .getSavedModel(initialEditModelId)
      .then((model) => {
        if (cancelled) return;
        applyEditModel(model);
        appliedEditModelIdRef.current = initialEditModelId;
      })
      .catch(() => {
        if (!cancelled) {
          setError('Failed to load saved model for editing.');
        }
      });

    return () => {
      cancelled = true;
    };
  }, [initialEditModelId, savedModels, applyEditModel]);

  const buildRunParams = (): Partial<MlParams> => {
    const params: Partial<MlParams> = { ...mlParams };
    if (runMode === 'inference' && selectedSavedModelId) {
      params.model_id = selectedSavedModelId;
    } else {
      delete params.model_id;
    }
    return params;
  };

  const handleTrain = async () => {
    if (validationError) {
      setError(validationError);
      return;
    }

    setTraining(true);
    setError(null);
    setTrainResult(null);

    try {
      const ohlcvQuery = buildOhlcvQuery(decisionTimeframe, dateRange);
      const result = await mlBacktestApi.train({
        symbol,
        model_type: modelType,
        params: mlParams,
        timeframe: decisionTimeframe,
        ...apiRangeFromOhlcvQuery(ohlcvQuery),
      });
      setTrainResult(result);
      await loadSavedModels();
    } catch (err: unknown) {
      setError(extractErrorMessage(err, 'Model training failed.'));
    } finally {
      setTraining(false);
    }
  };

  const handleCompare = async () => {
    if (validationError) {
      setError(validationError);
      return;
    }

    setComparing(true);
    setError(null);
    setCompareResults([]);

    try {
      const ohlcvQuery = buildOhlcvQuery(decisionTimeframe, dateRange);
      const rangeParams = apiRangeFromOhlcvQuery(ohlcvQuery);
      const compareModes = ML_COMPARE_FEATURE_MODES.filter(
        (mode) => mode.value !== 'prices_macro_fundamentals' || fundamentalsEntitled,
      );

      const settled = await Promise.allSettled(
        compareModes.map(async (mode) => {
          const params = {
            ...mlParams,
            feature_mode: mode.value,
          };
          const run = await mlBacktestApi.run({
            symbol,
            model_type: modelType,
            params,
            timeframe: decisionTimeframe,
            initial_cash: initialCash,
            commission_bps: commissionBps,
            ...rangeParams,
          });
          const full = await mlBacktestApi.getResults(run.id);
          return { featureMode: mode.value, label: mode.label, run: full };
        }),
      );

      setCompareResults(
        settled.map((result, index) => {
          const mode = compareModes[index];
          if (result.status === 'fulfilled') {
            return result.value;
          }
          return {
            featureMode: mode.value,
            label: mode.label,
            run: null,
            error: extractErrorMessage(result.reason, 'Compare run failed.'),
          };
        }),
      );
    } catch (err: unknown) {
      setError(extractErrorMessage(err, 'Feature mode comparison failed.'));
    } finally {
      setComparing(false);
    }
  };

  const handleRun = async () => {
    if (validationError) {
      setError(validationError);
      return;
    }

    setRunning(true);
    setError(null);
    setChartError(null);
    setResults(null);
    setChartRecords([]);

    try {
      const ohlcvQuery = buildOhlcvQuery(decisionTimeframe, dateRange);
      const run = await mlBacktestApi.run({
        symbol,
        model_type: modelType,
        params: buildRunParams(),
        timeframe: decisionTimeframe,
        initial_cash: initialCash,
        commission_bps: commissionBps,
        ...apiRangeFromOhlcvQuery(ohlcvQuery),
      });
      const full = await mlBacktestApi.getResults(run.id);
      setResults(full);
      wizard.setArtifact({ hasRunResults: true });
      wizard.goToStep('results');
      try {
        await loadResultCharts(full);
      } catch (chartErr: unknown) {
        setChartError(extractErrorMessage(chartErr, 'Price chart data could not be loaded.'));
      }
    } catch (err: unknown) {
      setError(extractErrorMessage(err));
    } finally {
      setRunning(false);
    }
  };

  const buildRangeParams = () => {
    const ohlcvQuery = buildOhlcvQuery(decisionTimeframe, dateRange);
    return {
      symbol,
      params: mlParams,
      timeframe: decisionTimeframe,
      ...apiRangeFromOhlcvQuery(ohlcvQuery),
    };
  };

  const handleDataPreview = async () => {
    setPreviewLoading(true);
    setJobProgress(null);
    setError(null);
    try {
      const preview = await mlBacktestApi.dataPreview(buildRangeParams(), (job) => {
        setJobProgress(job.progress);
      });
      setDataPreview(preview);
      previewFingerprintRef.current = previewConfigFingerprint(mlParams, dateRange);
      wizard.setArtifact({ hasDataPreview: true });
    } catch (err: unknown) {
      setError(extractErrorMessage(err, 'Data preview failed.'));
    } finally {
      setPreviewLoading(false);
      setJobProgress(null);
    }
  };

  const handleLabelSearch = async () => {
    setLabelSearchLoading(true);
    setError(null);
    try {
      const response = await mlBacktestApi.labelSearch({
        ...buildRangeParams(),
        label_mode: mlParams.label_mode ?? 'binary',
        horizons: [2, 4, 6, 8, 10],
        thresholds: [0.01, 0.02],
      });
      setLabelSearchResults(response.results);
      wizard.setArtifact({ hasLabelSearch: true });
    } catch (err: unknown) {
      setError(extractErrorMessage(err, 'Label grid search failed.'));
    } finally {
      setLabelSearchLoading(false);
    }
  };

  const handleThresholdSearch = async () => {
    setThresholdLoading(true);
    setError(null);
    try {
      const response = await mlBacktestApi.thresholdSearch({
        ...buildRangeParams(),
        model_type: modelType,
      });
      setThresholdResults(response.results);
      wizard.setArtifact({ hasThresholdSearch: true });
    } catch (err: unknown) {
      setError(extractErrorMessage(err, 'Threshold search failed.'));
    } finally {
      setThresholdLoading(false);
    }
  };

  const handleHyperparamSearch = async () => {
    setHyperparamMessage(null);
    setError(null);
    try {
      const response = await mlBacktestApi.hyperparameterSearch({
        ...buildRangeParams(),
        model_type: modelType,
      });
      if (response.best_params && Object.keys(response.best_params).length > 0) {
        setMlParams((prev) => ({ ...prev, ...parseMlParams(response.best_params) }));
      }
      setHyperparamMessage(
        formatHyperparameterSearchMessage(response, selectedModel?.label),
      );
    } catch (err: unknown) {
      setError(extractErrorMessage(err, 'Hyperparameter search failed.'));
    }
  };

  const applyLabelSearchResult = (result: MlLabelSearchResult) => {
    const nextModelType = result.model_type ?? modelType;
    const nextModelLabel = result.model_label ?? result.model_type ?? null;
    const mergedParams: MlParams = {
      ...mlParams,
      label_horizon: result.label_horizon,
      label_threshold: result.label_threshold ?? mlParams.label_threshold,
      label_mode: result.label_mode === 'ternary' ? 'ternary' : 'binary',
    };
    if (result.model_type) {
      setModelType(result.model_type);
    }
    setAppliedModelLabel(nextModelLabel);
    setMlParams(mergedParams);
    wizard.completeStepAndAdvance(
      { hasLabelApplied: true },
      {
        modelType: nextModelType,
        modelLabel: nextModelLabel ?? undefined,
        mlParams: mergedParams,
      },
    );
  };

  const applyThresholdResult = (result: MlThresholdSearchResult) => {
    const mergedParams: MlParams = {
      ...mlParams,
      buy_threshold: result.buy_threshold ?? mlParams.buy_threshold,
      sell_threshold: result.sell_threshold ?? mlParams.sell_threshold,
      min_class_probability: result.min_class_probability ?? mlParams.min_class_probability,
    };
    setMlParams(mergedParams);
    wizard.completeStepAndAdvance(
      { hasThresholdApplied: true },
      { mlParams: mergedParams },
    );
  };

  const confirmCurrentThresholds = () => {
    wizard.completeStepAndAdvance(
      { hasThresholdApplied: true },
      { mlParams: { ...mlParams } },
    );
  };

  if (loadingCatalog) {
    return (
      <div className="flex justify-center py-12">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {stepVisible(activeWizardStep, ['universe']) && (
        <MlUniversePeriodSection
          symbol={symbol}
          decisionTimeframe={decisionTimeframe}
          dateRange={dateRange}
          onDateRangeChange={onDateRangeChange}
          walkForwardParams={walkForwardParams}
          onWalkForwardParamChange={setWalkForwardParam}
          onResetWalkForwardDefaults={resetWalkForwardDefaults}
          barCount={availableBarCount}
          rangeStart={universeRangeStart}
          rangeEnd={universeRangeEnd}
          barCountLoading={universeBarCountLoading}
          barCountError={universeBarCountError}
          budget={walkForwardBudget}
          walkForwardValidationError={walkForwardValidationError}
          viableFolds={dataPreview?.walk_forward_readiness?.viable_folds ?? null}
        />
      )}

      {activeWizardStep !== 'universe' && (
        <MlWizardSummaryCard
          symbol={symbol}
          decisionTimeframe={decisionTimeframe}
          lockedConfig={wizard.lockedConfig}
          modelLabel={appliedModelLabel ?? selectedModel?.label}
          dataPreview={dataPreview}
        />
      )}

      {stepVisible(activeWizardStep, ['data_prep', 'labeling', 'model', 'signals', 'run']) && (
      <section className="rounded-xl border border-slate-800 bg-surface-900 p-4 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {stepVisible(activeWizardStep, ['data_prep']) && (
          <label className="space-y-1 text-sm">
            <FieldLabel
              label={mlFieldLabel('feature_mode')}
              help={mlFieldHelp('feature_mode')}
              htmlFor="ml-feature-mode"
            />
            <select
              id="ml-feature-mode"
              value={mlParams.feature_mode}
              onChange={(e) => updateFeatureMode(e.target.value)}
              className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
            >
              {ML_FEATURE_MODES.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          )}

          {stepVisible(activeWizardStep, ['labeling']) && (
            <>
              <label className="space-y-1 text-sm">
                <FieldLabel label="Label mode" help="Binary predicts up/down. Ternary adds a ranging class using a return threshold." htmlFor="ml-label-mode" />
                <select
                  id="ml-label-mode"
                  value={mlParams.label_mode ?? 'binary'}
                  onChange={(e) =>
                    setMlParams((prev) => ({
                      ...prev,
                      label_mode: e.target.value as 'binary' | 'ternary',
                    }))
                  }
                  className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
                >
                  <option value="binary">Binary (up / down)</option>
                  <option value="ternary">Ternary (ranging / sell / buy)</option>
                </select>
              </label>
              {(mlParams.label_mode ?? 'binary') === 'ternary' && (
                <label className="space-y-1 text-sm">
                  <FieldLabel label="Label threshold" help="Minimum absolute forward return to classify as uptrend or downtrend." htmlFor="ml-label-threshold" />
                  <input
                    id="ml-label-threshold"
                    type="number"
                    step={0.005}
                    value={mlParams.label_threshold ?? 0.01}
                    onChange={(e) =>
                      setMlParams((prev) => ({
                        ...prev,
                        label_threshold: Number(e.target.value),
                      }))
                    }
                    className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
                  />
                </label>
              )}
            </>
          )}

          {stepVisible(activeWizardStep, ['model']) && (
            <div className="space-y-1 text-sm">
              <FieldLabel label={mlFieldLabel('model')} help={mlFieldHelp('model')} />
              <p className="text-slate-100 bg-surface-950 border border-slate-700 rounded-lg px-3 py-2">
                {appliedModelLabel ?? selectedModel?.label ?? modelType}
              </p>
            </div>
          )}

          {stepVisible(activeWizardStep, ['model', 'run']) && (
          <>
          <label className="space-y-1 text-sm">
            <FieldLabel
              label={mlFieldLabel('run_mode')}
              help={mlFieldHelp('run_mode')}
              htmlFor="ml-run-mode"
            />
            <select
              id="ml-run-mode"
              value={runMode}
              onChange={(e) => setRunMode(e.target.value as MlRunMode)}
              className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
            >
              <option value="walk_forward">Walk-forward (retrain each fold)</option>
              <option value="inference">Use saved model (inference only)</option>
            </select>
          </label>

          {runMode === 'inference' && (
            <label className="space-y-1 text-sm">
              <FieldLabel
                label={mlFieldLabel('saved_model')}
                help={mlFieldHelp('saved_model')}
                htmlFor="ml-saved-model"
              />
              <select
                id="ml-saved-model"
                value={selectedSavedModelId}
                onChange={(e) => applySavedModel(e.target.value)}
                className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
              >
                <option value="">Select a saved model…</option>
                {savedModels.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
          )}

          {isRandomForestModel(modelType) && (
            <label className="space-y-1 text-sm">
              <FieldLabel
                label={mlFieldLabel('random_forest_estimators')}
                help={mlFieldHelp('random_forest_estimators')}
                htmlFor="ml-param-rf-estimators"
              />
              <input
                id="ml-param-rf-estimators"
                type="number"
                value={mlParams.random_forest_estimators ?? 100}
                min={selectedModel?.constraints.random_forest_estimators?.min}
                max={selectedModel?.constraints.random_forest_estimators?.max}
                onChange={(e) => updateParam('random_forest_estimators', Number(e.target.value))}
                className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
              />
            </label>
          )}

          {isGradientBoostingModel(modelType) && (
            <label className="space-y-1 text-sm">
              <FieldLabel
                label={mlFieldLabel('gradient_boosting_max_iter')}
                help={mlFieldHelp('gradient_boosting_max_iter')}
                htmlFor="ml-param-gb-max-iter"
              />
              <input
                id="ml-param-gb-max-iter"
                type="number"
                value={mlParams.gradient_boosting_max_iter ?? 100}
                min={selectedModel?.constraints.gradient_boosting_max_iter?.min}
                max={selectedModel?.constraints.gradient_boosting_max_iter?.max}
                onChange={(e) =>
                  setMlParams((prev) => ({
                    ...prev,
                    gradient_boosting_max_iter: Number(e.target.value),
                  }))
                }
                className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
              />
            </label>
          )}

          </>
          )}

          {stepVisible(activeWizardStep, ['run']) && (
          <>
          <label className="space-y-1 text-sm">
            <FieldLabel
              label={mlFieldLabel('initial_cash')}
              help={mlFieldHelp('initial_cash')}
              htmlFor="ml-initial-cash"
            />
            <input
              id="ml-initial-cash"
              type="number"
              value={initialCash}
              min={1}
              onChange={(e) => setInitialCash(Number(e.target.value))}
              className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
            />
          </label>

          <label className="space-y-1 text-sm">
            <FieldLabel
              label={mlFieldLabel('commission_bps')}
              help={mlFieldHelp('commission_bps')}
              htmlFor="ml-commission-bps"
            />
            <input
              id="ml-commission-bps"
              type="number"
              value={commissionBps}
              min={0}
              onChange={(e) => setCommissionBps(Number(e.target.value))}
              className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
            />
          </label>
          </>
          )}
        </div>

        {usesMacroFeatures && stepVisible(activeWizardStep, ['data_prep']) && (
          <div className="space-y-2">
            <FieldLabel
              label={mlFieldLabel('macro_series_ids')}
              help={mlFieldHelp('macro_series_ids')}
            />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-48 overflow-y-auto border border-slate-800 rounded-lg p-3">
              {selectableMacroSeries.map((item) => (
                <label
                  key={item.series_id}
                  className="flex items-start gap-2 text-sm text-slate-300 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={mlParams.macro_series_ids?.includes(item.series_id) ?? false}
                    onChange={() => toggleMacroSeries(item.series_id)}
                    className="mt-1"
                  />
                  <span>
                    <span className="font-medium text-slate-200">{item.series_id}</span>
                    <span className="block text-xs text-slate-500">{item.title}</span>
                  </span>
                </label>
              ))}
            </div>
            {macroWarning && (
              <p className="text-xs text-amber-200/80">{macroWarning}</p>
            )}
          </div>
        )}

        {usesFundamentalFeatures && stepVisible(activeWizardStep, ['data_prep']) && (
          <div className="space-y-3">
            <label className="space-y-1 text-sm block">
              <FieldLabel
                label={mlFieldLabel('fundamental_period_type')}
                help={mlFieldHelp('fundamental_period_type')}
                htmlFor="ml-fundamental-period"
              />
              <select
                id="ml-fundamental-period"
                value={mlParams.fundamental_period_type ?? 'quarterly'}
                onChange={(e) =>
                  setMlParams((prev) => ({
                    ...prev,
                    fundamental_period_type: e.target.value as 'quarterly' | 'annual',
                  }))
                }
                className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
              >
                <option value="quarterly">Quarterly</option>
                <option value="annual">Annual</option>
              </select>
            </label>

            <div className="space-y-2">
              <FieldLabel
                label={mlFieldLabel('fundamental_metrics')}
                help={mlFieldHelp('fundamental_metrics')}
              />
              {FUNDAMENTAL_GROUPS.map((group) => (
                <div key={group} className="space-y-2">
                  <p className="text-xs font-medium text-slate-400 uppercase tracking-wide">
                    {metricsByGroup(group)[0]?.groupLabel ?? group}
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 border border-slate-800 rounded-lg p-3">
                    {metricsByGroup(group).map((metric) => (
                      <label
                        key={metric.dataCode}
                        className="flex items-start gap-2 text-sm text-slate-300 cursor-pointer"
                      >
                        <input
                          type="checkbox"
                          checked={mlParams.fundamental_metrics?.includes(metric.dataCode) ?? false}
                          onChange={() => toggleFundamentalMetric(metric.dataCode)}
                          className="mt-1"
                        />
                        <span>
                          <span className="font-medium text-slate-200">{metric.label}</span>
                          <span className="block text-xs text-slate-500">{metric.dataCode}</span>
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {entitlementWarning && (
              <p className="text-xs text-amber-200/80">{entitlementWarning}</p>
            )}
            {fundamentalsCoverageWarningText && (
              <p className="text-xs text-amber-200/80">{fundamentalsCoverageWarningText}</p>
            )}
            {fundamentalMetricWarning && (
              <p className="text-xs text-amber-200/80">{fundamentalMetricWarning}</p>
            )}
            <p className="text-xs text-slate-500">
              Fundamentals are aligned to report publication dates. Sparse coverage can introduce
              survivorship bias when comparing symbols.
            </p>
          </div>
        )}

        {stepVisible(activeWizardStep, ['data_prep']) && (
          <div className="space-y-3 border-t border-slate-800 pt-4">
            <h3 className="text-sm font-medium text-slate-300">Multi-timeframe context</h3>
            <div className="flex flex-wrap gap-3">
              {CONTEXT_TIMEFRAME_OPTIONS.filter((tf) => tf !== decisionTimeframe).map((tf) => (
                <label key={tf} className="flex items-center gap-2 text-sm text-slate-300">
                  <input
                    type="checkbox"
                    checked={mlParams.context_timeframes?.includes(tf) ?? false}
                    onChange={() =>
                      setMlParams((prev) => {
                        const current = new Set(prev.context_timeframes ?? []);
                        if (current.has(tf)) current.delete(tf);
                        else current.add(tf);
                        return { ...prev, context_timeframes: [...current] };
                      })
                    }
                  />
                  {tf}
                </label>
              ))}
            </div>
            <h3 className="text-sm font-medium text-slate-300">Algo strategy features</h3>
            <div className="flex flex-wrap gap-3">
              {STRATEGY_FEATURE_OPTIONS.map((strategy) => (
                <label key={strategy.id} className="flex items-center gap-2 text-sm text-slate-300">
                  <input
                    type="checkbox"
                    checked={mlParams.strategy_feature_ids?.includes(strategy.id) ?? false}
                    onChange={() =>
                      setMlParams((prev) => {
                        const current = new Set(prev.strategy_feature_ids ?? []);
                        if (current.has(strategy.id)) current.delete(strategy.id);
                        else current.add(strategy.id);
                        return { ...prev, strategy_feature_ids: [...current] };
                      })
                    }
                  />
                  {strategy.label}
                </label>
              ))}
            </div>
            <p className="text-xs text-slate-500">
              Optional features merge with price features. If context or strategy columns are
              missing for a bar, that bar is excluded from training.
            </p>
            <button
              type="button"
              onClick={handleDataPreview}
              disabled={previewLoading}
              className="px-3 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-white text-sm"
            >
              {previewLoading
                ? jobProgress != null
                  ? `Loading preview… ${jobProgress}%`
                  : 'Loading preview…'
                : 'Preview data coverage'}
            </button>
            {previewLoading && (
              <p className="text-xs text-slate-500">
                Running in background worker.{' '}
                <Link to="/ingestion/jobs" className="text-brand-400 hover:text-brand-300">
                  View jobs
                </Link>
              </p>
            )}
            {dataPreview && (
              <div className="space-y-4">
                <MlWalkForwardReadinessCard
                  readiness={dataPreview.walk_forward_readiness}
                  warnings={dataPreview.warnings}
                />
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <div>
                    <h4 className="text-xs text-slate-400 mb-2">Bar counts by timeframe</h4>
                    <MlBarCountChart barCounts={dataPreview.bar_counts} />
                  </div>
                  <div>
                    <h4 className="text-xs text-slate-400 mb-2">Label class distribution</h4>
                    <MlClassDistributionChart
                      distribution={dataPreview.label_preview.class_distribution}
                    />
                  </div>
                </div>
                {usesMacroFeatures && dataPreview.macro_coverage.length > 0 && (
                  <div>
                    <h4 className="text-xs text-slate-400 mb-2">Macro ALFRED coverage</h4>
                    <MlMacroCoverageChart coverage={dataPreview.macro_coverage} />
                  </div>
                )}
                {dataPreview.warnings.map((warning) => (
                  <p key={warning} className="text-amber-200/80 text-xs">{warning}</p>
                ))}
                {usesMacroFeatures &&
                  dataPreview.macro_coverage.some((row) => row.release_date_pct < 100) && (
                  <p className="text-amber-200/80 text-xs">
                    Run{' '}
                    <Link to="/ingestion" className="text-brand-400 hover:text-brand-300 underline">
                      ALFRED backfill in Ingestion → FRED Macro
                    </Link>{' '}
                    to populate release dates for point-in-time macro features.
                  </p>
                )}
                <MlTrainingExportDialog
                  symbol={symbol}
                  modelType={modelType}
                  params={mlParams}
                  timeframe={decisionTimeframe}
                  {...exportRange}
                  dataPreview={dataPreview}
                  configSnapshot={workbookConfigSnapshot}
                />
              </div>
            )}
          </div>
        )}

        {stepVisible(activeWizardStep, ['labeling']) && (
          <div className="space-y-3 border-t border-slate-800 pt-4">
            {dataPreview && (
              <MlWalkForwardReadinessCard
                readiness={dataPreview.walk_forward_readiness}
                warnings={dataPreview.warnings}
                compact
              />
            )}
            {previewStale && (
              <p className="text-xs text-amber-200/80">
                Settings changed since the last data preview — go back to Data Prep and re-run
                preview before label grid search.
              </p>
            )}
            <div className="flex items-center gap-3">
              <h3 className="text-sm font-medium text-slate-300">Label grid search (all models)</h3>
              <button
                type="button"
                onClick={handleLabelSearch}
                disabled={labelSearchLoading || labelGridBlocked}
                className="px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs"
              >
                {labelSearchLoading ? 'Searching…' : 'Run grid search'}
              </button>
            </div>
            <p className="text-xs text-slate-500">
              Grid search evaluates label horizons 2, 4, 6, 8, and 10 bars. Universe label horizon
              applies after you Apply a result or continue with your current settings.
            </p>
            {labelGridBlocked && !labelSearchLoading && (
              <p className="text-xs text-amber-200/80">
                {!dataPreview?.walk_forward_readiness
                  ? 'Run data preview on Data Prep before label grid search.'
                  : previewStale
                    ? 'Re-run data preview — walk-forward settings changed since the last preview.'
                    : 'Walk-forward readiness shows zero viable folds — adjust universe or Data Prep settings before searching.'}
              </p>
            )}
            {labelSearchResults.length > 0 && (
              <>
                <MlLabelGridHeatmap results={labelSearchResults} />
                <MlLabelModelCompareChart results={labelSearchResults} />
              </>
            )}
            <MlLabelGridResults
              results={labelSearchResults}
              onApply={applyLabelSearchResult}
              readiness={dataPreview?.walk_forward_readiness}
            />
          </div>
        )}

        {stepVisible(activeWizardStep, ['signals']) && (
          <div className="space-y-3 border-t border-slate-800 pt-4">
            <h3 className="text-sm font-medium text-slate-300">Signal thresholds</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {(['buy_threshold', 'sell_threshold'] as const).map((key) => {
                const constraint = selectedModel?.constraints[key];
                return (
                  <label key={key} className="space-y-1 text-sm">
                    <FieldLabel
                      label={mlFieldLabel(key)}
                      help={mlFieldHelp(key)}
                      htmlFor={`ml-param-${key}`}
                    />
                    <input
                      id={`ml-param-${key}`}
                      type="number"
                      value={mlParams[key]}
                      min={constraint?.min}
                      max={constraint?.max}
                      step={0.01}
                      onChange={(e) => updateParam(key, Number(e.target.value))}
                      className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
                    />
                  </label>
                );
              })}
            </div>
            {validationError && (
              <p className="text-xs text-amber-200/80">{validationError}</p>
            )}
            <div className="flex flex-wrap items-center gap-3">
              <h3 className="text-sm font-medium text-slate-300">Threshold sweep (optional)</h3>
              <button
                type="button"
                onClick={handleThresholdSearch}
                disabled={thresholdLoading}
                className="px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-white text-xs"
              >
                {thresholdLoading ? 'Searching…' : 'Sweep thresholds'}
              </button>
              {thresholdResults[0] && (
                <button
                  type="button"
                  onClick={() => applyThresholdResult(thresholdResults[0])}
                  className="px-3 py-1.5 rounded-lg bg-brand-700 hover:bg-brand-600 text-white text-xs"
                >
                  Apply best
                </button>
              )}
              <button
                type="button"
                onClick={confirmCurrentThresholds}
                className="px-3 py-1.5 rounded-lg border border-slate-600 text-slate-300 text-xs"
              >
                Use current thresholds
              </button>
            </div>
            <MlThresholdSweepChart results={thresholdResults} />
          </div>
        )}

        {stepVisible(activeWizardStep, ['model']) && (
          <div className="border-t border-slate-800 pt-4">
            <button
              type="button"
              onClick={handleHyperparamSearch}
              disabled={selectedModel?.supports_hyperparameter_search === false}
              className="px-3 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm"
            >
              Auto-tune hyperparameters
            </button>
            {selectedModel?.supports_hyperparameter_search === false && (
              <p className="text-xs text-slate-500 mt-2">
                This model has no hyperparameters to auto-tune.
              </p>
            )}
            {hyperparamMessage && <p className="text-xs text-emerald-300 mt-2">{hyperparamMessage}</p>}
          </div>
        )}

        {selectedModel && (
          <p className="text-xs text-slate-500">{selectedModel.description}</p>
        )}

        <p className="text-xs text-amber-200/80">
          Minimum bars required: {minBars} (includes feature warmup).
          {runMode === 'walk_forward'
            ? ' Only out-of-sample predictions generate trades.'
            : ' Inference applies a frozen model to all valid bars.'}
          {availableBarCount != null && (
            <> Available {decisionTimeframe} bars: ~{availableBarCount}.</>
          )}
        </p>

        {barCoverageWarnings.map((warning) => (
          <p key={warning.timeframe} className="text-xs text-amber-200/80">
            {warning.message}
          </p>
        ))}

        {validationError && (
          <p className="text-xs text-red-400">{validationError}</p>
        )}

        {wizard.gateError && (
          <p className="text-xs text-amber-200/80">{wizard.gateError}</p>
        )}

        {trainResult && (
          <div className="rounded-lg border border-emerald-900/50 bg-emerald-950/20 p-3 text-sm text-emerald-100">
            Saved model <span className="font-medium">{trainResult.name}</span> (
            {formatMetricPercent(
              typeof trainResult.train_metrics.accuracy === 'number'
                ? (trainResult.train_metrics.accuracy as number)
                : null,
            )}{' '}
            train accuracy, {String(trainResult.train_metrics.sample_count ?? '—')} samples).
          </div>
        )}

        <div className="flex flex-wrap gap-3">
          {stepVisible(activeWizardStep, ['run']) && (
          <>
          <button
            type="button"
            onClick={handleRun}
            disabled={
              running ||
              comparing ||
              training ||
              !symbol ||
              Boolean(validationError) ||
              barCoverageWarnings.length > 0 ||
              (runMode === 'inference' && !selectedSavedModelId)
            }
            className="px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white text-sm font-medium"
          >
            {running ? 'Running ML backtest…' : 'Run ML backtest'}
          </button>

          <button
            type="button"
            onClick={handleTrain}
            disabled={
              running ||
              comparing ||
              training ||
              !symbol ||
              Boolean(validationError) ||
              barCoverageWarnings.length > 0 ||
              runMode === 'inference'
            }
            className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-white text-sm font-medium"
          >
            {training ? 'Training model…' : 'Train & save model'}
          </button>

          <button
            type="button"
            onClick={handleCompare}
            disabled={
              running ||
              comparing ||
              training ||
              !symbol ||
              Boolean(validationError) ||
              barCoverageWarnings.length > 0 ||
              runMode === 'inference'
            }
            className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-white text-sm font-medium"
          >
            {comparing ? 'Comparing feature modes…' : 'Compare feature modes'}
          </button>
          </>
          )}
        </div>
      </section>
      )}

      {compareResults.length > 0 && !comparing && stepVisible(activeWizardStep, ['run', 'results']) && (
        <MlComparePanel results={compareResults} />
      )}

      {error && <ErrorAlert message={error} />}
      {chartError && !error && <ErrorAlert message={chartError} />}

      {(running || comparing || training) && (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      )}

      {results && !running && stepVisible(activeWizardStep, ['results']) && (
        <div className="space-y-6">
          <MlTrainingExportDialog
            symbol={symbol}
            modelType={modelType}
            params={mlParams}
            timeframe={decisionTimeframe}
            {...exportRange}
            dataPreview={dataPreview}
            labelSearchResults={labelSearchResults}
            thresholdResults={thresholdResults}
            compareResults={compareResults}
            configSnapshot={workbookConfigSnapshot}
            runId={results.id}
          />
          {results.ml_summary && (
            <section className="rounded-xl border border-slate-800 bg-surface-900 p-4 space-y-3">
              <MlEvaluationScopeBanner
                summary={results.ml_summary}
                commissionBps={results.commission_bps}
              />
              <h2 className="text-lg font-semibold text-slate-200">ML summary</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <p className="text-slate-500">Feature mode</p>
                  <p className="text-slate-200">{results.ml_summary.feature_mode}</p>
                </div>
                <div>
                  <p className="text-slate-500">Run mode</p>
                  <p className="text-slate-200">{results.ml_summary.run_mode ?? 'walk_forward'}</p>
                </div>
                <div>
                  <p className="text-slate-500">OOS windows</p>
                  <p className="text-slate-200">{results.ml_summary.oos_window_count}</p>
                </div>
                <div>
                  <p className="text-slate-500">Mean OOS accuracy</p>
                  <p className="text-slate-200">
                    {formatOosAccuracy(results.ml_summary.mean_oos_accuracy)}
                  </p>
                </div>
                <div>
                  <p className="text-slate-500">Precision / Recall / F1</p>
                  <p className="text-slate-200">
                    {formatMetricPercent(results.ml_summary.precision)} /{' '}
                    {formatMetricPercent(results.ml_summary.recall)} /{' '}
                    {formatMetricPercent(results.ml_summary.f1)}
                  </p>
                </div>
                <div>
                  <p className="text-slate-500">Signals</p>
                  <p className="text-slate-200">
                    buy {results.ml_summary.signal_counts.buy ?? 0} · sell{' '}
                    {results.ml_summary.signal_counts.sell ?? 0} · hold{' '}
                    {results.ml_summary.signal_counts.hold ?? 0}
                  </p>
                </div>
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <MlConfusionMatrix matrix={results.ml_summary.confusion_matrix ?? []} />
                <MlOosAccuracyChart accuracies={results.ml_summary.window_accuracies ?? []} />
              </div>
              {(results.ml_summary.roc_curves?.length ?? 0) > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-slate-300 mb-2">ROC curves (one-vs-rest)</h3>
                  <MlRocChart curves={results.ml_summary.roc_curves ?? []} />
                  {results.ml_summary.auc_scores && (
                    <p className="text-xs text-slate-500 mt-2">
                      AUC:{' '}
                      {Object.entries(results.ml_summary.auc_scores)
                        .map(([key, value]) => `${key}=${value ?? '—'}`)
                        .join(' · ')}
                    </p>
                  )}
                </div>
              )}
              {(results.ml_summary.shap_importance?.length ?? 0) > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-slate-300 mb-2">SHAP feature impact by class</h3>
                  <MlShapImportanceChart
                    items={results.ml_summary.shap_importance ?? []}
                    labelMode={results.ml_summary.label_mode === 'ternary' ? 'ternary' : 'binary'}
                  />
                  {results.ml_summary.label_mode !== 'ternary' && (
                    <p className="text-xs text-slate-500 mt-2">
                      Buy/sell signals are derived from probability thresholds; SHAP shows impact on
                      label classes (Down / Up), not trading signals.
                    </p>
                  )}
                </div>
              )}
              {(results.ml_summary.feature_importance?.length ?? 0) > 0 && (
                <MlFeatureImportanceChart items={results.ml_summary.feature_importance ?? []} />
              )}
              {results.ml_summary.feature_names.length > 0 && (
                <p className="text-xs text-slate-500">
                  Features: {results.ml_summary.feature_names.join(', ')}
                </p>
              )}
              {(results.ml_summary.macro_warnings?.length ?? 0) > 0 && (
                <p className="text-xs text-amber-200/80">
                  Macro warnings: {results.ml_summary.macro_warnings?.join(' ')}
                </p>
              )}
              {(results.ml_summary.fundamental_warnings?.length ?? 0) > 0 && (
                <p className="text-xs text-amber-200/80">
                  Fundamental warnings: {results.ml_summary.fundamental_warnings?.join(' ')}
                </p>
              )}
              {results.ml_summary.simulation_start_date && (
                <p className="text-xs text-slate-500">
                  Simulation from bar {results.ml_summary.simulation_start_bar_index ?? '—'}{' '}
                  ({results.ml_summary.simulation_start_date.slice(0, 10)});{' '}
                  {results.ml_summary.pre_oos_bars_excluded ?? 0} pre-OOS bars excluded from
                  portfolio simulation.
                </p>
              )}
            </section>
          )}

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-slate-200">Results</h2>
            {portfolioMetricsCaption && (
              <p className="text-xs text-slate-400">{portfolioMetricsCaption}</p>
            )}
            <BacktestMetricsCards metrics={results.metrics} />
            <BacktestPerformanceLabels metrics={results.metrics} />
          </section>

          <section className="space-y-3">
            <h3 className="text-sm font-medium text-slate-300">Equity curve</h3>
            <BacktestEquityChart
              strategy={results.equity_curve}
              benchmark={results.benchmark_equity_curve}
              initialCash={results.metrics?.initial_cash ?? undefined}
            />
          </section>

          {simulationChartRecords.length > 0 && (
            <section className="space-y-3">
              <h3 className="text-sm font-medium text-slate-300">Price chart with trades</h3>
              <OhlcvTimelineChart
                records={simulationChartRecords}
                timeframe={decisionTimeframe}
                trades={results.trades}
              />
            </section>
          )}

          {results.trades.length > 0 && (
            <section className="space-y-3">
              <h3 className="text-sm font-medium text-slate-300">Trades</h3>
              <div className="overflow-x-auto border border-slate-800 rounded-lg">
                <table className="min-w-full text-sm">
                  <thead className="bg-surface-900 text-slate-400">
                    <tr>
                      <th className="px-3 py-2 text-left">Entry</th>
                      <th className="px-3 py-2 text-left">Exit</th>
                      <th className="px-3 py-2 text-right">Entry px</th>
                      <th className="px-3 py-2 text-right">Exit px</th>
                      <th className="px-3 py-2 text-right">Shares</th>
                      <th className="px-3 py-2 text-right">PnL</th>
                      <th className="px-3 py-2 text-right">PnL %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortTradesByExit(results.trades).map((trade, index) => (
                      <tr
                        key={`${trade.entry_date}-${trade.exit_date}-${index}`}
                        className="border-t border-slate-800"
                      >
                        <td className="px-3 py-2 text-slate-200">{trade.entry_date}</td>
                        <td className="px-3 py-2 text-slate-200">{trade.exit_date}</td>
                        <td className="px-3 py-2 text-right text-slate-300">
                          {trade.entry_price.toFixed(2)}
                        </td>
                        <td className="px-3 py-2 text-right text-slate-300">
                          {trade.exit_price.toFixed(2)}
                        </td>
                        <td className="px-3 py-2 text-right text-slate-300">
                          {trade.shares.toFixed(2)}
                        </td>
                        <td
                          className={`px-3 py-2 text-right ${trade.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}
                        >
                          {trade.pnl.toFixed(2)}
                        </td>
                        <td
                          className={`px-3 py-2 text-right ${trade.pnl_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}
                        >
                          {formatBacktestPct(trade.pnl_pct)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
