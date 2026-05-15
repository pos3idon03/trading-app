/** Default lookback for daily/weekly backtests (matches prior ~3-year window). */
export const DEFAULT_BACKTEST_YEARS = 3;

export type BacktestTimeframe = '5m' | '15m' | '30m' | '1h' | '4h' | '1d' | '1w';

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
