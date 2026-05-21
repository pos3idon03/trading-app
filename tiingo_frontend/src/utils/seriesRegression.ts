import type { TimeSeriesPoint } from './seriesData';

export type RegressionMethod = 'log_return_pearson' | 'level_pearson' | 'ols_r2';

export const REGRESSION_METHODS: { value: RegressionMethod; label: string }[] = [
  { value: 'log_return_pearson', label: 'Pearson r (log returns)' },
  { value: 'level_pearson', label: 'Pearson r (levels)' },
  { value: 'ols_r2', label: 'OLS R² (symmetric max)' },
];

export const MIN_REGRESSION_SAMPLE = 30;

export interface SeriesInput {
  id: string;
  label: string;
  points: TimeSeriesPoint[];
}

export interface RegressionMatrixResult {
  labels: string[];
  values: (number | null)[][];
  method: RegressionMethod;
  sampleSize: number;
  overlapStart: string | null;
  overlapEnd: string | null;
}

function sortDates(dates: string[]): string[] {
  return [...dates].sort((a, b) => a.localeCompare(b));
}

function forwardFillSeries(
  dates: string[],
  points: TimeSeriesPoint[],
): Map<string, number | null> {
  const byDate = new Map(points.map((p) => [p.date, p.value]));
  const filled = new Map<string, number | null>();
  let last: number | null = null;

  for (const date of dates) {
    const raw = byDate.get(date);
    if (raw != null && Number.isFinite(raw)) {
      last = raw;
    }
    filled.set(date, last);
  }
  return filled;
}

export function alignSeriesDaily(seriesList: SeriesInput[]): {
  dates: string[];
  aligned: number[][];
} {
  const dateSet = new Set<string>();
  for (const s of seriesList) {
    for (const p of s.points) {
      if (p.value != null && Number.isFinite(p.value)) {
        dateSet.add(p.date);
      }
    }
  }

  const dates = sortDates([...dateSet]);
  const filledMaps = seriesList.map((s) => forwardFillSeries(dates, s.points));

  const aligned: number[][] = [];
  const validDates: string[] = [];

  for (const date of dates) {
    const row: number[] = [];
    let complete = true;
    for (const m of filledMaps) {
      const v = m.get(date);
      if (v == null || !Number.isFinite(v)) {
        complete = false;
        break;
      }
      row.push(v);
    }
    if (complete) {
      validDates.push(date);
      aligned.push(row);
    }
  }

  return { dates: validDates, aligned };
}

function toLogReturns(
  dates: string[],
  aligned: number[][],
): { dates: string[]; data: number[][] } {
  if (aligned.length < 2) return { dates: [], data: [] };
  const out: number[][] = [];
  const outDates: string[] = [];
  for (let i = 1; i < aligned.length; i += 1) {
    const row: number[] = [];
    let ok = true;
    for (let j = 0; j < aligned[i].length; j += 1) {
      const prev = aligned[i - 1][j];
      const curr = aligned[i][j];
      if (prev <= 0 || curr <= 0) {
        ok = false;
        break;
      }
      row.push(Math.log(curr / prev));
    }
    if (ok) {
      out.push(row);
      outDates.push(dates[i]);
    }
  }
  return { dates: outDates, data: out };
}

function pearson(x: number[], y: number[]): number | null {
  const n = x.length;
  if (n < 2) return null;

  const meanX = x.reduce((a, b) => a + b, 0) / n;
  const meanY = y.reduce((a, b) => a + b, 0) / n;

  let num = 0;
  let denX = 0;
  let denY = 0;
  for (let i = 0; i < n; i += 1) {
    const dx = x[i] - meanX;
    const dy = y[i] - meanY;
    num += dx * dy;
    denX += dx * dx;
    denY += dy * dy;
  }
  const den = Math.sqrt(denX * denY);
  if (den === 0) return null;
  return num / den;
}

function olsR2(x: number[], y: number[]): number | null {
  const n = x.length;
  if (n < 2) return null;

  const meanX = x.reduce((a, b) => a + b, 0) / n;
  const meanY = y.reduce((a, b) => a + b, 0) / n;

  let ssTot = 0;
  let ssRes = 0;
  let sxy = 0;
  let sxx = 0;

  for (let i = 0; i < n; i += 1) {
    const dx = x[i] - meanX;
    const dy = y[i] - meanY;
    sxy += dx * dy;
    sxx += dx * dx;
    ssTot += dy * dy;
  }

  if (sxx === 0 || ssTot === 0) return null;
  const slope = sxy / sxx;
  const intercept = meanY - slope * meanX;

  for (let i = 0; i < n; i += 1) {
    const pred = intercept + slope * x[i];
    ssRes += (y[i] - pred) ** 2;
  }

  const r2 = 1 - ssRes / ssTot;
  return Number.isFinite(r2) ? Math.max(0, Math.min(1, r2)) : null;
}

function buildPearsonMatrix(data: number[][], n: number): (number | null)[][] {
  const matrix: (number | null)[][] = Array.from({ length: n }, () =>
    Array(n).fill(null),
  );

  for (let i = 0; i < n; i += 1) {
    matrix[i][i] = 1;
    const colI = data.map((row) => row[i]);
    for (let j = i + 1; j < n; j += 1) {
      const colJ = data.map((row) => row[j]);
      const r = pearson(colI, colJ);
      matrix[i][j] = r;
      matrix[j][i] = r;
    }
  }
  return matrix;
}

function buildOlsMatrix(data: number[][], n: number): (number | null)[][] {
  const matrix: (number | null)[][] = Array.from({ length: n }, () =>
    Array(n).fill(null),
  );

  for (let i = 0; i < n; i += 1) {
    matrix[i][i] = 1;
    const colI = data.map((row) => row[i]);
    for (let j = i + 1; j < n; j += 1) {
      const colJ = data.map((row) => row[j]);
      const r2ij = olsR2(colI, colJ);
      const r2ji = olsR2(colJ, colI);
      const sym =
        r2ij == null && r2ji == null
          ? null
          : Math.max(r2ij ?? -Infinity, r2ji ?? -Infinity);
      matrix[i][j] = sym;
      matrix[j][i] = sym;
    }
  }
  return matrix;
}

export function computeRegressionMatrix(
  seriesList: SeriesInput[],
  method: RegressionMethod,
): RegressionMatrixResult | null {
  const labels = seriesList.map((s) => s.id);
  const { dates, aligned } = alignSeriesDaily(seriesList);

  let data = aligned;
  let effectiveDates = dates;
  if (method === 'log_return_pearson') {
    const transformed = toLogReturns(dates, aligned);
    data = transformed.data;
    effectiveDates = transformed.dates;
  }

  const sampleSize = data.length;
  if (sampleSize < MIN_REGRESSION_SAMPLE) {
    return null;
  }

  const n = seriesList.length;
  const values =
    method === 'ols_r2'
      ? buildOlsMatrix(data, n)
      : buildPearsonMatrix(data, n);

  return {
    labels,
    values,
    method,
    sampleSize,
    overlapStart: effectiveDates.length > 0 ? effectiveDates[0] : null,
    overlapEnd:
      effectiveDates.length > 0 ? effectiveDates[effectiveDates.length - 1] : null,
  };
}

export function formatMatrixCell(value: number | null, method: RegressionMethod): string {
  if (value == null || !Number.isFinite(value)) return '—';
  if (method === 'ols_r2') return `R² = ${value.toFixed(3)}`;
  return `r = ${value.toFixed(3)}`;
}

export function methodDescription(method: RegressionMethod): string {
  switch (method) {
    case 'log_return_pearson':
      return 'Daily log returns after forward-fill alignment.';
    case 'level_pearson':
      return 'Aligned levels after forward-fill on a common daily calendar.';
    case 'ols_r2':
      return 'Symmetric max of pairwise OLS R² (Y ~ X and X ~ Y).';
    default:
      return '';
  }
}
