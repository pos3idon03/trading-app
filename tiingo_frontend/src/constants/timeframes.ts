export const OHLCV_TIMEFRAMES = [
  { value: '1m', label: '1 min' },
  { value: '5m', label: '5 min' },
  { value: '15m', label: '15 min' },
  { value: '30m', label: '30 min' },
  { value: '1h', label: '1 hour' },
  { value: '4h', label: '4 hours' },
  { value: '1d', label: '1 day' },
  { value: '1w', label: '1 week' },
  { value: '1mo', label: '1 month' },
] as const;

export type OhlcvTimeframe = (typeof OHLCV_TIMEFRAMES)[number]['value'];

export const INTRADAY_TIMEFRAMES = new Set<string>(['1m', '5m', '15m', '30m', '1h', '4h']);

export const DAILY_PLUS_TIMEFRAMES = new Set<string>(['1d', '1w', '1mo']);

export const INTRADAY_BAR_LIMIT = 3000;
export const DAILY_PLUS_BAR_LIMIT = 10000;

export type DateRangePreset = '1D' | '5D' | '1M' | '3M' | '6M' | 'YTD' | '1Y' | 'MAX';

export interface DateRangeValue {
  preset: DateRangePreset;
  start?: string;
  end?: string;
}

export function computePresetRange(preset: DateRangePreset, mode: 'datetime' | 'date' = 'datetime'): DateRangeValue {
  if (preset === 'MAX') {
    return { preset: 'MAX' };
  }

  const now = new Date();
  const end = mode === 'date' ? formatDate(now) : now.toISOString();
  const startDate = new Date(now);

  switch (preset) {
    case '1D':
      startDate.setDate(startDate.getDate() - 1);
      break;
    case '5D':
      startDate.setDate(startDate.getDate() - 5);
      break;
    case '1M':
      startDate.setMonth(startDate.getMonth() - 1);
      break;
    case '3M':
      startDate.setMonth(startDate.getMonth() - 3);
      break;
    case '6M':
      startDate.setMonth(startDate.getMonth() - 6);
      break;
    case 'YTD':
      startDate.setMonth(0);
      startDate.setDate(1);
      break;
    case '1Y':
      startDate.setFullYear(startDate.getFullYear() - 1);
      break;
    default:
      break;
  }

  const start = mode === 'date' ? formatDate(startDate) : startDate.toISOString();
  return { preset, start, end };
}

function formatDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export function toApiRange(value: DateRangeValue): { start?: string; end?: string } {
  if (value.preset === 'MAX' && !value.start && !value.end) {
    return {};
  }
  const range: { start?: string; end?: string } = {};
  if (value.start) range.start = value.start;
  if (value.end) range.end = value.end;
  return range;
}

function isDateOnly(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(value);
}

export function toDailyApiRange(value: DateRangeValue): { start?: string; end?: string } {
  const base = toApiRange(value);
  const range: { start?: string; end?: string } = {};
  if (base.start) {
    range.start = isDateOnly(base.start) ? `${base.start}T00:00:00Z` : base.start;
  }
  if (base.end) {
    range.end = isDateOnly(base.end) ? `${base.end}T23:59:59Z` : base.end;
  }
  return range;
}

export function isDailyPlusTimeframe(timeframe: string): boolean {
  return DAILY_PLUS_TIMEFRAMES.has(timeframe);
}

export function dateRangeModeForTimeframe(timeframe: string): 'datetime' | 'date' {
  return isDailyPlusTimeframe(timeframe) ? 'date' : 'datetime';
}

export interface OhlcvApiQuery {
  timeframe: string;
  start?: string;
  end?: string;
  limit: number;
}

export function buildOhlcvQuery(timeframe: string, dateRange: DateRangeValue): OhlcvApiQuery {
  const limit = isDailyPlusTimeframe(timeframe) ? DAILY_PLUS_BAR_LIMIT : INTRADAY_BAR_LIMIT;
  if (dateRange.preset === 'MAX' && !dateRange.start && !dateRange.end) {
    return { timeframe, limit };
  }
  const rangeFn = isDailyPlusTimeframe(timeframe) ? toDailyApiRange : toApiRange;
  return { timeframe, limit, ...rangeFn(dateRange) };
}

export function defaultDateRangeForTimeframe(_timeframe: string): DateRangeValue {
  return { preset: 'MAX' };
}

export const DATE_RANGE_PRESETS: DateRangePreset[] = ['1D', '5D', '1M', '3M', '6M', 'YTD', '1Y', 'MAX'];

export function defaultPortfolioDateRange(): DateRangeValue {
  return computePresetRange('YTD', 'date');
}

export function toPortfolioApiRange(value: DateRangeValue): { start?: string; end?: string } {
  if (value.preset === 'MAX' && !value.start && !value.end) {
    return { start: '2000-01-01T00:00:00Z' };
  }
  return toDailyApiRange(value);
}
