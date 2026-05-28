export function topFeatureImportance(
  items: { name: string; value: number }[] | undefined,
  limit = 15,
): { name: string; value: number }[] {
  if (!items?.length) return [];
  return [...items]
    .sort((a, b) => b.value - a.value)
    .slice(0, limit);
}

export function buildOosAccuracyChartData(
  accuracies: number[] | undefined,
): { window: number; accuracy: number; accuracyPct: number }[] {
  if (!accuracies?.length) return [];
  return accuracies.map((accuracy, index) => ({
    window: index + 1,
    accuracy,
    accuracyPct: accuracy * 100,
  }));
}

export function confusionMatrixLabels(): { rows: string[]; cols: string[] } {
  return {
    rows: ['Actual down (0)', 'Actual up (1)'],
    cols: ['Pred down (0)', 'Pred up (1)'],
  };
}

export function confusionMatrixMaxValue(matrix: number[][] | undefined): number {
  if (!matrix?.length) return 1;
  return Math.max(1, ...matrix.flat());
}

export function formatConfusionCell(value: number): string {
  return String(value);
}

function recordDateKey(record: { date?: string; time?: string }): string {
  if (record.time) {
    return record.time.slice(0, 10);
  }
  return (record.date ?? '').slice(0, 10);
}

export function filterRecordsFromSimulationStart<T extends { date?: string; time?: string }>(
  records: T[],
  simulationStartDate: string | null | undefined,
): T[] {
  if (!simulationStartDate || records.length === 0) {
    return records;
  }
  const startKey = simulationStartDate.slice(0, 10);
  return records.filter((record) => recordDateKey(record) >= startKey);
}

export function resolveEvaluationStartDate(
  mlSummary:
    | {
        evaluation_start_date?: string | null;
        simulation_start_date?: string | null;
      }
    | null
    | undefined,
): string | null {
  if (!mlSummary) {
    return null;
  }
  return mlSummary.evaluation_start_date ?? mlSummary.simulation_start_date ?? null;
}

export function formatSimulationPeriodLabel(
  simulationStartDate: string | null | undefined,
  endDate: string | null | undefined,
): string | null {
  if (!simulationStartDate) {
    return null;
  }
  const start = simulationStartDate.slice(0, 10);
  const end = endDate?.slice(0, 10) ?? '—';
  return `${start} – ${end}`;
}

export type MlEvaluationScope = 'holdout' | 'in_sample' | 'walk_forward_oos';

export interface EvaluationScopeNotice {
  tone: 'info' | 'warning';
  title: string;
  message: string;
}

export function buildEvaluationScopeNotice(
  summary:
    | {
        evaluation_scope?: string | null;
        holdout_bars?: number | null;
        holdout_start_date?: string | null;
        holdout_end_date?: string | null;
      }
    | null
    | undefined,
): EvaluationScopeNotice | null {
  const scope = summary?.evaluation_scope;
  if (!scope) {
    return null;
  }

  if (scope === 'in_sample') {
    return {
      tone: 'warning',
      title: 'In-sample diagnostics',
      message:
        'Metrics and portfolio results cover the same period used to train this model. ' +
        'They are not indicative of live performance.',
    };
  }

  if (scope === 'holdout') {
    const bars = summary?.holdout_bars;
    const period = formatSimulationPeriodLabel(
      summary?.holdout_start_date,
      summary?.holdout_end_date,
    );
    const barsLabel = typeof bars === 'number' ? `${bars} bars` : 'held-out bars';
    const periodLabel = period ? ` (${period})` : '';
    return {
      tone: 'info',
      title: 'Holdout evaluation',
      message:
        `Results use the last ${barsLabel}${periodLabel} reserved during training. ` +
        'The model did not see these bars while fitting.',
    };
  }

  if (scope === 'walk_forward_oos') {
    return {
      tone: 'info',
      title: 'Walk-forward out-of-sample',
      message: 'Predictions and trades use only out-of-sample folds; in-sample bars stay flat.',
    };
  }

  return null;
}

export function collectMlDataWarnings(
  summary:
    | {
        macro_warnings?: string[] | null;
        fundamental_warnings?: string[] | null;
      }
    | null
    | undefined,
): string[] {
  if (!summary) {
    return [];
  }
  return [
    ...(summary.macro_warnings ?? []),
    ...(summary.fundamental_warnings ?? []),
  ].filter(Boolean);
}
