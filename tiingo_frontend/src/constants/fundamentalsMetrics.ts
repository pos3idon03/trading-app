export type FundamentalFormat = 'currency' | 'percent' | 'ratio' | 'perShare';

export type FundamentalStatementGroup =
  | 'incomeStatement'
  | 'cashFlow'
  | 'balanceSheet'
  | 'overview';

export interface FundamentalMetricDef {
  dataCode: string;
  label: string;
  group: FundamentalStatementGroup;
  groupLabel: string;
  format: FundamentalFormat;
}

const GROUP_LABELS: Record<FundamentalStatementGroup, string> = {
  incomeStatement: 'Income statement',
  cashFlow: 'Cash flow',
  balanceSheet: 'Balance sheet',
  overview: 'Overview',
};

/** Tiingo `dataCode` values from /fundamentals/{ticker}/statements statementData */
export const FUNDAMENTAL_METRICS: FundamentalMetricDef[] = [
  { dataCode: 'revenue', label: 'Total Revenue', group: 'incomeStatement', groupLabel: GROUP_LABELS.incomeStatement, format: 'currency' },
  { dataCode: 'grossProfit', label: 'Gross Profit', group: 'incomeStatement', groupLabel: GROUP_LABELS.incomeStatement, format: 'currency' },
  { dataCode: 'opinc', label: 'Operating Income', group: 'incomeStatement', groupLabel: GROUP_LABELS.incomeStatement, format: 'currency' },
  { dataCode: 'netinc', label: 'Net Income', group: 'incomeStatement', groupLabel: GROUP_LABELS.incomeStatement, format: 'currency' },
  { dataCode: 'eps', label: 'EPS', group: 'incomeStatement', groupLabel: GROUP_LABELS.incomeStatement, format: 'perShare' },
  { dataCode: 'ebitda', label: 'EBITDA', group: 'incomeStatement', groupLabel: GROUP_LABELS.incomeStatement, format: 'currency' },
  { dataCode: 'freeCashFlow', label: 'Free Cash Flow', group: 'cashFlow', groupLabel: GROUP_LABELS.cashFlow, format: 'currency' },
  { dataCode: 'ncfo', label: 'Operating Cash Flow', group: 'cashFlow', groupLabel: GROUP_LABELS.cashFlow, format: 'currency' },
  { dataCode: 'totalAssets', label: 'Total Assets', group: 'balanceSheet', groupLabel: GROUP_LABELS.balanceSheet, format: 'currency' },
  { dataCode: 'debt', label: 'Total Debt', group: 'balanceSheet', groupLabel: GROUP_LABELS.balanceSheet, format: 'currency' },
  { dataCode: 'equity', label: 'Total Equity', group: 'balanceSheet', groupLabel: GROUP_LABELS.balanceSheet, format: 'currency' },
  { dataCode: 'roe', label: 'Return on Equity', group: 'overview', groupLabel: GROUP_LABELS.overview, format: 'ratio' },
  { dataCode: 'roa', label: 'Return on Assets', group: 'overview', groupLabel: GROUP_LABELS.overview, format: 'ratio' },
  { dataCode: 'debtEquity', label: 'Debt / Equity', group: 'overview', groupLabel: GROUP_LABELS.overview, format: 'ratio' },
  { dataCode: 'grossMargin', label: 'Gross Margin', group: 'overview', groupLabel: GROUP_LABELS.overview, format: 'percent' },
  { dataCode: 'profitMargin', label: 'Profit Margin', group: 'overview', groupLabel: GROUP_LABELS.overview, format: 'percent' },
  { dataCode: 'currentRatio', label: 'Current Ratio', group: 'overview', groupLabel: GROUP_LABELS.overview, format: 'ratio' },
];

export const FUNDAMENTAL_METRIC_CODES = FUNDAMENTAL_METRICS.map((m) => m.dataCode);

export const FUNDAMENTAL_GROUPS: FundamentalStatementGroup[] = [
  'incomeStatement',
  'cashFlow',
  'balanceSheet',
  'overview',
];

export function metricsByGroup(group: FundamentalStatementGroup): FundamentalMetricDef[] {
  return FUNDAMENTAL_METRICS.filter((m) => m.group === group);
}
