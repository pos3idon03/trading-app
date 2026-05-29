import { describe, expect, it } from 'vitest';

import {
  buildPortfolioSummaryCards,
  CLOSED_PNL_HELP,
  computeUntrackedQty,
  formatPortfolioPeriodLabel,
  OPEN_PNL_HELP,
} from '../utils/tradingPortfolio';

describe('tradingPortfolio utils', () => {
  it('computes untracked qty as alpaca minus attributed', () => {
    expect(computeUntrackedQty(0.33, 0.1)).toBeCloseTo(0.23, 6);
  });

  it('returns zero when fully attributed', () => {
    expect(computeUntrackedQty(1, 1)).toBe(0);
  });

  it('formats portfolio period label', () => {
    const label = formatPortfolioPeriodLabel('2026-01-01T00:00:00Z', '2026-05-28T00:00:00Z');
    expect(label).toContain('2026');
    expect(label).toContain('–');
  });

  it('builds summary cards from portfolio summary', () => {
    const cards = buildPortfolioSummaryCards(
      {
        closed_pnl: { amount: 100, pct: 10 },
        open_pnl: { amount: -20, pct: -2 },
        qqq_return_pct: 5.5,
        voo_return_pct: 4.2,
      },
      'Jan 1, 2026 – May 28, 2026',
    );
    expect(cards).toHaveLength(4);
    expect(cards[0].label).toBe('Closed P/L');
    expect(cards[0].value).toContain('+$100.00');
    expect(cards[0].sublabel).toContain(CLOSED_PNL_HELP);
    expect(cards[1].sublabel).toContain(OPEN_PNL_HELP);
    expect(cards[1].toneValue).toBe(-20);
    expect(cards[2].value).toContain('5.50%');
  });
});
