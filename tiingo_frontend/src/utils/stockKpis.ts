import type { StockKpiItem } from '../api/types';

export function formatKpiValue(item: StockKpiItem): string {
  if (item.value == null || Number.isNaN(item.value)) {
    return '—';
  }
  switch (item.format) {
    case 'percent':
      return `${item.value.toFixed(2)}%`;
    case 'perShare':
      return `$${item.value.toFixed(2)}`;
    case 'currency':
      return item.value.toLocaleString(undefined, { maximumFractionDigits: 0 });
    case 'ratio':
    default:
      return item.value.toFixed(2);
  }
}

export const KPI_GROUPS: { title: string; keys: string[] }[] = [
  { title: 'Valuation', keys: ['pe_ratio', 'dividend_yield', 'eps_ttm'] },
  {
    title: 'Profitability',
    keys: ['roe', 'roa', 'grossMargin', 'profitMargin'],
  },
  { title: 'Balance sheet', keys: ['debtEquity', 'currentRatio'] },
];

export function groupKpis(kpis: StockKpiItem[]): { title: string; items: StockKpiItem[] }[] {
  const byKey = new Map(kpis.map((k) => [k.key, k]));
  return KPI_GROUPS.map(({ title, keys }) => ({
    title,
    items: keys.map((key) => byKey.get(key)).filter((k): k is StockKpiItem => k != null),
  })).filter((g) => g.items.length > 0);
}
