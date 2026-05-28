import { useCallback, useEffect, useRef, useState } from 'react';
import { mlBacktestApi } from '../../api/endpoints';
import type { MlBacktestResultsResponse, MlSavedModel } from '../../api/mlBacktestTypes';
import {
  buildResultsExportFilename,
  exportElementAsPng,
  printElement,
  TRADING_MODEL_RESULTS_PRINT_ROOT_ID,
} from '../../utils/exportTradingModelResults';
import { formatMetricPercent, formatOosAccuracy } from '../../utils/mlBacktestConfig';
import { buildInferenceRunRequest, resolveSymbol } from '../../utils/tradingModels';
import BacktestMetricsCards from '../BacktestMetricsCards';
import BacktestPerformanceLabels from '../backtesting/BacktestPerformanceLabels';
import MlEvaluationScopeBanner from '../backtesting/MlEvaluationScopeBanner';
import BacktestEquityChart from '../charts/BacktestEquityChart';
import MlConfusionMatrix from '../charts/MlConfusionMatrix';
import ErrorAlert from '../ErrorAlert';
import Spinner from '../Spinner';

interface TradingModelResultsModalProps {
  open: boolean;
  model: MlSavedModel | null;
  onClose: () => void;
}

function extractErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}

function ResultsBody({ results }: { results: MlBacktestResultsResponse }) {
  const summary = results.ml_summary;

  return (
    <div className="space-y-6">
      <MlEvaluationScopeBanner summary={summary} commissionBps={results.commission_bps} />
      {summary && (
        <section className="rounded-xl border border-slate-800 bg-surface-900 p-4 space-y-3">
          <h3 className="text-sm font-semibold text-slate-200">ML summary</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-slate-500">Feature mode</p>
              <p className="text-slate-200">{summary.feature_mode}</p>
            </div>
            <div>
              <p className="text-slate-500">Run mode</p>
              <p className="text-slate-200">{summary.run_mode ?? 'inference'}</p>
            </div>
            <div>
              <p className="text-slate-500">Mean OOS accuracy</p>
              <p className="text-slate-200">{formatOosAccuracy(summary.mean_oos_accuracy)}</p>
            </div>
            <div>
              <p className="text-slate-500">Precision / Recall / F1</p>
              <p className="text-slate-200">
                {formatMetricPercent(summary.precision)} /{' '}
                {formatMetricPercent(summary.recall)} / {formatMetricPercent(summary.f1)}
              </p>
            </div>
          </div>
          {(summary.confusion_matrix?.length ?? 0) > 0 && (
            <MlConfusionMatrix matrix={summary.confusion_matrix ?? []} />
          )}
        </section>
      )}

      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-slate-200">Portfolio results</h3>
        <BacktestMetricsCards metrics={results.metrics} />
        <BacktestPerformanceLabels metrics={results.metrics} />
        <BacktestEquityChart
          strategy={results.equity_curve ?? []}
          benchmark={results.benchmark_equity_curve ?? []}
        />
      </section>
    </div>
  );
}

export default function TradingModelResultsModal({
  open,
  model,
  onClose,
}: TradingModelResultsModalProps) {
  const exportRootRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [results, setResults] = useState<MlBacktestResultsResponse | null>(null);

  const runInference = useCallback(async (savedModel: MlSavedModel) => {
    setLoading(true);
    setError(null);
    setExportError(null);
    setResults(null);

    try {
      const request = buildInferenceRunRequest(savedModel);
      const run = await mlBacktestApi.run(request);
      const full = await mlBacktestApi.getResults(run.id);
      setResults(full);
    } catch (err: unknown) {
      setError(extractErrorMessage(err, 'Inference backtest failed.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!open || !model) {
      setResults(null);
      setError(null);
      setExportError(null);
      return;
    }
    void runInference(model);
  }, [open, model, runInference]);

  const handleExportPng = async () => {
    if (!exportRootRef.current || !model) return;
    setExporting(true);
    setExportError(null);
    try {
      const filename = buildResultsExportFilename(
        resolveSymbol(model),
        model.name,
        'png',
      );
      await exportElementAsPng(exportRootRef.current, filename);
    } catch (err: unknown) {
      setExportError(extractErrorMessage(err, 'PNG export failed.'));
    } finally {
      setExporting(false);
    }
  };

  const handlePrint = () => {
    if (!exportRootRef.current) return;
    setExportError(null);
    try {
      printElement(exportRootRef.current);
    } catch (err: unknown) {
      setExportError(extractErrorMessage(err, 'Print failed.'));
    }
  };

  const exportDisabled = loading || exporting || !results;

  if (!open || !model) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4 py-8"
      role="dialog"
      aria-modal="true"
      aria-labelledby="trading-model-results-title"
    >
      <div className="flex max-h-[90vh] w-full max-w-5xl flex-col rounded-xl border border-slate-700 bg-surface-900 shadow-xl">
        <div className="flex items-start justify-between gap-4 border-b border-slate-800 p-4">
          <div>
            <h2 id="trading-model-results-title" className="text-lg font-medium text-white">
              Inference results — {model.name}
            </h2>
            <p className="mt-1 text-sm text-slate-400">
              {resolveSymbol(model)} · {model.feature_mode}
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <button
              type="button"
              disabled={exportDisabled}
              onClick={() => void handleExportPng()}
              className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-300 hover:bg-surface-800 disabled:opacity-50"
            >
              {exporting ? 'Exporting…' : 'Export PNG'}
            </button>
            <button
              type="button"
              disabled={exportDisabled}
              onClick={handlePrint}
              className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-300 hover:bg-surface-800 disabled:opacity-50"
            >
              Print / Save PDF
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-300 hover:bg-surface-800"
            >
              Close
            </button>
          </div>
        </div>

        <div className="overflow-y-auto p-4">
          {loading && (
            <div className="flex justify-center py-12">
              <Spinner />
            </div>
          )}
          {error && <ErrorAlert message={error} />}
          {exportError && !error && <ErrorAlert message={exportError} />}
          {!loading && !error && results && (
            <div
              ref={exportRootRef}
              id={TRADING_MODEL_RESULTS_PRINT_ROOT_ID}
              className="space-y-4 bg-surface-900 p-2"
            >
              <div className="border-b border-slate-800 pb-3">
                <h3 className="text-base font-semibold text-slate-100">
                  Inference results — {model.name}
                </h3>
                <p className="mt-1 text-sm text-slate-400">
                  {resolveSymbol(model)} · {model.feature_mode}
                </p>
              </div>
              <ResultsBody results={results} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
