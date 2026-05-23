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
