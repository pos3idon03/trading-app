import { useMemo } from 'react';
import FieldLabel from '../FieldLabel';
import {
  WALK_FORWARD_CONSTRAINTS,
  WALK_FORWARD_PARAM_KEYS,
  type WalkForwardParamKey,
  type WalkForwardParams,
} from '../../utils/mlBacktestConfig';
import { maxWalkForwardParamValue, type WalkForwardBudget } from '../../utils/mlUniverseBudget';
import { assessWalkForwardBarReadiness } from '../../utils/mlWalkForwardBarReadiness';
import { mlFieldHelp, mlFieldLabel } from '../../utils/mlBacktestHelp';
import MlWalkForwardBarReadinessBanner from './MlWalkForwardBarReadinessBanner';

interface MlWalkForwardParamsControlsProps {
  params: WalkForwardParams;
  onChange: (key: WalkForwardParamKey, value: number) => void;
  onResetDefaults: () => void;
  barCount: number | null;
  barCountLoading?: boolean;
  budget: WalkForwardBudget | null;
  validationError: string | null;
  disabled?: boolean;
  viableFolds?: number | null;
  assetType?: string;
  timeframe?: string;
  labelMode?: 'binary' | 'ternary' | 'meta_label';
  maxHorizonBars?: number;
}

export default function MlWalkForwardParamsControls({
  params,
  onChange,
  onResetDefaults,
  barCount,
  barCountLoading = false,
  budget,
  validationError,
  disabled = false,
  viableFolds = null,
  assetType,
  timeframe,
  labelMode,
  maxHorizonBars,
}: MlWalkForwardParamsControlsProps) {
  const readiness = useMemo(
    () =>
      assessWalkForwardBarReadiness(barCount, params, {
        loading: barCountLoading,
        budget,
        assetType,
        timeframe,
        labelMode,
        maxHorizonBars,
      }),
    [
      barCount,
      barCountLoading,
      params,
      budget,
      assetType,
      timeframe,
      labelMode,
      maxHorizonBars,
    ],
  );

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

      <MlWalkForwardBarReadinessBanner
        readiness={readiness}
        validationError={validationError}
      />

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
                  {exceedsRange && ' — exceeds available bars'}
                </p>
              )}
            </label>
          );
        })}
      </div>

      {viableFolds != null && (
        <p className="text-xs text-slate-500">
          After Data Prep preview: {viableFolds} viable fold{viableFolds === 1 ? '' : 's'} (bars
          with valid features and labels). Structural folds above count geometry only.
        </p>
      )}
    </section>
  );
}
