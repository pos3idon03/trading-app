import {
  formatMatrixCell,
  methodDescription,
  type RegressionMethod,
} from '../../utils/seriesRegression';

interface CorrelationHeatmapProps {
  labels: string[];
  values: (number | null)[][];
  method: RegressionMethod;
  sampleSize: number;
  overlapStart: string | null;
  overlapEnd: string | null;
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

function cellColor(value: number | null, min: number, max: number, method: RegressionMethod): string {
  if (value === null || !Number.isFinite(value)) {
    return 'rgb(30, 41, 59)';
  }
  const normalized =
    method === 'ols_r2' ? value : (value + 1) / 2;
  const normMin = method === 'ols_r2' ? min : (min + 1) / 2;
  const normMax = method === 'ols_r2' ? max : (max + 1) / 2;
  if (normMin === normMax) {
    return 'rgb(34, 197, 94)';
  }
  const t = (normalized - normMin) / (normMax - normMin);
  const r = Math.round(239 - t * 167);
  const g = Math.round(68 + t * 126);
  const b = Math.round(68 + t * 26);
  return `rgb(${r}, ${g}, ${b})`;
}

export default function CorrelationHeatmap({
  labels,
  values,
  method,
  sampleSize,
  overlapStart,
  overlapEnd,
}: CorrelationHeatmapProps) {
  const nums = collectNumericValues(values);
  const min = nums.length > 0 ? Math.min(...nums) : 0;
  const max = nums.length > 0 ? Math.max(...nums) : 0;
  const n = labels.length;
  const gridCols = `minmax(5rem, 1fr) repeat(${n}, minmax(3.5rem, 1fr))`;

  const overlapLabel =
    overlapStart && overlapEnd
      ? `${overlapStart.slice(0, 7)} → ${overlapEnd.slice(0, 7)}`
      : '—';

  return (
    <section className="w-full border border-slate-800 rounded-lg bg-surface-900 p-4 overflow-x-auto">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <h3 className="text-sm font-semibold text-slate-200">Series correlation matrix</h3>
        <span className="text-xs text-slate-500">
          n={sampleSize} · overlap {overlapLabel}
        </span>
      </div>
      <p className="text-xs text-slate-500 mb-3">{methodDescription(method)}</p>
      <div
        className="inline-grid gap-px min-w-full"
        style={{ gridTemplateColumns: gridCols }}
        role="grid"
        aria-label="Series correlation heatmap"
      >
        <div className="bg-surface-900 p-2" />
        {labels.map((col) => (
          <div
            key={`col-${col}`}
            className="bg-surface-900 p-1 text-[10px] text-slate-400 text-center truncate font-mono"
            title={col}
          >
            {col}
          </div>
        ))}
        {labels.map((row, i) => (
          <div key={`row-group-${row}`} className="contents">
            <div
              className="bg-surface-900 p-1 text-[10px] text-slate-400 truncate flex items-center font-mono"
              title={row}
            >
              {row}
            </div>
            {labels.map((col, j) => {
              const value = values[i]?.[j] ?? null;
              const isDiagonal = i === j;
              const formatted = formatMatrixCell(value, method);
              return (
                <div
                  key={`${row}-${col}`}
                  role="gridcell"
                  className={`p-1 text-center text-[10px] font-mono text-slate-100 ${
                    isDiagonal ? 'ring-1 ring-inset ring-slate-500' : ''
                  }`}
                  style={{ backgroundColor: cellColor(value, min, max, method) }}
                  title={`${row} vs ${col}: ${formatted}`}
                >
                  {value == null ? '—' : value.toFixed(2)}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </section>
  );
}
