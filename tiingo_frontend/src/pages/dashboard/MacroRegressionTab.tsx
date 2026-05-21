import { useState } from 'react';
import type { DashboardSeriesRef } from '../../api/types';
import DateRangeControls from '../../components/DateRangeControls';
import ErrorAlert from '../../components/ErrorAlert';
import UnifiedSeriesSearch from '../../components/UnifiedSeriesSearch';
import Spinner from '../../components/Spinner';
import CorrelationHeatmap from '../../components/charts/CorrelationHeatmap';
import { type DateRangeValue, computePresetRange } from '../../constants/timeframes';
import { fetchSeriesObservations } from '../../utils/seriesData';
import {
  MIN_REGRESSION_SAMPLE,
  REGRESSION_METHODS,
  computeRegressionMatrix,
  type RegressionMatrixResult,
  type RegressionMethod,
  type SeriesInput,
} from '../../utils/seriesRegression';

const MAX_SERIES = 10;
const MIN_SERIES = 2;

export default function MacroRegressionTab() {
  const [dateRange, setDateRange] = useState<DateRangeValue>(() => computePresetRange('1Y', 'date'));
  const [method, setMethod] = useState<RegressionMethod>('log_return_pearson');
  const [pickerRef, setPickerRef] = useState<DashboardSeriesRef | null>(null);
  const [selected, setSelected] = useState<DashboardSeriesRef[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RegressionMatrixResult | null>(null);

  const addSeries = () => {
    if (!pickerRef || selected.length >= MAX_SERIES) return;
    const exists = selected.some((s) => s.source === pickerRef.source && s.id === pickerRef.id);
    if (exists) {
      setError(`${pickerRef.id} is already in the list.`);
      return;
    }
    setSelected((prev) => [...prev, pickerRef]);
    setPickerRef(null);
    setError(null);
    setResult(null);
  };

  const removeSeries = (id: string, source: DashboardSeriesRef['source']) => {
    setSelected((prev) => prev.filter((s) => !(s.id === id && s.source === source)));
    setResult(null);
  };

  const runAnalysis = async () => {
    if (selected.length < MIN_SERIES) {
      setError(`Select at least ${MIN_SERIES} series.`);
      return;
    }
    if (selected.length > MAX_SERIES) {
      setError(`At most ${MAX_SERIES} series allowed.`);
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const inputs: SeriesInput[] = [];
      for (const ref of selected) {
        const points = await fetchSeriesObservations(ref, dateRange);
        if (!points.length) {
          setError(`No data for ${ref.id} in the selected range.`);
          return;
        }
        inputs.push({ id: ref.id, label: ref.label, points });
      }

      const matrix = computeRegressionMatrix(inputs, method);
      if (!matrix) {
        setError(
          `Insufficient overlap (need at least ${MIN_REGRESSION_SAMPLE} aligned points). Try a wider date range.`,
        );
        return;
      }
      setResult(matrix);
    } catch {
      setError('Failed to load series data for regression. Check ingestion coverage.');
    } finally {
      setLoading(false);
    }
  };

  const atMax = selected.length >= MAX_SERIES;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-3 items-end">
        <div className="flex-1 min-w-[240px]">
          <p className="text-xs text-slate-500 mb-1">Add series ({selected.length}/{MAX_SERIES})</p>
          <UnifiedSeriesSearch
            selected={pickerRef}
            onSelect={setPickerRef}
            disabled={atMax}
            placeholder="Macro, stock, ETF, or crypto"
          />
        </div>
        <button
          type="button"
          onClick={addSeries}
          disabled={!pickerRef || atMax}
          className="px-4 py-2 rounded-lg bg-brand-500 text-white text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed hover:bg-brand-600"
        >
          Add
        </button>
      </div>

      {selected.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {selected.map((s) => (
            <span
              key={`${s.source}-${s.id}`}
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-800 border border-slate-700 text-sm text-slate-200"
            >
              <span className="font-mono text-brand-400">{s.id}</span>
              <span className="text-xs text-slate-500 uppercase">{s.source === 'macro' ? 'FRED' : s.assetType}</span>
              <button
                type="button"
                onClick={() => removeSeries(s.id, s.source)}
                className="text-slate-400 hover:text-red-400"
                aria-label={`Remove ${s.id}`}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      <DateRangeControls value={dateRange} onChange={setDateRange} mode="date" />

      <div className="flex flex-wrap gap-4 items-center">
        <label className="text-xs text-slate-500">
          Method
          <select
            value={method}
            onChange={(e) => {
              setMethod(e.target.value as RegressionMethod);
              setResult(null);
            }}
            className="ml-2 bg-surface-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100"
          >
            {REGRESSION_METHODS.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={runAnalysis}
          disabled={loading || selected.length < MIN_SERIES}
          className="px-4 py-2 rounded-lg bg-brand-500 text-white text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed hover:bg-brand-600"
        >
          Run analysis
        </button>
      </div>

      {error && <ErrorAlert message={error} />}

      {loading && (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      )}

      {!loading && result && (
        <CorrelationHeatmap
          labels={result.labels}
          values={result.values}
          method={result.method}
          sampleSize={result.sampleSize}
          overlapStart={result.overlapStart}
          overlapEnd={result.overlapEnd}
        />
      )}

      {!loading && !result && selected.length === 0 && (
        <div className="text-center py-16 text-slate-500 text-sm border border-dashed border-slate-800 rounded-lg">
          Add {MIN_SERIES}–{MAX_SERIES} series, set a date range and method, then run analysis.
        </div>
      )}

      {!loading && !result && selected.length > 0 && selected.length < MIN_SERIES && (
        <div className="text-center py-8 text-slate-500 text-sm">
          Add at least one more series ({MIN_SERIES} required).
        </div>
      )}
    </div>
  );
}
