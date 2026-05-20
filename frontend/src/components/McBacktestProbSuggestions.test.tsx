import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import McBacktestProbSuggestions from './McBacktestProbSuggestions';
import type { McBacktestSignalPoint, McBacktestZoneStats } from '../api/types';

const baseZoneStats: McBacktestZoneStats = {
  entry_zone_pct: 10,
  exit_zone_pct: 10,
  middle_zone_pct: 80,
  bars_with_prob: 12,
  prob_min: 0.44,
  prob_p25: 0.46,
  prob_median: 0.5,
  prob_p75: 0.54,
  prob_max: 0.56,
  suggested_buy_threshold: 0.54,
  suggested_sell_threshold: 0.46,
};

const signalLog: McBacktestSignalPoint[] = Array.from({ length: 12 }, (_, i) => ({
  time: `2024-01-${String(i + 1).padStart(2, '0')}T00:00:00+00:00`,
  prob_positive: 0.44 + i * 0.01,
  effective_prob: 0.44 + i * 0.01,
  signal: 'FLAT',
}));

describe('McBacktestProbSuggestions', () => {
  it('renders percentiles and suggested thresholds', () => {
    render(
      <McBacktestProbSuggestions
        zoneStats={baseZoneStats}
        signalLog={signalLog}
        entryConfirmationBars={2}
        onApplySuggested={vi.fn()}
      />,
    );
    expect(screen.getByText(/Min: 44.0%/)).toBeInTheDocument();
    expect(screen.getByText(/Suggested entry ≥ 54.0%/)).toBeInTheDocument();
    expect(screen.getByText(/Suggested exit < 46.0%/)).toBeInTheDocument();
    expect(screen.getByText(/entry confirmation = 2/)).toBeInTheDocument();
  });

  it('calls onApplySuggested with rounded pct strings', () => {
    const onApply = vi.fn();
    render(
      <McBacktestProbSuggestions
        zoneStats={baseZoneStats}
        signalLog={signalLog}
        entryConfirmationBars={1}
        onApplySuggested={onApply}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: /apply suggested thresholds/i }));
    expect(onApply).toHaveBeenCalledWith('54', '46');
  });

  it('shows insufficient data message when suggestions are null', () => {
    render(
      <McBacktestProbSuggestions
        zoneStats={{
          ...baseZoneStats,
          bars_with_prob: 5,
          suggested_buy_threshold: null,
          suggested_sell_threshold: null,
        }}
        signalLog={signalLog.slice(0, 5)}
        entryConfirmationBars={1}
        onApplySuggested={vi.fn()}
      />,
    );
    expect(screen.getByText(/Need at least 10 bars/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /apply suggested thresholds/i })).not.toBeInTheDocument();
  });

  it('returns null when no bars with prob', () => {
    const { container } = render(
      <McBacktestProbSuggestions
        zoneStats={{ ...baseZoneStats, bars_with_prob: 0 }}
        signalLog={[]}
        entryConfirmationBars={1}
        onApplySuggested={vi.fn()}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
