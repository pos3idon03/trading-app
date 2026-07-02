import type { MlModelCatalogItem, MlParams } from '../../api/mlBacktestTypes';
import type { MacroSeries } from '../../api/types';
import {
  DEFAULT_ML_PARAMS,
  ML_EXIT_POLICIES,
  WARMUP_BARS_CONSTRAINTS,
  featureModeUsesMacro,
} from '../../utils/mlBacktestConfig';
import { mlFieldHelp, mlFieldLabel } from '../../utils/mlBacktestHelp';
import type { WalkForwardBudget } from '../../utils/mlUniverseBudget';
import type { WalkForwardParamKey } from '../../utils/mlBacktestConfig';
import FieldLabel from '../FieldLabel';
import MlAlgoStrategyFeaturesPicker from './MlAlgoStrategyFeaturesPicker';
import MlDynamicIndicatorGroupsPicker from './MlDynamicIndicatorGroupsPicker';
import MlWalkForwardParamsControls from './MlWalkForwardParamsControls';
import MacroSeriesCategoryPicker from './MacroSeriesCategoryPicker';
import {
  DEFAULT_INDICATOR_GROUPS,
  type MlIndicatorGroupId,
} from '../../utils/mlIndicatorGroups';
import type { StrategyFeatureOption } from '../../utils/mlStrategyFeatures';

interface MlExpertSettingsSectionProps {
  mlParams: MlParams;
  onParamsChange: (patch: Partial<MlParams>) => void;
  assetType: string;
  timeframe: string;
  walkForwardParams: Pick<
    MlParams,
    'train_bars' | 'test_bars' | 'step_bars' | 'label_horizon' | 'warmup_bars'
  >;
  onWalkForwardChange: (key: WalkForwardParamKey, value: number) => void;
  onWarmupChange: (value: number) => void;
  onResetWalkForwardDefaults: () => void;
  barCount: number | null;
  barCountLoading?: boolean;
  budget: WalkForwardBudget | null;
  walkForwardError: string | null;
  indicatorError: string | null;
  macroSeries?: MacroSeries[];
  ingestedMacroIds?: Set<string>;
  strategyOptions?: StrategyFeatureOption[];
  loadingStrategies?: boolean;
  disabled?: boolean;
  showPortfolioFields?: boolean;
  initialCash?: number;
  commissionBps?: number;
  onInitialCashChange?: (value: number) => void;
  onCommissionBpsChange?: (value: number) => void;
  isMetaLabel?: boolean;
  selectedModel?: MlModelCatalogItem;
}

export default function MlExpertSettingsSection({
  mlParams,
  onParamsChange,
  assetType,
  timeframe,
  walkForwardParams,
  onWalkForwardChange,
  onWarmupChange,
  onResetWalkForwardDefaults,
  barCount,
  barCountLoading = false,
  budget,
  walkForwardError,
  indicatorError,
  macroSeries = [],
  ingestedMacroIds,
  strategyOptions = [],
  loadingStrategies = false,
  disabled = false,
  showPortfolioFields = false,
  initialCash,
  commissionBps,
  onInitialCashChange,
  onCommissionBpsChange,
  isMetaLabel = false,
  selectedModel,
}: MlExpertSettingsSectionProps) {
  const usesMacroFeatures = featureModeUsesMacro(mlParams.feature_mode);
  const usesFundamentalFeatures = mlParams.feature_mode === 'prices_macro_fundamentals';

  const toggleStrategy = (strategyId: string) => {
    const current = new Set(mlParams.strategy_feature_ids ?? []);
    if (current.has(strategyId)) {
      current.delete(strategyId);
    } else {
      current.add(strategyId);
    }
    onParamsChange({ strategy_feature_ids: [...current] });
  };

  const toggleIndicatorGroup = (groupId: MlIndicatorGroupId) => {
    const current = new Set(
      (mlParams.indicator_groups ?? DEFAULT_INDICATOR_GROUPS) as MlIndicatorGroupId[],
    );
    if (current.has(groupId)) {
      current.delete(groupId);
    } else {
      current.add(groupId);
    }
    onParamsChange({ indicator_groups: [...current] });
  };

  const toggleMacroSeries = (seriesId: string) => {
    const current = new Set(mlParams.macro_series_ids ?? []);
    if (current.has(seriesId)) {
      current.delete(seriesId);
    } else {
      current.add(seriesId);
    }
    onParamsChange({ macro_series_ids: [...current] });
  };

  return (
    <div className="space-y-5 border-t border-slate-800 pt-4">
      <MlWalkForwardParamsControls
        params={walkForwardParams}
        onChange={onWalkForwardChange}
        onResetDefaults={onResetWalkForwardDefaults}
        barCount={barCount}
        barCountLoading={barCountLoading}
        budget={budget}
        validationError={walkForwardError}
        assetType={assetType}
        timeframe={timeframe}
        labelMode={mlParams.label_mode}
        maxHorizonBars={mlParams.max_horizon_bars}
      />

      <label className="space-y-1 text-sm block max-w-xs">
        <FieldLabel
          label="Warmup bars"
          help="Bars skipped before the first train window to warm up indicators."
        />
        <input
          type="number"
          value={mlParams.warmup_bars ?? DEFAULT_ML_PARAMS.warmup_bars}
          min={WARMUP_BARS_CONSTRAINTS.min}
          max={WARMUP_BARS_CONSTRAINTS.max}
          disabled={disabled}
          onChange={(e) => onWarmupChange(Number(e.target.value))}
          className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
        />
      </label>

      {showPortfolioFields && onInitialCashChange != null && onCommissionBpsChange != null && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <label className="space-y-1 text-sm">
            <span className="text-slate-400">Initial cash</span>
            <input
              type="number"
              value={initialCash ?? 10_000}
              disabled={disabled}
              onChange={(e) => onInitialCashChange(Number(e.target.value))}
              className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
            />
          </label>
          <label className="space-y-1 text-sm">
            <span className="text-slate-400">Commission (bps)</span>
            <input
              type="number"
              value={commissionBps ?? 5}
              disabled={disabled}
              onChange={(e) => onCommissionBpsChange(Number(e.target.value))}
              className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
            />
          </label>
        </div>
      )}

      {usesMacroFeatures && macroSeries.length > 0 && (
        <MacroSeriesCategoryPicker
          series={macroSeries}
          selectedIds={mlParams.macro_series_ids ?? []}
          onToggle={toggleMacroSeries}
          ingestedIds={ingestedMacroIds}
        />
      )}

      <section className="space-y-4">
        <h3 className="text-sm font-medium text-slate-300">Feature enrichment</h3>
        <MlAlgoStrategyFeaturesPicker
          options={strategyOptions}
          selectedIds={mlParams.strategy_feature_ids ?? []}
          onToggle={toggleStrategy}
          loading={loadingStrategies}
          disabled={disabled}
        />
        <MlDynamicIndicatorGroupsPicker
          enabled={Boolean(mlParams.dynamic_indicator_selection)}
          selectedGroups={mlParams.indicator_groups ?? DEFAULT_INDICATOR_GROUPS}
          onEnabledChange={(enabled) =>
            onParamsChange({
              dynamic_indicator_selection: enabled,
              indicator_groups:
                mlParams.indicator_groups?.length
                  ? mlParams.indicator_groups
                  : [...DEFAULT_INDICATOR_GROUPS],
            })
          }
          onToggleGroup={toggleIndicatorGroup}
          disabled={disabled}
          validationError={indicatorError}
        />
      </section>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <label className="space-y-1 text-sm">
          <FieldLabel
            label={mlFieldLabel('correlation_prune_threshold')}
            help={mlFieldHelp('correlation_prune_threshold')}
          />
          <input
            type="number"
            min={0}
            max={1}
            step={0.05}
            disabled={disabled}
            value={mlParams.correlation_prune_threshold ?? 0.75}
            onChange={(e) =>
              onParamsChange({ correlation_prune_threshold: Number(e.target.value) })
            }
            className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
          />
        </label>

        <label className="flex items-center gap-2 text-sm text-slate-300 self-end pb-2">
          <input
            type="checkbox"
            disabled={disabled}
            checked={Boolean(mlParams.technical_pca_enabled)}
            onChange={(e) => onParamsChange({ technical_pca_enabled: e.target.checked })}
          />
          Technical PCA
        </label>

        <label className="space-y-1 text-sm">
          <span className="text-slate-400">Denoise method</span>
          <select
            disabled={disabled}
            value={mlParams.denoise_method ?? 'none'}
            onChange={(e) =>
              onParamsChange({
                denoise_method: e.target.value as MlParams['denoise_method'],
              })
            }
            className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
          >
            <option value="none">None</option>
            <option value="kalman">Kalman</option>
            <option value="wavelet">Wavelet</option>
          </select>
        </label>

        <label className="space-y-1 text-sm">
          <span className="text-slate-400">Exit policy</span>
          <select
            disabled={disabled}
            value={mlParams.exit_policy ?? 'label_horizon'}
            onChange={(e) =>
              onParamsChange({
                exit_policy: e.target.value as MlParams['exit_policy'],
              })
            }
            className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
          >
            {ML_EXIT_POLICIES.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {usesMacroFeatures && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <label className="space-y-1 text-sm">
            <FieldLabel
              label={mlFieldLabel('macro_features_mode')}
              help={mlFieldHelp('macro_features_mode')}
            />
            <select
              disabled={disabled}
              value={mlParams.macro_features_mode ?? 'changes_only'}
              onChange={(e) =>
                onParamsChange({
                  macro_features_mode: e.target.value as 'full' | 'changes_only',
                })
              }
              className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
            >
              <option value="full">Full (levels + changes)</option>
              <option value="changes_only">Changes only</option>
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-300 self-end pb-2">
            <input
              type="checkbox"
              disabled={disabled}
              checked={Boolean(mlParams.macro_pca_enabled)}
              onChange={(e) => onParamsChange({ macro_pca_enabled: e.target.checked })}
            />
            <FieldLabel
              label={mlFieldLabel('macro_pca_enabled')}
              help={mlFieldHelp('macro_pca_enabled')}
            />
          </label>
          <label className="space-y-1 text-sm">
            <FieldLabel
              label={mlFieldLabel('macro_pca_input_mode')}
              help={mlFieldHelp('macro_pca_input_mode')}
            />
            <select
              disabled={disabled}
              value={mlParams.macro_pca_input_mode ?? 'changes_only'}
              onChange={(e) =>
                onParamsChange({
                  macro_pca_input_mode: e.target.value as 'changes_only' | 'all_macro',
                })
              }
              className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
            >
              <option value="changes_only">Changes only</option>
              <option value="all_macro">All macro columns</option>
            </select>
          </label>
          <label className="space-y-1 text-sm">
            <FieldLabel
              label={mlFieldLabel('macro_pca_variance_threshold')}
              help={mlFieldHelp('macro_pca_variance_threshold')}
            />
            <input
              type="number"
              step={0.01}
              min={0.5}
              max={1}
              disabled={disabled}
              value={mlParams.macro_pca_variance_threshold ?? 0.85}
              onChange={(e) =>
                onParamsChange({ macro_pca_variance_threshold: Number(e.target.value) })
              }
              className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
            />
          </label>
        </div>
      )}

      {usesFundamentalFeatures && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <label className="flex items-center gap-2 text-sm text-slate-300">
            <input
              type="checkbox"
              disabled={disabled}
              checked={Boolean(mlParams.fundamental_pca_enabled)}
              onChange={(e) => onParamsChange({ fundamental_pca_enabled: e.target.checked })}
            />
            Fundamental PCA (KPI block)
          </label>
          <label className="space-y-1 text-sm">
            <span className="text-slate-400">Fundamental features mode</span>
            <select
              disabled={disabled}
              value={mlParams.fundamental_features_mode ?? 'growth_only'}
              onChange={(e) =>
                onParamsChange({
                  fundamental_features_mode: e.target.value as 'full' | 'growth_only',
                })
              }
              className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
            >
              <option value="full">Full (levels + growth)</option>
              <option value="growth_only">Growth only (YoY/QoQ)</option>
            </select>
          </label>
          <label className="space-y-1 text-sm">
            <span className="text-slate-400">Fundamental PCA variance threshold</span>
            <input
              type="number"
              step={0.01}
              min={0.5}
              max={1}
              disabled={disabled}
              value={mlParams.fundamental_pca_variance_threshold ?? 0.85}
              onChange={(e) =>
                onParamsChange({ fundamental_pca_variance_threshold: Number(e.target.value) })
              }
              className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
            />
          </label>
        </div>
      )}

      {!isMetaLabel && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <label className="space-y-1 text-sm">
            <FieldLabel
              label={mlFieldLabel('buy_threshold')}
              help={mlFieldHelp('buy_threshold')}
            />
            <input
              type="number"
              step={0.01}
              disabled={disabled}
              value={mlParams.buy_threshold}
              onChange={(e) => onParamsChange({ buy_threshold: Number(e.target.value) })}
              className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
            />
          </label>
          <label className="space-y-1 text-sm">
            <FieldLabel
              label={mlFieldLabel('sell_threshold')}
              help={mlFieldHelp('sell_threshold')}
            />
            <input
              type="number"
              step={0.01}
              disabled={disabled}
              value={mlParams.sell_threshold}
              onChange={(e) => onParamsChange({ sell_threshold: Number(e.target.value) })}
              className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
            />
          </label>
        </div>
      )}

      {isMetaLabel && selectedModel && (
        <label className="space-y-1 text-sm max-w-xs">
          <FieldLabel
            label={mlFieldLabel('meta_gate_threshold')}
            help={mlFieldHelp('meta_gate_threshold')}
          />
          <input
            type="number"
            step={0.01}
            disabled={disabled}
            value={mlParams.meta_gate_threshold ?? 0.65}
            onChange={(e) => onParamsChange({ meta_gate_threshold: Number(e.target.value) })}
            className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
          />
        </label>
      )}

      <label className="space-y-1 text-sm max-w-xs">
        <span className="text-slate-400">Label threshold</span>
        <input
          type="number"
          step={0.001}
          disabled={disabled}
          value={mlParams.label_threshold ?? 0.01}
          onChange={(e) => onParamsChange({ label_threshold: Number(e.target.value) })}
          className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
        />
      </label>
    </div>
  );
}
