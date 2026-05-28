import type { DateRangeValue } from '../../constants/timeframes';
import { dateRangeModeForTimeframe } from '../../constants/timeframes';
import type { WalkForwardBudget } from '../../utils/mlUniverseBudget';
import {
  formatMlDateRangeLabel,
  isUsingMaxPreset,
} from '../../utils/mlUniverseBudget';
import type { WalkForwardParamKey, WalkForwardParams } from '../../utils/mlBacktestConfig';
import DateRangeControls from '../DateRangeControls';
import MlUniverseChart from './MlUniverseChart';
import MlWalkForwardParamsControls from './MlWalkForwardParamsControls';

interface MlUniversePeriodSectionProps {
  symbol: string;
  decisionTimeframe: string;
  dateRange: DateRangeValue;
  onDateRangeChange: (value: DateRangeValue) => void;
  walkForwardParams: WalkForwardParams;
  onWalkForwardParamChange: (key: WalkForwardParamKey, value: number) => void;
  onResetWalkForwardDefaults: () => void;
  barCount: number | null;
  rangeStart: string | null;
  rangeEnd: string | null;
  barCountLoading: boolean;
  barCountError: string | null;
  budget: WalkForwardBudget | null;
  walkForwardValidationError: string | null;
  viableFolds: number | null;
  disabled?: boolean;
}

function formatEffectiveRangeLine(
  barCount: number | null,
  rangeStart: string | null,
  rangeEnd: string | null,
  dateRange: DateRangeValue,
): string | null {
  if (barCount == null) {
    return null;
  }
  const dates = formatMlDateRangeLabel(dateRange, rangeStart, rangeEnd);
  return `${barCount.toLocaleString()} bars · ${dates}`;
}

export default function MlUniversePeriodSection({
  symbol,
  decisionTimeframe,
  dateRange,
  onDateRangeChange,
  walkForwardParams,
  onWalkForwardParamChange,
  onResetWalkForwardDefaults,
  barCount,
  rangeStart,
  rangeEnd,
  barCountLoading,
  barCountError,
  budget,
  walkForwardValidationError,
  viableFolds,
  disabled = false,
}: MlUniversePeriodSectionProps) {
  const effectiveRangeLine = formatEffectiveRangeLine(
    barCount,
    rangeStart,
    rangeEnd,
    dateRange,
  );

  return (
    <section className="rounded-xl border border-slate-800 bg-surface-900 p-4 space-y-4">
      <div className="space-y-2">
        <h3 className="text-sm font-medium text-slate-300">Simulation period</h3>
        <p className="text-xs text-slate-400 leading-relaxed">
          Start and end dates define the full bar history used for feature engineering, labeling,
          walk-forward training, and out-of-sample simulation. The first 50 bars are feature warmup;
          simulation trading begins at bar {walkForwardParams.train_bars} (first out-of-sample window).
          The last {walkForwardParams.label_horizon} bars cannot be labeled because they lack forward
          returns.
        </p>
      </div>

      <DateRangeControls
        value={dateRange}
        onChange={onDateRangeChange}
        mode={dateRangeModeForTimeframe(decisionTimeframe)}
        autoApply
      />

      {barCountLoading && (
        <p className="text-xs text-slate-500">Loading bars for selected period…</p>
      )}
      {barCountError && <p className="text-xs text-red-400">{barCountError}</p>}
      {effectiveRangeLine && !barCountLoading && (
        <p className="text-xs text-slate-400">{effectiveRangeLine}</p>
      )}
      {isUsingMaxPreset(dateRange) && barCount != null && (
        <p className="text-xs text-slate-500">
          Using full ingested history (~{barCount.toLocaleString()} bars).
        </p>
      )}

      <div className="space-y-2">
        <h4 className="text-xs font-medium text-slate-400">Price history preview</h4>
        <MlUniverseChart
          symbol={symbol}
          decisionTimeframe={decisionTimeframe}
          dateRange={dateRange}
        />
      </div>

      {budget && (
        <div className="rounded-lg border border-slate-800 bg-surface-950/60 p-3 space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Bar budget
          </h4>
          <dl className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <div>
              <dt className="text-slate-500 text-xs">Minimum required</dt>
              <dd className="text-slate-100">{budget.minimumRequired}</dd>
            </div>
            <div>
              <dt className="text-slate-500 text-xs">Walk-forward budget</dt>
              <dd className="text-slate-100">{budget.walkForwardBudget}</dd>
            </div>
            <div>
              <dt className="text-slate-500 text-xs">Remaining headroom</dt>
              <dd className={budget.remainingBars < 0 ? 'text-amber-300' : 'text-slate-100'}>
                {budget.remainingBars}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500 text-xs">Structural folds</dt>
              <dd className="text-slate-100">~{budget.structuralFolds}</dd>
            </div>
          </dl>
          <p className="text-xs text-slate-500">
            Warmup: {budget.warmupBars} bars · label tail: {budget.labelTail} bars · simulation
            starts at bar {budget.simulationStartBarIndex}.
          </p>
        </div>
      )}

      <MlWalkForwardParamsControls
        params={walkForwardParams}
        onChange={onWalkForwardParamChange}
        onResetDefaults={onResetWalkForwardDefaults}
        barCount={barCount}
        budget={budget}
        validationError={walkForwardValidationError}
        disabled={disabled}
        viableFolds={viableFolds}
      />
    </section>
  );
}
