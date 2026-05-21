export const PERFORMANCE_PERIOD_LABELS: Record<string, string> = {
  '1W': '1W',
  '1M': '1M',
  '3M': '3M',
  '6M': '6M',
  YTD: 'YTD',
  '1Y': '1Y',
  '2Y': '2Y',
  '5Y': '5Y',
};

const CURRENCY_LOCALE: Record<string, string> = {
  USD: 'en-US',
  EUR: 'de-DE',
  GBP: 'en-GB',
};

export function formatPerformancePct(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return '—';
  }
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

export function formatExampleAmount(currency: string, amount: number): string {
  const locale = CURRENCY_LOCALE[currency] ?? 'en-US';
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

export function formatExampleOutcome(
  currency: string,
  investment: number,
  outcome: number | null | undefined,
): string {
  if (outcome == null || Number.isNaN(outcome)) {
    return '—';
  }
  return `${formatExampleAmount(currency, investment)} → ${formatExampleAmount(currency, outcome)}`;
}

export function performanceCardClass(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return 'bg-surface-900 border-slate-700 text-slate-400';
  }
  if (value >= 0) {
    return 'bg-emerald-950/40 border-emerald-800/60 text-emerald-300';
  }
  return 'bg-red-950/40 border-red-800/60 text-red-300';
}

export function performanceSublineClass(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return 'text-slate-500';
  }
  if (value > 0) {
    return 'text-emerald-400/90';
  }
  if (value < 0) {
    return 'text-red-400/90';
  }
  return 'text-slate-400';
}
