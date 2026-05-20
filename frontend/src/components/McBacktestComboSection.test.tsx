import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import McBacktestComboSection, {
  comboConfigToRequestPayload,
  DEFAULT_MC_COMBO_CONFIG,
  validateMcComboConfig,
} from './McBacktestComboSection';

describe('McBacktestComboSection', () => {
  it('toggle reveals strategy picker', () => {
    const onChange = vi.fn();
    render(
      <McBacktestComboSection
        config={DEFAULT_MC_COMBO_CONFIG}
        onChange={onChange}
        execTimeframe="1d"
      />,
    );
    expect(screen.queryByLabelText('Add algo strategy')).not.toBeInTheDocument();
    fireEvent.click(screen.getByLabelText('Algo combo'));
    expect(screen.getByLabelText('Add algo strategy')).toBeInTheDocument();
    expect(screen.getByText(/Add at least one strategy/i)).toBeInTheDocument();
  });

  it('validateMcComboConfig requires min one algo when enabled', () => {
    expect(validateMcComboConfig(DEFAULT_MC_COMBO_CONFIG)).toBeNull();
    expect(
      validateMcComboConfig({ ...DEFAULT_MC_COMBO_CONFIG, enabled: true, entries: [] }),
    ).toMatch(/at least one algo/i);
  });

  it('comboConfigToRequestPayload includes combo fields when enabled', () => {
    const payload = comboConfigToRequestPayload({
      enabled: true,
      mode: 'and',
      threshold: 0.5,
      mcLegWeight: 1,
      entries: [
        { id: '1', strategy_name: 'rsi', weight: 1, timeframe: '1d' },
      ],
      paramsMap: { rsi: { period: 14 } },
    });
    expect(payload.combo_enabled).toBe(true);
    expect(payload.algo_strategies).toHaveLength(1);
    expect(payload.algo_strategies?.[0].strategy_name).toBe('rsi');
  });
});
