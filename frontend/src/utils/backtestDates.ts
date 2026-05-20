/** Default lookback for daily/weekly backtests (matches prior ~3-year window). */
export const DEFAULT_BACKTEST_YEARS = 3;

/** Stored 5m ingestion window — intraday MC cannot calibrate beyond this. */
export const INTRADAY_MAX_LOOKBACK_DAYS = 90;

export type BacktestTimeframe = '5m' | '15m' | '30m' | '1h' | '4h' | '1d' | '1w';

const INTRADAY_TIMEFRAMES = new Set<string>(['5m', '15m', '30m', '1h', '4h']);

export function isIntradayTimeframe(tf: string): boolean {
  return INTRADAY_TIMEFRAMES.has(tf);
}

export const INTRADAY_CALIBRATION_DAY_OPTIONS = [7, 14, 30, 60, 90] as const;

export function defaultCalibrationDaysForTimeframe(tf: BacktestTimeframe): number {
  if (tf === '5m' || tf === '15m' || tf === '30m') return 30;
  if (tf === '1h' || tf === '4h') return 60;
  return 30;
}

export function formatLocalDate(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function defaultDatesForTimeframe(
  tf: BacktestTimeframe,
  years: number = DEFAULT_BACKTEST_YEARS,
): { start: string; end: string } {
  const today = new Date();
  const end = formatLocalDate(today);
  if (tf === '5m' || tf === '15m' || tf === '30m') {
    const start = new Date(today);
    start.setDate(start.getDate() - 30);
    return { start: formatLocalDate(start), end };
  }
  if (tf === '1h' || tf === '4h') {
    const start = new Date(today);
    start.setDate(start.getDate() - 90);
    return { start: formatLocalDate(start), end };
  }
  const start = new Date(today);
  start.setFullYear(start.getFullYear() - years);
  return { start: formatLocalDate(start), end };
}
