import type { PortfolioSummary } from '../api/executionTypes';
import { formatBacktestPct } from './backtestData';
import {
  formatOverviewProfit,
  formatOverviewProfitPct,
  profitMetricClass,
} from './tradingOverview';

export function computeUntrackedQty(alpacaQty: number, attributedQty: number): number {
  const remainder = alpacaQty - attributedQty;
  return remainder > 1e-8 ? remainder : 0;
}

export function formatPortfolioPeriodLabel(start: string, end: string): string {
  const startDate = new Date(start);
  const endDate = new Date(end);
  const options: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric', year: 'numeric' };
  return `${startDate.toLocaleDateString('en-US', options)} – ${endDate.toLocaleDateString('en-US', options)}`;
}

export interface PortfolioSummaryCard {
  label: string;
  value: string;
  sublabel?: string;
  toneValue: number | null;
}

export const CLOSED_PNL_HELP = 'Realized from deployment sells in period';
export const OPEN_PNL_HELP = 'Mark-to-market on shares held today vs period start';

export function buildPortfolioSummaryCards(
  summary: PortfolioSummary | null,
  periodLabel: string | null,
): PortfolioSummaryCard[] {
  if (!summary) {
    return [];
  }
  const closedValue = `${formatOverviewProfit(summary.closed_pnl.amount)} (${formatOverviewProfitPct(summary.closed_pnl.pct)})`;
  const openValue = `${formatOverviewProfit(summary.open_pnl.amount)} (${formatOverviewProfitPct(summary.open_pnl.pct)})`;
  const periodSuffix = periodLabel ? ` · ${periodLabel}` : '';
  return [
    {
      label: 'Closed P/L',
      value: closedValue,
      sublabel: `${CLOSED_PNL_HELP}${periodSuffix}`,
      toneValue: summary.closed_pnl.amount,
    },
    {
      label: 'Open P/L',
      value: openValue,
      sublabel: `${OPEN_PNL_HELP}${periodSuffix}`,
      toneValue: summary.open_pnl.amount,
    },
    {
      label: 'QQQ return',
      value: formatBacktestPct(summary.qqq_return_pct),
      sublabel: periodLabel ?? undefined,
      toneValue: summary.qqq_return_pct,
    },
    {
      label: 'VOO return',
      value: formatBacktestPct(summary.voo_return_pct),
      sublabel: periodLabel ?? undefined,
      toneValue: summary.voo_return_pct,
    },
  ];
}

export function portfolioPlCellClass(value: number | null | undefined): string {
  return profitMetricClass(value);
}

export function formatPortfolioPl(value: number): string {
  return formatOverviewProfit(value);
}
