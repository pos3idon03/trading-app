import { STRATEGIES } from '../constants/strategies';
import { fmt, fmtPct } from '../utils/formatting';
import type { ComboMatrixMetric } from '../api/types';

interface StrategyHeatmapProps {
  strategies: string[];
  values: (number | null)[][];
  metric: ComboMatrixMetric;
  combinationMode: string;
}

function strategyLabel(name: string): string {
  return STRATEGIES.find((s) => s.value === name)?.label ?? name;
}

function formatCellValue(value: number | null, metric: ComboMatrixMetric): string {
  if (value === null) return '—';
  if (metric === 'total_return') return fmtPct(value);
  return fmt(value, 2);
}

function collectNumericValues(values: (number | null)[][]): number[] {
  const nums: number[] = [];
  for (const row of values) {
    for (const v of row) {
      if (v !== null && Number.isFinite(v)) nums.push(v);
    }
  }
  return nums;
}

function cellColor(value: number | null, min: number, max: number): string {
  if (value === null || !Number.isFinite(value)) {
    return 'rgb(30, 41, 59)';
  }
  if (min === max) {
    return 'rgb(34, 197, 94)';
  }
  const t = (value - min) / (max - min);
  const r = Math.round(239 - t * 167);
  const g = Math.round(68 + t * 126);
  const b = Math.round(68 + t * 26);
  return `rgb(${r}, ${g}, ${b})`;
}

function cellTooltip(
  row: string,
  col: string,
  value: number | null,
  metric: ComboMatrixMetric,
): string {
  const labelA = strategyLabel(row);
  const labelB = strategyLabel(col);
  const formatted = formatCellValue(value, metric);
  if (row === col) {
    return `${labelA} (solo): ${formatted}`;
  }
  return `${labelA} + ${labelB}: ${formatted}`;
}

export default function StrategyHeatmap({
  strategies,
  values,
  metric,
  combinationMode,
}: StrategyHeatmapProps) {
  const nums = collectNumericValues(values);
  const min = nums.length > 0 ? Math.min(...nums) : 0;
  const max = nums.length > 0 ? Math.max(...nums) : 0;
  const n = strategies.length;
  const gridCols = `minmax(7rem, 1.2fr) repeat(${n}, minmax(3.5rem, 1fr))`;

  return (
    <section className="card overflow-x-auto">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-slate-200">Strategy combination heatmap</h3>
        <span className="text-xs text-slate-500">
          Mode: {combinationMode} &bull; Diagonal = solo strategy
        </span>
      </div>
      <div
        className="inline-grid gap-px min-w-full"
        style={{ gridTemplateColumns: gridCols }}
        role="grid"
        aria-label="Strategy combination heatmap"
      >
        <div className="bg-surface-900 p-2" />
        {strategies.map((col) => (
          <div
            key={`col-${col}`}
            className="bg-surface-900 p-1 text-[10px] text-slate-400 text-center truncate"
            title={strategyLabel(col)}
          >
            {strategyLabel(col).split(' ')[0]}
          </div>
        ))}
        {strategies.map((row, i) => (
          <div key={`row-group-${row}`} className="contents">
            <div
              className="bg-surface-900 p-1 text-[10px] text-slate-400 truncate flex items-center"
              title={strategyLabel(row)}
            >
              {strategyLabel(row).split(' ')[0]}
            </div>
            {strategies.map((col, j) => {
              const value = values[i]?.[j] ?? null;
              const isDiagonal = i === j;
              return (
                <div
                  key={`${row}-${col}`}
                  role="gridcell"
                  className={`p-1 text-center text-[10px] font-mono text-slate-100 ${
                    isDiagonal ? 'ring-1 ring-inset ring-slate-500' : ''
                  }`}
                  style={{ backgroundColor: cellColor(value, min, max) }}
                  title={cellTooltip(row, col, value, metric)}
                >
                  {formatCellValue(value, metric)}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </section>
  );
}
