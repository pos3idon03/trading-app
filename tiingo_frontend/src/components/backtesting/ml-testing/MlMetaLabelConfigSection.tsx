import type { MlModelCatalogItem, MlParams } from '../../../api/mlBacktestTypes';
import { DEFAULT_ML_PARAMS } from '../../../utils/mlBacktestConfig';
import { mlFieldHelp, mlFieldLabel } from '../../../utils/mlBacktestHelp';
import {
  DEFAULT_META_LABEL_BASE_STRATEGIES,
  type StrategyFeatureOption,
} from '../../../utils/mlStrategyFeatures';
import FieldLabel from '../../FieldLabel';

interface MlMetaLabelConfigSectionProps {
  mlParams: MlParams;
  baseStrategyOptions: StrategyFeatureOption[];
  selectedModel?: MlModelCatalogItem;
  disabled?: boolean;
  onChange: (patch: Partial<MlParams>) => void;
}

export default function MlMetaLabelConfigSection({
  mlParams,
  baseStrategyOptions,
  selectedModel,
  disabled = false,
  onChange,
}: MlMetaLabelConfigSectionProps) {
  const options =
    baseStrategyOptions.length > 0 ? baseStrategyOptions : DEFAULT_META_LABEL_BASE_STRATEGIES;
  const fallbackBaseId = options[0]?.id ?? 'ts_momentum';
  const baseId = mlParams.base_strategy_id ?? fallbackBaseId;
  const gateThreshold =
    mlParams.meta_gate_threshold ?? DEFAULT_ML_PARAMS.meta_gate_threshold ?? 0.65;
  const gateConstraint = selectedModel?.constraints.meta_gate_threshold;

  return (
    <section className="space-y-3 rounded-lg border border-slate-800 bg-surface-950/40 p-3">
      <div>
        <h3 className="text-sm font-medium text-slate-300">Meta-label trading</h3>
        <p className="text-xs text-slate-500 mt-1">
          Trades only on entry events from the base strategy below, when the model probability
          meets the gate. Algo strategy features above are model inputs only.
        </p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <label className="space-y-1 text-sm">
          <FieldLabel
            label={mlFieldLabel('base_strategy_id')}
            help={mlFieldHelp('base_strategy_id')}
            htmlFor="ml-test-base-strategy"
          />
          <select
            id="ml-test-base-strategy"
            value={baseId}
            disabled={disabled}
            onChange={(e) => onChange({ base_strategy_id: e.target.value })}
            className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 disabled:opacity-50"
          >
            {options.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1 text-sm">
          <FieldLabel
            label={mlFieldLabel('meta_gate_threshold')}
            help={mlFieldHelp('meta_gate_threshold')}
            htmlFor="ml-test-meta-gate"
          />
          <input
            id="ml-test-meta-gate"
            type="number"
            step={0.01}
            min={gateConstraint?.min ?? 0.51}
            max={gateConstraint?.max ?? 0.99}
            value={gateThreshold}
            disabled={disabled}
            onChange={(e) => onChange({ meta_gate_threshold: Number(e.target.value) })}
            className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
          />
        </label>
      </div>
    </section>
  );
}
