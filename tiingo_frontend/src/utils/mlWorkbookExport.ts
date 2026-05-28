export interface MlWorkbookConfigSnapshotInput {
  initialCash: number;
  commissionBps: number;
  runMode: string;
  modelLabel?: string | null;
  appliedModelLabel?: string | null;
  dateRangeStart?: string;
  dateRangeEnd?: string;
}

export function buildMlWorkbookConfigSnapshot(
  input: MlWorkbookConfigSnapshotInput,
): Record<string, unknown> {
  return {
    initial_cash: input.initialCash,
    commission_bps: input.commissionBps,
    run_mode: input.runMode,
    model_label: input.appliedModelLabel ?? input.modelLabel ?? null,
    date_range_start: input.dateRangeStart,
    date_range_end: input.dateRangeEnd,
  };
}
