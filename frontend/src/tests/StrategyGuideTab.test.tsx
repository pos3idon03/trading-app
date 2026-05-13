import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import StrategyGuideTab from '../components/StrategyGuideTab';
import { STRATEGIES, DEFAULT_PARAMS_MAP } from '../constants/strategies';
import { STRATEGY_GUIDE } from '../constants/strategyGuide';

// ── Completeness assertions (data-layer) ──────────────────────────────────

describe('STRATEGY_GUIDE completeness', () => {
  it('has an entry for every strategy in STRATEGIES', () => {
    const missing = STRATEGIES.filter((s) => !(s.value in STRATEGY_GUIDE));
    expect(missing).toHaveLength(0);
  });

  it('covers all DEFAULT_PARAMS_MAP keys in each strategy paramDescriptions', () => {
    const gaps: string[] = [];
    for (const [strategyId, params] of Object.entries(DEFAULT_PARAMS_MAP)) {
      const guide = STRATEGY_GUIDE[strategyId];
      if (!guide) continue;
      for (const key of Object.keys(params)) {
        if (!(key in guide.paramDescriptions)) {
          gaps.push(`${strategyId}.paramDescriptions.${key}`);
        }
      }
    }
    expect(gaps).toHaveLength(0);
  });

  it('has non-empty overview, whenBuy, whenSell, and valueAndCaveats for every entry', () => {
    const incomplete: string[] = [];
    for (const [id, g] of Object.entries(STRATEGY_GUIDE)) {
      if (!g.overview.trim()) incomplete.push(`${id}.overview`);
      if (!g.whenBuy.trim()) incomplete.push(`${id}.whenBuy`);
      if (!g.whenSell.trim()) incomplete.push(`${id}.whenSell`);
      if (!g.valueAndCaveats.trim()) incomplete.push(`${id}.valueAndCaveats`);
    }
    expect(incomplete).toHaveLength(0);
  });
});

// ── Rendering ─────────────────────────────────────────────────────────────

describe('StrategyGuideTab', () => {
  it('renders the section heading', () => {
    render(<StrategyGuideTab />);
    expect(screen.getByText(/strategy guide/i)).toBeInTheDocument();
  });

  it('renders a card for every strategy', () => {
    render(<StrategyGuideTab />);
    for (const s of STRATEGIES) {
      expect(screen.getByText(s.label)).toBeInTheDocument();
    }
  });

  it('shows group filter buttons including "All"', () => {
    render(<StrategyGuideTab />);
    expect(screen.getByRole('button', { name: 'All' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Momentum' })).toBeInTheDocument();
  });

  it('filters the list when a group is selected', () => {
    render(<StrategyGuideTab />);
    fireEvent.click(screen.getByRole('button', { name: 'Seasonal' }));
    expect(screen.getByText('Seasonal / Sell in May')).toBeInTheDocument();
    expect(screen.queryByText('MA Crossover')).not.toBeInTheDocument();
  });

  it('expands a strategy card when clicked and shows content', () => {
    render(<StrategyGuideTab />);
    // Click the MA Crossover card header to expand it
    fireEvent.click(screen.getByText('MA Crossover'));
    expect(screen.getByText(/overview/i)).toBeInTheDocument();
    expect(screen.getByText(/when it buys/i)).toBeInTheDocument();
    expect(screen.getByText(/when it sells/i)).toBeInTheDocument();
  });

  it('shows the total strategy count', () => {
    render(<StrategyGuideTab />);
    expect(screen.getByText(`${STRATEGIES.length} strategies`)).toBeInTheDocument();
  });
});
