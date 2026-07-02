import { useEffect, useMemo, useState } from 'react';
import type { MlModelCatalogItem, MlParams } from '../../../api/mlBacktestTypes';
import type { MacroSeries } from '../../../api/types';
import { sortMacroSeriesForDisplay } from '../../../utils/macroCatalog';
import FieldLabel from '../../FieldLabel';
import MlExpertSettingsSection from '../MlExpertSettingsSection';
import {
  DEFAULT_LABEL_MODE_BY_MODEL,
  ML_FEATURE_MODES,
  featureModeUsesMacro,
  macroCoverageWarning,
  pickWalkForwardParams,
  validateMlParams,
  validateWalkForwardParams,
  type WalkForwardParamKey,
} from '../../../utils/mlBacktestConfig';
import { mlFieldHelp, mlFieldLabel } from '../../../utils/mlBacktestHelp';
import { mergePrimaryMlChoices } from '../../../utils/mlNoiseReductionPreset';
import { computeWalkForwardBudget } from '../../../utils/mlUniverseBudget';
import type { MlTestingConfigSnapshot } from '../../../utils/mlTestingSession';
import MlTestingPeriodSummary from './MlTestingPeriodSummary';
import {
  defaultMetaLabelBaseStrategyId,
  type StrategyFeatureOption,
} from '../../../utils/mlStrategyFeatures';
import MlMetaLabelConfigSection from './MlMetaLabelConfigSection';
import { validateIndicatorGroups } from '../../../utils/mlIndicatorGroups';

interface MlTestingConfigPanelProps {
  draft: MlTestingConfigSnapshot;
  models: MlModelCatalogItem[];
  assetType: string;
  barCount: number | null;
  barCountLoading: boolean;
  validationError: string | null;
  running: boolean;
  jobProgress: number | null;
  onDraftChange: (draft: MlTestingConfigSnapshot) => void;
  onRun: () => void;
  onPreview?: () => void;
  previewLoading?: boolean;
  macroSeries?: MacroSeries[];
  ingestedMacroIds?: Set<string>;
  strategyOptions?: StrategyFeatureOption[];
  baseStrategyOptions?: StrategyFeatureOption[];
  loadingStrategies?: boolean;
}

export default function MlTestingConfigPanel({
  draft,
  models,
  assetType,
  barCount,
  barCountLoading,
  validationError,
  running,
  jobProgress,
  onDraftChange,
  onRun,
  onPreview,
  previewLoading = false,
  macroSeries = [],
  ingestedMacroIds,
  strategyOptions = [],
  baseStrategyOptions = [],
  loadingStrategies = false,
}: MlTestingConfigPanelProps) {
  const [showExpert, setShowExpert] = useState(false);
  const { mlParams, modelType } = draft;
  const usesMacroFeatures = featureModeUsesMacro(mlParams.feature_mode);

  const selectedModel = useMemo(
    () => models.find((item) => item.id === modelType),
    [models, modelType],
  );

  const walkForwardParams = useMemo(() => pickWalkForwardParams(mlParams), [mlParams]);
  const budget = useMemo(
    () =>
      barCount != null && barCount > 0
        ? computeWalkForwardBudget(barCount, walkForwardParams)
        : null,
    [barCount, walkForwardParams],
  );

  const wfError = useMemo(
    () => validateWalkForwardParams(walkForwardParams, barCount),
    [walkForwardParams, barCount],
  );

  const indicatorError = useMemo(() => validateIndicatorGroups(mlParams), [mlParams]);

  const mlError = useMemo(() => {
    const base = validateMlParams(mlParams, selectedModel);
    if (base) return base;
    return indicatorError;
  }, [mlParams, selectedModel, indicatorError]);

  const macroWarning = useMemo(() => {
    if (!usesMacroFeatures) return null;
    return macroCoverageWarning(mlParams.macro_series_ids ?? [], ingestedMacroIds ?? new Set());
  }, [usesMacroFeatures, mlParams.macro_series_ids, ingestedMacroIds]);

  const setParams = (patch: Partial<MlParams>) => {
    onDraftChange({ ...draft, mlParams: { ...mlParams, ...patch } });
  };

  const applyPrimaryChoices = (patch: Partial<MlParams>) => {
    const merged = mergePrimaryMlChoices(
      { ...mlParams, ...patch },
      {
        featureMode: patch.feature_mode,
        includeNewsSentiment: patch.include_news_sentiment,
        labelMode: patch.label_mode,
        timeframe: draft.timeframe,
        assetType,
      },
      assetType,
    );
    onDraftChange({ ...draft, mlParams: merged });
  };

  const onWalkForwardChange = (key: WalkForwardParamKey, value: number) => {
    setParams({ [key]: value });
  };

  const onWarmupChange = (value: number) => {
    setParams({ warmup_bars: value });
  };

  const onModelChange = (nextModel: string) => {
    const labelMode = DEFAULT_LABEL_MODE_BY_MODEL[nextModel] ?? mlParams.label_mode;
    const paramsPatch: Partial<MlParams> = { label_mode: labelMode };
    if (labelMode === 'meta_label') {
      paramsPatch.base_strategy_id =
        mlParams.base_strategy_id ?? defaultMetaLabelBaseStrategyId(assetType);
      if (nextModel === 'ml_lstm') {
        paramsPatch.lstm_seq_length = Math.min(mlParams.lstm_seq_length ?? 32, 12);
      }
    }
    onDraftChange({
      ...draft,
      modelType: nextModel,
      mlParams: mergePrimaryMlChoices(
        { ...mlParams, ...paramsPatch },
        { labelMode, assetType, timeframe: draft.timeframe },
        assetType,
      ),
    });
  };

  const onLabelModeChange = (labelMode: MlParams['label_mode']) => {
    const patch: Partial<MlParams> = { label_mode: labelMode };
    if (labelMode === 'meta_label') {
      if (!mlParams.base_strategy_id) {
        patch.base_strategy_id = defaultMetaLabelBaseStrategyId(assetType);
      }
      if (modelType === 'ml_lstm' && (mlParams.lstm_seq_length ?? 32) > 16) {
        patch.lstm_seq_length = 12;
      }
    }
    applyPrimaryChoices(patch);
  };

  const isMetaLabel = mlParams.label_mode === 'meta_label';

  useEffect(() => {
    if (!isMetaLabel || modelType !== 'ml_lstm') {
      return;
    }
    const patch: Partial<MlParams> = {};
    if (!mlParams.base_strategy_id) {
      patch.base_strategy_id = defaultMetaLabelBaseStrategyId(assetType);
    }
    if ((mlParams.lstm_seq_length ?? 32) > 16) {
      patch.lstm_seq_length = 12;
    }
    if (Object.keys(patch).length > 0) {
      setParams(patch);
    }
  }, [
    assetType,
    isMetaLabel,
    modelType,
    mlParams.base_strategy_id,
    mlParams.lstm_seq_length,
  ]);

  const resetWalkForwardDefaults = () => {
    applyPrimaryChoices({});
  };

  const canRun = !validationError && !wfError && !mlError && !running;

  const sortedMacroSeries = useMemo(
    () => sortMacroSeriesForDisplay(macroSeries),
    [macroSeries],
  );

  return (
    <section className="rounded-xl border border-slate-800 bg-surface-900 p-4 space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-lg font-semibold text-slate-200">Configuration</h2>
          <p className="text-xs text-slate-500 mt-1">
            All technical indicators with PCA denoising are applied by default.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowExpert((value) => !value)}
          className="text-xs text-brand-400 hover:text-brand-300"
        >
          {showExpert ? 'Hide expert settings' : 'Expert settings'}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <label className="space-y-1 text-sm">
          <FieldLabel
            label={mlFieldLabel('feature_mode')}
            help={mlFieldHelp('feature_mode')}
          />
          <select
            value={mlParams.feature_mode}
            onChange={(e) => applyPrimaryChoices({ feature_mode: e.target.value })}
            className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
          >
            {ML_FEATURE_MODES.map((mode) => (
              <option key={mode.value} value={mode.value}>
                {mode.label}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-1 text-sm">
          <FieldLabel label={mlFieldLabel('model')} help={mlFieldHelp('model')} />
          <select
            value={modelType}
            onChange={(e) => onModelChange(e.target.value)}
            className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
          >
            {models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.label}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-1 text-sm">
          <FieldLabel label={mlFieldLabel('label_mode')} help={mlFieldHelp('label_mode')} />
          <select
            value={mlParams.label_mode ?? 'binary'}
            onChange={(e) =>
              onLabelModeChange(e.target.value as MlParams['label_mode'])
            }
            className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
          >
            <option value="binary">Binary</option>
            <option value="ternary">Ternary</option>
            <option value="meta_label">Meta-label</option>
          </select>
        </label>

        <label className="flex items-center gap-2 text-sm text-slate-300 self-end pb-2">
          <input
            type="checkbox"
            checked={mlParams.include_news_sentiment ?? false}
            onChange={(e) =>
              applyPrimaryChoices({ include_news_sentiment: e.target.checked })
            }
            className="rounded border-slate-600"
          />
          <FieldLabel
            label={mlFieldLabel('include_news_sentiment')}
            help={mlFieldHelp('include_news_sentiment')}
          />
        </label>
      </div>

      {macroWarning && (
        <p className="text-xs text-amber-200/80">{macroWarning}</p>
      )}

      {isMetaLabel && (
        <MlMetaLabelConfigSection
          mlParams={mlParams}
          baseStrategyOptions={baseStrategyOptions}
          selectedModel={selectedModel}
          disabled={running}
          onChange={setParams}
        />
      )}

      <MlTestingPeriodSummary params={walkForwardParams} budget={budget} />

      {showExpert && (
        <MlExpertSettingsSection
          mlParams={mlParams}
          onParamsChange={setParams}
          assetType={assetType}
          timeframe={draft.timeframe}
          walkForwardParams={walkForwardParams}
          onWalkForwardChange={onWalkForwardChange}
          onWarmupChange={onWarmupChange}
          onResetWalkForwardDefaults={resetWalkForwardDefaults}
          barCount={barCount}
          barCountLoading={barCountLoading}
          budget={budget}
          walkForwardError={wfError}
          indicatorError={indicatorError}
          macroSeries={sortedMacroSeries}
          ingestedMacroIds={ingestedMacroIds}
          strategyOptions={strategyOptions}
          loadingStrategies={loadingStrategies}
          disabled={running}
          showPortfolioFields
          initialCash={draft.initialCash}
          commissionBps={draft.commissionBps}
          onInitialCashChange={(value) => onDraftChange({ ...draft, initialCash: value })}
          onCommissionBpsChange={(value) => onDraftChange({ ...draft, commissionBps: value })}
          isMetaLabel={isMetaLabel}
          selectedModel={selectedModel}
        />
      )}

      {(validationError || wfError || mlError) && (
        <p className="text-sm text-amber-200/90">
          {validationError ?? wfError ?? mlError}
        </p>
      )}

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          disabled={!canRun}
          onClick={onRun}
          className="px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-500 disabled:opacity-40"
        >
          {running ? 'Running ML backtest…' : 'Run backtest'}
        </button>
        {onPreview && (
          <button
            type="button"
            disabled={previewLoading || running}
            onClick={onPreview}
            className="px-4 py-2 rounded-lg border border-slate-700 text-slate-200 text-sm hover:bg-surface-800 disabled:opacity-40"
          >
            {previewLoading ? 'Previewing…' : 'Preview data'}
          </button>
        )}
        {jobProgress != null && running && (
          <span className="text-sm text-slate-400 self-center">
            Job progress: {Math.round(jobProgress)}%
          </span>
        )}
      </div>
    </section>
  );
}
