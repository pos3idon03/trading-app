import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { backtestApi, ingestionApi, marketDataApi, mlBacktestApi } from '../../api/endpoints';
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
import MlAdvancedExplainabilitySection from '../charts/MlAdvancedExplainabilitySection';
import MlShapImportanceChart from '../charts/MlShapImportanceChart';
import OhlcvTimelineChart from '../charts/OhlcvTimelineChart';
import MlComparePanel from './MlComparePanel';
import MlTrainingExportDialog from './MlTrainingExportDialog';
import MlUniversePeriodSection from './MlUniversePeriodSection';
import MlWizardSummaryCard from './MlWizardSummaryCard';
import MlWalkForwardReadinessCard from './MlWalkForwardReadinessCard';
import MlTrainingFeaturesCard from './MlTrainingFeaturesCard';
import MlWalkForwardBarReadinessBanner from './MlWalkForwardBarReadinessBanner';
import MlExpertSettingsSection from './MlExpertSettingsSection';
import MlAlgoStrategyFeaturesPicker from './MlAlgoStrategyFeaturesPicker';
import MlDynamicIndicatorGroupsPicker from './MlDynamicIndicatorGroupsPicker';
import MlBarCountChart from '../charts/MlBarCountChart';
import MlClassDistributionChart from '../charts/MlClassDistributionChart';
import MlMacroCoverageChart from '../charts/MlMacroCoverageChart';
import MlLabelGridHeatmap from '../charts/MlLabelGridHeatmap';
import MlLabelModelCompareChart from '../charts/MlLabelModelCompareChart';
import MlLabelSearchModelMatrix from './MlLabelSearchModelMatrix';
import MlThresholdSweepChart from '../charts/MlThresholdSweepChart';
import { useMlWizard } from '../../hooks/useMlWizard';
import { useMlUniverseBarCount } from '../../hooks/useMlUniverseBarCount';
import {
  canNavigateToWizardStep,
  type MlLockedConfig,
} from '../../utils/mlWizardState';
import { buildMlWorkbookConfigSnapshot } from '../../utils/mlWorkbookExport';
import { formatBacktestPct, sortTradesByExit } from '../../utils/backtestData';
import { buildMlRunRequest } from '../../utils/mlRunRequest';
import type { MlTestingConfigSnapshot } from '../../utils/mlTestingSession';
import { apiRangeFromOhlcvQuery, chartDateRange } from '../../utils/multitimeframeBacktest';
import {
  DEFAULT_INDICATOR_GROUPS,
  validateIndicatorGroups,
  type MlIndicatorGroupId,
} from '../../utils/mlIndicatorGroups';
import {
  eligibleStrategyFeatureOptions,
  type StrategyFeatureOption,
} from '../../utils/mlStrategyFeatures';
import {
  DEFAULT_LABEL_MODE_BY_MODEL,
  DEFAULT_FUNDAMENTAL_METRICS,
  applyAlignedExitPolicy,
  DEFAULT_MACRO_SERIES_IDS,
  ML_EXIT_POLICIES,
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
  getCryptoMlPreset,
  labelSearchHorizons,
  resolveWalkForwardParams,
  validateMlParams,
  validateWalkForwardParams,
  type WalkForwardParamKey,
} from '../../utils/mlBacktestConfig';
import { assessWalkForwardBarReadiness } from '../../utils/mlWalkForwardBarReadiness';
import {
  buildDefaultLabelSearchMatrix,
  buildLabelSearchGate,
  enabledLabelSearchConfigs,
  maxLabelTailBars,
  type LabelSearchMatrixState,
} from '../../utils/mlLabelSearchMatrix';
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
import { sortMacroSeriesForDisplay } from '../../utils/macroCatalog';
import {
  filterRecordsFromSimulationStart,
  formatSimulationPeriodLabel,
  resolveEvaluationStartDate,
} from '../../utils/mlBacktestEvaluation';
import MlEvaluationScopeBanner from './MlEvaluationScopeBanner';
import {
  isReadinessReady,
  dataPrepPreviewFingerprint,
} from '../../utils/mlWalkForwardDiagnostics';
import { computeWalkForwardBudget } from '../../utils/mlUniverseBudget';
import {
  applyNoiseReductionDefaults,
  mergePrimaryMlChoices,
} from '../../utils/mlNoiseReductionPreset';
import { defaultMetaLabelBaseStrategyId } from '../../utils/mlStrategyFeatures';

interface MLBacktestPanelProps {
  symbol: string;
  dateRange: DateRangeValue;
  onDateRangeChange: (value: DateRangeValue) => void;
  decisionTimeframe: string;
  assetType?: string;
  wizardStep?: MlWizardStep;
  onWizardBridge?: (bridge: MlWizardBridge | null) => void;
  initialEditModelId?: string;
  initialTestingBootstrap?: MlTestingConfigSnapshot | null;
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
  assetType = 'stock',
  wizardStep,
  onWizardBridge,
  initialEditModelId,
  initialTestingBootstrap,
}: MLBacktestPanelProps) {
  const [models, setModels] = useState<MlModelCatalogItem[]>([]);
  const [modelType, setModelType] = useState('ml_gradient_boosting');
  const [mlParams, setMlParams] = useState<MlParams>(() =>
    applyNoiseReductionDefaults(DEFAULT_ML_PARAMS),
  );
  const [showExpertSettings, setShowExpertSettings] = useState(false);
  const [initialCash, setInitialCash] = useState(10_000);
  const [universeSymbols, setUniverseSymbols] = useState('');
  const [universeId, setUniverseId] = useState<number | null>(null);
  const [universes, setUniverses] = useState<{ id: number; name: string }[]>([]);
  const [commissionBps, setCommissionBps] = useState(5);
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [strategyFeatureOptions, setStrategyFeatureOptions] = useState<StrategyFeatureOption[]>(
    [],
  );
  const [loadingStrategyCatalog, setLoadingStrategyCatalog] = useState(true);
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
  const [labelSearchMatrix, setLabelSearchMatrix] = useState<LabelSearchMatrixState>({});
  const [labelSearchLoading, setLabelSearchLoading] = useState(false);
  const [thresholdResults, setThresholdResults] = useState<MlThresholdSearchResult[]>([]);
  const [thresholdLoading, setThresholdLoading] = useState(false);
  const [hyperparamMessage, setHyperparamMessage] = useState<string | null>(null);
  const [appliedModelLabel, setAppliedModelLabel] = useState<string | null>(null);
  const walkForwardCustomizedRef = useRef(false);
  const prevModelTypeRef = useRef(modelType);
  const previewFingerprintRef = useRef<string | null>(null);
  const labelSearchCenterRef = useRef<number | null>(null);
  const prevDateRangeRef = useRef(JSON.stringify(dateRange));
  const cryptoPresetAppliedRef = useRef<string | null>(null);
  const testingBootstrapAppliedRef = useRef(false);
  const isCryptoAsset = assetType === 'crypto';

  useEffect(() => {
    if (!initialTestingBootstrap || testingBootstrapAppliedRef.current) return;
    testingBootstrapAppliedRef.current = true;
    setModelType(initialTestingBootstrap.modelType);
    setMlParams(initialTestingBootstrap.mlParams);
    setInitialCash(initialTestingBootstrap.initialCash);
    setCommissionBps(initialTestingBootstrap.commissionBps);
    onDateRangeChange(initialTestingBootstrap.dateRange);
    walkForwardCustomizedRef.current = true;
  }, [initialTestingBootstrap, onDateRangeChange]);

  const applyCryptoTrainingDefaults = useCallback(() => {
    setMlParams(getCryptoMlPreset(decisionTimeframe));
    setModelType('ml_xgboost');
    setCommissionBps(20);
    walkForwardCustomizedRef.current = false;
  }, [decisionTimeframe]);

  useEffect(() => {
    if (!isCryptoAsset || !symbol || loadingCatalog) return;
    const key = `${symbol}:${decisionTimeframe}`;
    if (cryptoPresetAppliedRef.current === key) return;
    applyCryptoTrainingDefaults();
    cryptoPresetAppliedRef.current = key;
  }, [isCryptoAsset, symbol, decisionTimeframe, loadingCatalog, applyCryptoTrainingDefaults]);

  useEffect(() => {
    if (isCryptoAsset) return;
    cryptoPresetAppliedRef.current = null;
  }, [isCryptoAsset, symbol]);

  useEffect(() => {
    mlBacktestApi.listUniverses().then((res) => setUniverses(res.universes)).catch(() => {});
  }, []);

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

  useEffect(() => {
    if (models.length === 0) {
      return;
    }
    setLabelSearchMatrix((prev) => {
      if (Object.keys(prev).length > 0) {
        return prev;
      }
      return buildDefaultLabelSearchMatrix(models);
    });
  }, [models]);

  const labelSearchGate = useMemo(
    () => buildLabelSearchGate(labelSearchMatrix, labelSearchResults),
    [labelSearchMatrix, labelSearchResults],
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
    labelSearchGate,
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
      const resolved = resolveWalkForwardParams(decisionTimeframe, barCount, assetType);
      setMlParams((prev) => ({ ...prev, ...resolved }));
    },
    [decisionTimeframe, assetType],
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

  const validationError = useMemo(() => {
    const base = validateMlParams(mlParams, selectedModel);
    if (base) return base;
    return validateIndicatorGroups(mlParams);
  }, [mlParams, selectedModel]);

  const minBars = useMemo(() => minimumBarsRequired(mlParams), [mlParams]);

  const lockedWalkForwardParams = useMemo(
    () => pickWalkForwardParams(wizard.lockedConfig.mlParams ?? mlParams),
    [wizard.lockedConfig.mlParams, mlParams],
  );

  const dataPrepBarReadiness = useMemo(() => {
    const previewBars = dataPreview?.walk_forward_readiness?.total_bars;
    const barCount =
      previewBars ??
      availableBarCount ??
      wizard.lockedConfig.availableBarCountAtLock ??
      null;
    return assessWalkForwardBarReadiness(barCount, lockedWalkForwardParams, {
      assetType,
      timeframe: decisionTimeframe,
      labelMode: mlParams.label_mode,
      maxHorizonBars: mlParams.max_horizon_bars,
    });
  }, [
    dataPreview?.walk_forward_readiness?.total_bars,
    availableBarCount,
    wizard.lockedConfig.availableBarCountAtLock,
    lockedWalkForwardParams,
    assetType,
    decisionTimeframe,
    mlParams.label_mode,
    mlParams.max_horizon_bars,
  ]);

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
    return dataPrepPreviewFingerprint(mlParams, dateRange) !== previewFingerprintRef.current;
  }, [dataPreview, mlParams, dateRange]);

  const labelGridBlocked = useMemo(() => {
    if (!dataPreview?.walk_forward_readiness) {
      return true;
    }
    if (previewStale) {
      return true;
    }
    if (!isReadinessReady(dataPreview.walk_forward_readiness)) {
      return true;
    }
    const barCount = dataPreview.walk_forward_readiness.total_bars;
    const tail = maxLabelTailBars(
      labelSearchMatrix,
      mlParams.label_horizon,
      mlParams.max_horizon_bars ?? 48,
    );
    const barCheck = assessWalkForwardBarReadiness(barCount, lockedWalkForwardParams, {
      assetType,
      timeframe: decisionTimeframe,
      labelMode: tail.labelMode,
      maxHorizonBars: mlParams.max_horizon_bars,
    });
    return barCheck.status !== 'ready';
  }, [
    dataPreview,
    previewStale,
    labelSearchMatrix,
    mlParams.label_horizon,
    mlParams.max_horizon_bars,
    lockedWalkForwardParams,
    assetType,
    decisionTimeframe,
  ]);

  const labelSearchHorizonsList = useMemo(
    () => labelSearchHorizons(mlParams.label_horizon),
    [mlParams.label_horizon],
  );

  const labelSearchHorizonMismatch =
    labelSearchResults.length > 0 &&
    labelSearchCenterRef.current != null &&
    labelSearchCenterRef.current !== mlParams.label_horizon;

  useEffect(() => {
    if (!wizard.artifacts.hasLabelSearch) {
      setLabelSearchResults([]);
      labelSearchCenterRef.current = null;
    }
  }, [wizard.artifacts.hasLabelSearch]);

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

  const sortedMacroSeries = useMemo(
    () => sortMacroSeriesForDisplay(macroSeries),
    [macroSeries],
  );

  useEffect(() => {
    let cancelled = false;
    setLoadingCatalog(true);
    mlBacktestApi
      .listModels()
      .then((data) => {
        if (cancelled) return;
        setModels(data.models);
        const first = data.models[0];
        if (!first) return;
        if (assetType === 'crypto' && symbol) {
          applyCryptoTrainingDefaults();
          cryptoPresetAppliedRef.current = `${symbol}:${decisionTimeframe}`;
        } else {
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
  }, [assetType, symbol, decisionTimeframe, applyCryptoTrainingDefaults]);

  useEffect(() => {
    let cancelled = false;
    setLoadingStrategyCatalog(true);
    backtestApi
      .listStrategies()
      .then((data) => {
        if (cancelled) return;
        setStrategyFeatureOptions(eligibleStrategyFeatureOptions(data.strategies));
      })
      .catch(() => {
        if (!cancelled) setStrategyFeatureOptions([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingStrategyCatalog(false);
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
      .listMacroSeries()
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
    const resolvedWalkForward = resolveWalkForwardParams(
      decisionTimeframe,
      availableBarCount,
      assetType,
    );

    if (modelChanged) {
      walkForwardCustomizedRef.current = false;
      setMlParams((prev) =>
        applyNoiseReductionDefaults({
          ...parsed,
          ...resolvedWalkForward,
          feature_mode: prev.feature_mode ?? parsed.feature_mode,
          macro_series_ids: prev.macro_series_ids ?? parsed.macro_series_ids,
          fundamental_metrics: prev.fundamental_metrics ?? parsed.fundamental_metrics,
          fundamental_period_type: prev.fundamental_period_type ?? parsed.fundamental_period_type,
          label_mode: prev.label_mode ?? parsed.label_mode,
          include_news_sentiment: prev.include_news_sentiment ?? parsed.include_news_sentiment,
        }),
      );
      return;
    }

    if (walkForwardCustomizedRef.current) {
      return;
    }

    setMlParams((prev) => ({
      ...prev,
      ...resolvedWalkForward,
    }));
  }, [modelType, selectedModel, decisionTimeframe, availableBarCount, assetType]);

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
    setMlParams((prev) => {
      const withMode = {
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
      };
      return mergePrimaryMlChoices(withMode, { featureMode, assetType }, assetType);
    });
  };

  const onModelTypeChange = (nextModel: string) => {
    setModelType(nextModel);
    const labelMode = DEFAULT_LABEL_MODE_BY_MODEL[nextModel] ?? mlParams.label_mode ?? 'binary';
    setMlParams((prev) => {
      const patch: Partial<MlParams> = { label_mode: labelMode };
      if (labelMode === 'meta_label' && !prev.base_strategy_id) {
        patch.base_strategy_id = defaultMetaLabelBaseStrategyId(assetType);
      }
      return mergePrimaryMlChoices(
        { ...prev, ...patch },
        { labelMode, assetType, timeframe: decisionTimeframe },
        assetType,
      );
    });
  };

  const onLabelModeChange = (labelMode: MlParams['label_mode']) => {
    setMlParams((prev) => {
      const patch: Partial<MlParams> = { label_mode: labelMode };
      if (labelMode === 'meta_label' && !prev.base_strategy_id) {
        patch.base_strategy_id = defaultMetaLabelBaseStrategyId(assetType);
      }
      return mergePrimaryMlChoices(
        { ...prev, ...patch },
        { labelMode, assetType, timeframe: decisionTimeframe },
        assetType,
      );
    });
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
      const extraSymbols = universeSymbols
        .split(',')
        .map((s) => s.trim().toUpperCase())
        .filter(Boolean);
      const run = await mlBacktestApi.run({
        ...buildMlRunRequest({
          symbol,
          modelType,
          params: buildRunParams(),
          timeframe: decisionTimeframe,
          dateRange,
          initialCash,
          commissionBps,
        }),
        ...(extraSymbols.length > 0 ? { symbols: extraSymbols } : {}),
        ...(universeId != null ? { universe_id: universeId } : {}),
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
      previewFingerprintRef.current = dataPrepPreviewFingerprint(mlParams, dateRange);
      wizard.setArtifact({ hasDataPreview: true });
    } catch (err: unknown) {
      setError(extractErrorMessage(err, 'Data preview failed.'));
    } finally {
      setPreviewLoading(false);
      setJobProgress(null);
    }
  };

  const handleLabelSearch = async () => {
    const modelConfigs = enabledLabelSearchConfigs(labelSearchMatrix);
    if (modelConfigs.length === 0) {
      setError('Select at least one model for label grid search.');
      return;
    }
    setLabelSearchLoading(true);
    setError(null);
    try {
      const response = await mlBacktestApi.labelSearch({
        ...buildRangeParams(),
        model_configs: modelConfigs,
        horizons: labelSearchHorizonsList,
        thresholds: [0.01, 0.02],
      });
      setLabelSearchResults(response.results);
      labelSearchCenterRef.current = mlParams.label_horizon;
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
      label_mode:
        result.label_mode === 'meta_label'
          ? 'meta_label'
          : result.label_mode === 'ternary'
            ? 'ternary'
            : 'binary',
    };
    if (result.model_type) {
      setModelType(result.model_type);
    }
    setAppliedModelLabel(nextModelLabel);
    setMlParams(mergedParams);
    const advanceError = wizard.completeStepAndAdvance(
      { hasLabelApplied: true },
      {
        modelType: nextModelType,
        modelLabel: nextModelLabel ?? undefined,
        mlParams: mergedParams,
      },
    );
    if (advanceError) {
      setError(advanceError);
    } else {
      setError(null);
    }
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
          assetType={assetType}
          labelMode={mlParams.label_mode}
          maxHorizonBars={mlParams.max_horizon_bars}
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
          universeSymbols={universeSymbols}
          onUniverseSymbolsChange={setUniverseSymbols}
          universes={universes}
          universeId={universeId}
          onUniverseIdChange={setUniverseId}
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
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs text-slate-500">
            All technical indicators with PCA denoising are applied by default.
          </p>
          {stepVisible(activeWizardStep, ['data_prep', 'model']) && (
            <button
              type="button"
              onClick={() => setShowExpertSettings((value) => !value)}
              className="text-xs text-brand-400 hover:text-brand-300"
            >
              {showExpertSettings ? 'Hide expert settings' : 'Expert settings'}
            </button>
          )}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {stepVisible(activeWizardStep, ['data_prep']) && isCryptoAsset && (
            <p className="text-xs text-emerald-300/90 rounded-lg border border-emerald-800/60 bg-emerald-950/40 px-3 py-2 mb-3">
              Crypto ML preset active: prices + macro (T10Y2Y, WALCL, WTREGEN), news sentiment,
              meta-label gatekeeper on step 3, XGBoost, 20 bps commission. Use 1h timeframe for
              hourly crypto training.
            </p>
          )}
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

          {stepVisible(activeWizardStep, ['data_prep']) && (
          <label className="flex items-center gap-2 text-sm self-end pb-2">
            <input
              type="checkbox"
              checked={mlParams.include_news_sentiment ?? false}
              onChange={(e) =>
                setMlParams((prev) =>
                  mergePrimaryMlChoices(
                    { ...prev, include_news_sentiment: e.target.checked },
                    {
                      includeNewsSentiment: e.target.checked,
                      assetType,
                      timeframe: decisionTimeframe,
                    },
                    assetType,
                  ),
                )
              }
              className="rounded border-slate-600"
            />
            <FieldLabel
              label={mlFieldLabel('include_news_sentiment')}
              help={mlFieldHelp('include_news_sentiment')}
            />
          </label>
          )}

          {stepVisible(activeWizardStep, ['model']) && (
            <label className="space-y-1 text-sm">
              <FieldLabel label={mlFieldLabel('model')} help={mlFieldHelp('model')} htmlFor="ml-model" />
              <select
                id="ml-model"
                value={modelType}
                onChange={(e) => onModelTypeChange(e.target.value)}
                className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
              >
                {models.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
          )}

          {stepVisible(activeWizardStep, ['model']) && (
            <label className="space-y-1 text-sm">
              <FieldLabel
                label={mlFieldLabel('label_mode')}
                help={mlFieldHelp('label_mode')}
                htmlFor="ml-label-mode"
              />
              <select
                id="ml-label-mode"
                value={mlParams.label_mode ?? 'binary'}
                onChange={(e) => onLabelModeChange(e.target.value as MlParams['label_mode'])}
                className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
              >
                <option value="binary">Binary</option>
                <option value="ternary">Ternary</option>
                <option value="meta_label">Meta-label</option>
              </select>
            </label>
          )}

          {usesMacroFeatures && stepVisible(activeWizardStep, ['data_prep']) && macroWarning && (
            <p className="text-xs text-amber-200/80 md:col-span-2 xl:col-span-4">{macroWarning}</p>
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

          <label className="space-y-1 text-sm">
            <FieldLabel
              label={mlFieldLabel('slippage_bps')}
              help={mlFieldHelp('slippage_bps')}
              htmlFor="ml-slippage-bps"
            />
            <input
              id="ml-slippage-bps"
              type="number"
              value={mlParams.slippage_bps ?? 0}
              min={0}
              onChange={(e) =>
                setMlParams((prev) => ({
                  ...prev,
                  slippage_bps: Number(e.target.value),
                }))
              }
              className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
            />
          </label>
          </>
          )}
        </div>

        {showExpertSettings && stepVisible(activeWizardStep, ['data_prep', 'model']) && (
          <MlExpertSettingsSection
            mlParams={mlParams}
            onParamsChange={(patch) => setMlParams((prev) => ({ ...prev, ...patch }))}
            assetType={assetType}
            timeframe={decisionTimeframe}
            walkForwardParams={walkForwardParams}
            onWalkForwardChange={setWalkForwardParam}
            onWarmupChange={(value) => setMlParams((prev) => ({ ...prev, warmup_bars: value }))}
            onResetWalkForwardDefaults={resetWalkForwardDefaults}
            barCount={availableBarCount}
            barCountLoading={universeBarCountLoading}
            budget={walkForwardBudget}
            walkForwardError={walkForwardValidationError}
            indicatorError={validateIndicatorGroups(mlParams)}
            macroSeries={sortedMacroSeries}
            ingestedMacroIds={ingestedMacroIds}
            strategyOptions={strategyFeatureOptions}
            loadingStrategies={loadingStrategyCatalog}
            isMetaLabel={mlParams.label_mode === 'meta_label'}
            selectedModel={selectedModel}
          />
        )}

        {showExpertSettings && usesFundamentalFeatures && stepVisible(activeWizardStep, ['data_prep']) && (
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
            <MlWalkForwardBarReadinessBanner readiness={dataPrepBarReadiness} />
            {wizard.lockedConfig.availableBarCountAtLock != null &&
              dataPreview?.walk_forward_readiness?.total_bars != null &&
              wizard.lockedConfig.availableBarCountAtLock !==
                dataPreview.walk_forward_readiness.total_bars && (
                <p className="text-xs text-amber-200/90">
                  Universe showed{' '}
                  {wizard.lockedConfig.availableBarCountAtLock.toLocaleString()} bars; preview loaded{' '}
                  {dataPreview.walk_forward_readiness.total_bars.toLocaleString()}. Use preview
                  counts for walk-forward readiness.
                </p>
              )}
            <h3 className="text-sm font-medium text-slate-300">Multi-timeframe context</h3>
            {showExpertSettings && (
            <>
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
            <MlAlgoStrategyFeaturesPicker
              options={strategyFeatureOptions}
              selectedIds={mlParams.strategy_feature_ids ?? []}
              onToggle={(strategyId) =>
                setMlParams((prev) => {
                  const current = new Set(prev.strategy_feature_ids ?? []);
                  if (current.has(strategyId)) current.delete(strategyId);
                  else current.add(strategyId);
                  return { ...prev, strategy_feature_ids: [...current] };
                })
              }
              loading={loadingStrategyCatalog}
            />
            <MlDynamicIndicatorGroupsPicker
              enabled={Boolean(mlParams.dynamic_indicator_selection)}
              selectedGroups={mlParams.indicator_groups ?? DEFAULT_INDICATOR_GROUPS}
              onEnabledChange={(enabled) =>
                setMlParams((prev) => ({
                  ...prev,
                  dynamic_indicator_selection: enabled,
                  indicator_groups:
                    prev.indicator_groups?.length
                      ? prev.indicator_groups
                      : [...DEFAULT_INDICATOR_GROUPS],
                }))
              }
              onToggleGroup={(groupId) =>
                setMlParams((prev) => {
                  const current = new Set(
                    (prev.indicator_groups ?? DEFAULT_INDICATOR_GROUPS) as MlIndicatorGroupId[],
                  );
                  if (current.has(groupId)) current.delete(groupId);
                  else current.add(groupId);
                  return { ...prev, indicator_groups: [...current] };
                })
              }
              validationError={validateIndicatorGroups(mlParams)}
            />
            <p className="text-xs text-slate-500">
              If context or strategy columns are missing for a bar, that bar is excluded from
              training.
            </p>
            </>
            )}
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
                <MlTrainingFeaturesCard
                  featureNames={dataPreview.feature_names ?? []}
                  featureGroups={dataPreview.feature_groups ?? {}}
                  alwaysIncluded={dataPreview.always_included_features ?? ['volume_rel_20']}
                  featureCount={dataPreview.feature_count ?? dataPreview.feature_names?.length ?? 0}
                  walkForwardReadiness={dataPreview.walk_forward_readiness}
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
                Data Prep settings changed since the last preview — go back to Data Prep and re-run
                preview before label grid search.
              </p>
            )}
            {labelSearchHorizonMismatch && !previewStale && (
              <p className="text-xs text-amber-200/80">
                Grid search was centered on {labelSearchCenterRef.current} bars; universe horizon is
                now {mlParams.label_horizon}. Results below are still from the previous search — re-run
                grid search to refresh for the new horizon.
              </p>
            )}
            <MlLabelSearchModelMatrix
              models={models}
              matrix={labelSearchMatrix}
              onChange={setLabelSearchMatrix}
              disabled={labelSearchLoading}
            />
            <div className="flex items-center gap-3">
              <h3 className="text-sm font-medium text-slate-300">Label grid search</h3>
              <button
                type="button"
                onClick={handleLabelSearch}
                disabled={
                  labelSearchLoading
                  || labelGridBlocked
                  || labelSearchGate.enabledModelIds.length === 0
                }
                className="px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs"
              >
                {labelSearchLoading ? 'Searching…' : 'Run grid search'}
              </button>
            </div>
            <p className="text-xs text-slate-500">
              Each selected model runs with its own label mode. Horizons{' '}
              {labelSearchHorizonsList.join(', ')} bars center on your Universe label horizon (
              {mlParams.label_horizon}); meta-label models use one evaluation (horizon ignored).
              Apply a result to set the final label horizon, label mode, and model.
            </p>
            {labelGridBlocked && !labelSearchLoading && (
              <p className="text-xs text-amber-200/80">
                {!dataPreview?.walk_forward_readiness
                  ? 'Run data preview on Data Prep before label grid search.'
                  : previewStale
                    ? 'Re-run data preview — Data Prep settings changed since the last preview.'
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
              {(mlParams.label_mode === 'meta_label'
                ? (['meta_gate_threshold'] as const)
                : (['buy_threshold', 'sell_threshold'] as const)
              ).map((key) => {
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
            <div className="space-y-3 rounded-lg border border-slate-800 bg-surface-950/50 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-medium text-slate-300">Trade exits</h3>
                <button
                  type="button"
                  onClick={() => setMlParams((prev) => applyAlignedExitPolicy(prev))}
                  className="text-xs rounded-lg border border-slate-700 px-3 py-1.5 text-slate-300 hover:bg-slate-800"
                >
                  Align exits with labels
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                <label className="space-y-1 text-sm">
                  <FieldLabel
                    label={mlFieldLabel('exit_policy')}
                    help={mlFieldHelp('exit_policy')}
                    htmlFor="ml-exit-policy"
                  />
                  <select
                    id="ml-exit-policy"
                    value={mlParams.exit_policy ?? ''}
                    onChange={(e) =>
                      setMlParams((prev) => ({
                        ...prev,
                        exit_policy: e.target.value as typeof prev.exit_policy,
                      }))
                    }
                    className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
                  >
                    <option value="">Auto (by label mode)</option>
                    {ML_EXIT_POLICIES.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="space-y-1 text-sm">
                  <FieldLabel
                    label={mlFieldLabel('max_hold_bars')}
                    help={mlFieldHelp('max_hold_bars')}
                    htmlFor="ml-max-hold-bars"
                  />
                  <input
                    id="ml-max-hold-bars"
                    type="number"
                    min={1}
                    value={mlParams.max_hold_bars ?? mlParams.label_horizon}
                    onChange={(e) =>
                      setMlParams((prev) => ({
                        ...prev,
                        max_hold_bars: Number(e.target.value),
                      }))
                    }
                    className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
                  />
                </label>
                {(mlParams.exit_policy === 'atr_bracket' ||
                  mlParams.exit_policy === 'combined' ||
                  mlParams.label_mode === 'meta_label') && (
                  <>
                    <label className="space-y-1 text-sm">
                      <FieldLabel
                        label={mlFieldLabel('profit_atr_mult')}
                        help={mlFieldHelp('profit_atr_mult')}
                        htmlFor="ml-profit-atr"
                      />
                      <input
                        id="ml-profit-atr"
                        type="number"
                        step={0.1}
                        min={0.1}
                        value={mlParams.profit_atr_mult ?? 2}
                        onChange={(e) =>
                          setMlParams((prev) => ({
                            ...prev,
                            profit_atr_mult: Number(e.target.value),
                          }))
                        }
                        className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
                      />
                    </label>
                    <label className="space-y-1 text-sm">
                      <FieldLabel
                        label={mlFieldLabel('stop_atr_mult')}
                        help={mlFieldHelp('stop_atr_mult')}
                        htmlFor="ml-stop-atr"
                      />
                      <input
                        id="ml-stop-atr"
                        type="number"
                        step={0.1}
                        min={0.1}
                        value={mlParams.stop_atr_mult ?? 1.5}
                        onChange={(e) =>
                          setMlParams((prev) => ({
                            ...prev,
                            stop_atr_mult: Number(e.target.value),
                          }))
                        }
                        className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
                      />
                    </label>
                  </>
                )}
              </div>
              <p className="text-xs text-slate-500">
                Threshold sweep ranks pairs by simulated profit factor using these exit rules.
              </p>
            </div>
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
              {(results.ml_summary.coefficient_importance?.length ?? 0) > 0 &&
                results.ml_summary.model_type === 'ml_logistic' && (
                  <div>
                    <h3 className="text-sm font-medium text-slate-300 mb-2">
                      Logistic coefficients (abs)
                    </h3>
                    <MlFeatureImportanceChart
                      items={results.ml_summary.coefficient_importance ?? []}
                    />
                  </div>
                )}
              <MlAdvancedExplainabilitySection summary={results.ml_summary} />
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
              {(results.ml_summary.survivorship_warnings?.length ?? 0) > 0 && (
                <p className="text-xs text-amber-200/80">
                  Survivorship warnings: {results.ml_summary.survivorship_warnings?.join(' ')}
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
                      <th className="px-3 py-2 text-left">Exit reason</th>
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
                        <td className="px-3 py-2 text-slate-400 text-xs">
                          {trade.exit_reason || '—'}
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
