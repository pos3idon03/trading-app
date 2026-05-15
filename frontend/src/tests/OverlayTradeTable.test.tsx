import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { ChartOverlayTradeEntry } from '../api/types';
import OverlayTradeTable from '../components/OverlayTradeTable';

function makeTrade(overrides: Partial<ChartOverlayTradeEntry> = {}): ChartOverlayTradeEntry {
  return {
    entry_time: '2024-01-02T09:30:00Z',
    exit_time: '2024-01-15T16:00:00Z',
    direction: 'long',
    entry_price: 100,
    exit_price: 110,
    pnl: 10,
    return_pct: 0.1,
    ...overrides,
  };
}

describe('OverlayTradeTable', () => {
  it('renders nothing when trade list is empty', () => {
    const { container } = render(<OverlayTradeTable trades={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders the correct number of table rows', () => {
    const trades = [makeTrade(), makeTrade({ return_pct: -0.05 }), makeTrade({ return_pct: 0.2 })];
    render(<OverlayTradeTable trades={trades} />);
    const rows = screen.getAllByRole('row');
    // 1 header row + 3 data rows
    expect(rows).toHaveLength(4);
  });

  it('displays Total Transactions correctly', () => {
    render(<OverlayTradeTable trades={[makeTrade(), makeTrade()]} />);
    expect(screen.getByText('2')).toBeTruthy();
  });

  it('displays Profitable Transactions correctly', () => {
    const trades = [
      makeTrade({ return_pct: 0.1 }),
      makeTrade({ return_pct: -0.05 }),
      makeTrade({ return_pct: 0.2 }),
    ];
    render(<OverlayTradeTable trades={trades} />);
    expect(screen.getByText('Profitable Transactions')).toBeTruthy();
    // 2 profitable out of 3
    const cells = screen.getAllByText('2');
    expect(cells.length).toBeGreaterThan(0);
  });

  it('displays Average Profit % with a + sign', () => {
    render(<OverlayTradeTable trades={[makeTrade({ return_pct: 0.1 })]} />);
    expect(screen.getByText('+10.00%')).toBeTruthy();
  });

  it('displays Average Loss % as negative', () => {
    render(<OverlayTradeTable trades={[makeTrade({ return_pct: -0.05 })]} />);
    expect(screen.getByText('-5.00%')).toBeTruthy();
  });

  it('displays Total Profit / Loss card with correct value', () => {
    const trades = [
      makeTrade({ pnl: 10 }),
      makeTrade({ pnl: -3 }),
    ];
    render(<OverlayTradeTable trades={trades} />);
    expect(screen.getByText('Total Profit / Loss')).toBeTruthy();
    expect(screen.getByText('+7.00')).toBeTruthy();
  });

  it('displays Total Profit/Loss % card with summed return_pct', () => {
    const trades = [
      makeTrade({ return_pct: 0.1 }),
      makeTrade({ return_pct: -0.05 }),
    ];
    render(<OverlayTradeTable trades={trades} />);
    expect(screen.getByText('Total Profit/Loss %')).toBeTruthy();
    expect(screen.getByText('+5.00%')).toBeTruthy();
  });

  it('displays Profit / Loss column for each row', () => {
    render(<OverlayTradeTable trades={[makeTrade({ pnl: 10 })]} />);
    expect(screen.getByText('Profit / Loss')).toBeTruthy();
    expect(screen.getByText('+10.00')).toBeTruthy();
  });

  it('renames Profit % column to Profit/Loss %', () => {
    render(<OverlayTradeTable trades={[makeTrade()]} />);
    expect(screen.getByText('Profit/Loss %')).toBeTruthy();
  });

  it('shows Open for trades without exit', () => {
    render(
      <OverlayTradeTable
        trades={[makeTrade({ exit_time: null, exit_price: null, pnl: null, return_pct: null })]}
      />
    );
    const openCells = screen.getAllByText('Open');
    expect(openCells.length).toBeGreaterThanOrEqual(1);
  });

  it('shows buy date and sell date columns', () => {
    render(<OverlayTradeTable trades={[makeTrade()]} />);
    expect(screen.getByText('2024-01-02')).toBeTruthy();
    expect(screen.getByText('2024-01-15')).toBeTruthy();
  });

  it('colors profitable rows green and losing rows red', () => {
    const trades = [
      makeTrade({ return_pct: 0.1 }),
      makeTrade({ return_pct: -0.05 }),
    ];
    render(<OverlayTradeTable trades={trades} />);
    const profitCell = screen.getByText('+10.00%');
    const lossCell = screen.getByText('-5.00%');
    expect(profitCell.className).toContain('green');
    expect(lossCell.className).toContain('red');
  });
});
