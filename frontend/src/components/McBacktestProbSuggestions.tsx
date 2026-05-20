import type { McBacktestSignalPoint, McBacktestZoneStats } from '../api/types';

interface McBacktestProbSuggestionsProps {
  zoneStats: McBacktestZoneStats;
  signalLog: McBacktestSignalPoint[];
  entryConfirmationBars: number;
  onApplySuggested: (buyPct: string, sellPct: string) => void;
}

function formatProbPct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function thresholdToPctString(value: number): string {
  return String(Math.round(value * 100));
}

function extractSignalProbs(signalLog: McBacktestSignalPoint[]): number[] {
  return signalLog
    .map((entry) => entry.effective_prob ?? entry.prob_positive)
    .filter((v): v is number => v != null);
}

function computeEntryZonePreview(probs: number[], buyThreshold: number): number {
  if (probs.length === 0) return 0;
  const count = probs.filter((p) => p >= buyThreshold).length;
  return Math.round((count / probs.length) * 1000) / 10;
}

export default function McBacktestProbSuggestions({
  zoneStats,
  signalLog,
  entryConfirmationBars,
  onApplySuggested,
}: McBacktestProbSuggestionsProps) {
  if (zoneStats.bars_with_prob === 0) return null;

  const hasSuggestions =
    zoneStats.suggested_buy_threshold != null &&
    zoneStats.suggested_sell_threshold != null;

  const entryPreviewPct = hasSuggestions
    ? computeEntryZonePreview(extractSignalProbs(signalLog), zoneStats.suggested_buy_threshold!)
    : null;

  const handleApply = () => {
    if (!hasSuggestions) return;
    onApplySuggested(
      thresholdToPctString(zoneStats.suggested_buy_threshold!),
      thresholdToPctString(zoneStats.suggested_sell_threshold!),
    );
  };

  return (
    <div className="mt-4 pt-4 border-t border-slate-700">
      <h4 className="text-slate-300 font-medium text-sm mb-2">Prob distribution</h4>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-400 mb-3">
        <span>Min: {formatProbPct(zoneStats.prob_min)}</span>
        <span>P25: {formatProbPct(zoneStats.prob_p25)}</span>
        <span>Median: {formatProbPct(zoneStats.prob_median)}</span>
        <span>P75: {formatProbPct(zoneStats.prob_p75)}</span>
        <span>Max: {formatProbPct(zoneStats.prob_max)}</span>
      </div>

      {hasSuggestions ? (
        <>
          <div className="flex flex-wrap gap-6 text-sm mb-2">
            <span className="text-green-400">
              Suggested entry ≥ {formatProbPct(zoneStats.suggested_buy_threshold!)}
            </span>
            <span className="text-red-400">
              Suggested exit &lt; {formatProbPct(zoneStats.suggested_sell_threshold!)}
            </span>
          </div>
          <p className="text-slate-500 text-xs mb-3">
            Based on effective prob from this run. With entry confirmation = {entryConfirmationBars},
            you need {entryConfirmationBars} consecutive bar{entryConfirmationBars === 1 ? '' : 's'} above entry.
            {entryPreviewPct != null && (
              <> At suggested entry, ~{entryPreviewPct}% of bars qualify.</>
            )}
          </p>
          <button type="button" onClick={handleApply} className="btn-secondary text-sm">
            Apply suggested thresholds
          </button>
        </>
      ) : (
        <p className="text-slate-500 text-xs">
          Need at least 10 bars with prob data to suggest thresholds.
        </p>
      )}
    </div>
  );
}
