import FieldLabel from '../FieldLabel';
import {
  minimumBarsRequired,
  WALK_FORWARD_CONSTRAINTS,
  WALK_FORWARD_PARAM_KEYS,
  type WalkForwardParamKey,
  type WalkForwardParams,
} from '../../utils/mlBacktestConfig';
import { maxWalkForwardParamValue, type WalkForwardBudget } from '../../utils/mlUniverseBudget';
import { mlFieldHelp, mlFieldLabel } from '../../utils/mlBacktestHelp';

interface MlWalkForwardParamsControlsProps {
  params: WalkForwardParams;
  onChange: (key: WalkForwardParamKey, value: number) => void;
  onResetDefaults: () => void;
  barCount: number | null;
  budget: WalkForwardBudget | null;
  validationError: string | null;
  disabled?: boolean;
  viableFolds?: number | null;
}

export default function MlWalkForwardParamsControls({
  params,
  onChange,
  onResetDefaults,
  barCount,
  budget,
  validationError,
  disabled = false,
  viableFolds = null,
}: MlWalkForwardParamsControlsProps) {
  const minBars = minimumBarsRequired(params);

  return (
    <section className="rounded-xl border border-slate-800 bg-surface-950/40 p-4 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-medium text-slate-300">
          Walk-forward window (within selected period)
        </h3>
        <button
          type="button"
          onClick={onResetDefaults}
          disabled={disabled}
          className="text-xs text-brand-400 hover:text-brand-300 disabled:opacity-40"
        >
          Reset to timeframe defaults
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {WALK_FORWARD_PARAM_KEYS.map((key) => {
          const constraint = WALK_FORWARD_CONSTRAINTS[key];
          const rangeMax =
            barCount != null && barCount > 0
              ? maxWalkForwardParamValue(key, barCount, params)
              : constraint.max;
          const exceedsRange = barCount != null && params[key] > rangeMax;

          return (
            <label key={key} className="space-y-1 text-sm">
              <FieldLabel
                label={mlFieldLabel(key)}
                help={mlFieldHelp(key)}
                htmlFor={`ml-wf-${key}`}
              />
              <input
                id={`ml-wf-${key}`}
                type="number"
                value={params[key]}
                min={constraint.min}
                max={constraint.max}
                step={1}
                disabled={disabled}
                onChange={(e) => onChange(key, Number(e.target.value))}
                className={`w-full bg-surface-950 border rounded-lg px-3 py-2 text-slate-100 disabled:opacity-50 ${
                  exceedsRange ? 'border-amber-600' : 'border-slate-700'
                }`}
              />
              {barCount != null && (
                <p className={`text-xs ${exceedsRange ? 'text-amber-200/90' : 'text-slate-500'}`}>
                  Max for this range: {rangeMax}
                </p>
              )}
            </label>
          );
        })}
      </div>

      <p className="text-xs text-slate-500">
        Minimum bars required: {minBars} (includes 50-bar feature warmup).
        {budget != null && (
          <>
            {' '}
            Walk-forward budget: {budget.walkForwardBudget} bars · structural folds: ~
            {budget.structuralFolds}.
          </>
        )}
        {viableFolds != null && <> Viable folds from last preview: {viableFolds}.</>}
      </p>

      {validationError && (
        <p className="text-xs text-amber-200/80">{validationError}</p>
      )}
    </section>
  );
}
