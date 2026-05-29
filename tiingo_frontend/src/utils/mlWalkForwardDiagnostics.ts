import type { MlParams, MlWalkForwardReadiness } from '../api/mlBacktestTypes';
import type { DateRangeValue } from '../constants/timeframes';

/** Inputs that affect feature assembly and walk-forward bar windows in data preview. */
export function dataPrepPreviewFingerprint(
  params: MlParams,
  dateRange?: DateRangeValue,
): string {
  return JSON.stringify({
    feature_mode: params.feature_mode,
    include_news_sentiment: params.include_news_sentiment ?? false,
    context_timeframes: params.context_timeframes ?? [],
    strategy_feature_ids: params.strategy_feature_ids ?? [],
    macro_series_ids: params.macro_series_ids ?? [],
    fundamental_metrics: params.fundamental_metrics ?? [],
    train_bars: params.train_bars,
    test_bars: params.test_bars,
    step_bars: params.step_bars,
    date_start: dateRange?.start ?? null,
    date_end: dateRange?.end ?? null,
    date_preset: dateRange?.preset ?? 'MAX',
  });
}

/** @deprecated Use {@link dataPrepPreviewFingerprint} for preview staleness checks. */
export function previewConfigFingerprint(
  params: MlParams,
  dateRange?: DateRangeValue,
): string {
  return dataPrepPreviewFingerprint(params, dateRange);
}

export function isReadinessReady(readiness: MlWalkForwardReadiness | undefined): boolean {
  return (readiness?.viable_folds ?? 0) > 0;
}

export function formatZeroOosGuidance(
  readiness: MlWalkForwardReadiness | undefined,
  classDistribution: Record<string, number> | undefined,
): string[] {
  const messages: string[] = [];
  if (!readiness) {
    messages.push(
      'No out-of-sample windows completed. Run data preview on Data Prep to diagnose walk-forward readiness.',
    );
    return messages;
  }

  if (readiness.valid_feature_rows === 0) {
    messages.push(
      'No valid feature rows — optional context/strategy features or macro coverage may have nullified all rows. Uncheck optional features on Data Prep or fix data coverage.',
    );
  } else if (readiness.viable_folds === 0) {
    messages.push(
      'Walk-forward cannot train on any fold — extend the date range, set train bars well above the 50-bar warmup, or include earlier/choppier market history.',
    );
  }

  if (classDistribution) {
    const total = Object.values(classDistribution).reduce((sum, count) => sum + count, 0);
    if (total > 0) {
      const majority = Math.max(...Object.values(classDistribution)) / total;
      if (majority > 0.85) {
        messages.push(
          'Label distribution is heavily one-sided — include a longer or more varied date range so train windows contain both up and down labels.',
        );
      }
    }
  }

  if (messages.length === 0) {
    messages.push(
      'No out-of-sample windows completed — check macro coverage, date range, and walk-forward bar settings.',
    );
  }

  return messages;
}

export function readinessStatusTone(
  readiness: MlWalkForwardReadiness | undefined,
): 'ready' | 'warning' | 'unknown' {
  if (!readiness || readiness.total_bars === 0) {
    return 'unknown';
  }
  return readiness.viable_folds > 0 ? 'ready' : 'warning';
}
