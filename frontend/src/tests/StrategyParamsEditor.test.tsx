import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import StrategyParamsEditor from '../components/StrategyParamsEditor';
import { DEFAULT_PARAMS_MAP } from '../constants/strategies';

function buildParamsMap(strategies: string[]) {
  return Object.fromEntries(
    strategies.map((s) => [s, { ...(DEFAULT_PARAMS_MAP[s] ?? {}) }])
  );
}

describe('StrategyParamsEditor', () => {
  it('renders nothing when no strategies are selected', () => {
    const { container } = render(
      <StrategyParamsEditor
        selectedStrategies={[]}
        paramsMap={{}}
        onChange={vi.fn()}
      />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders a section for each selected strategy', () => {
    render(
      <StrategyParamsEditor
        selectedStrategies={['ema_cross', 'rsi']}
        paramsMap={buildParamsMap(['ema_cross', 'rsi'])}
        onChange={vi.fn()}
      />
    );
    expect(screen.getByText('EMA Cross')).toBeInTheDocument();
    expect(screen.getByText(/RSI/i)).toBeInTheDocument();
  });

  it('renders number inputs for each parameter of a strategy', () => {
    render(
      <StrategyParamsEditor
        selectedStrategies={['ema_cross']}
        paramsMap={buildParamsMap(['ema_cross'])}
        onChange={vi.fn()}
      />
    );
    expect(screen.getByLabelText('Fast Span')).toBeInTheDocument();
    expect(screen.getByLabelText('Slow Span')).toBeInTheDocument();
  });

  it('displays default values in the inputs', () => {
    render(
      <StrategyParamsEditor
        selectedStrategies={['ema_cross']}
        paramsMap={buildParamsMap(['ema_cross'])}
        onChange={vi.fn()}
      />
    );
    const fastInput = screen.getByLabelText('Fast Span') as HTMLInputElement;
    const slowInput = screen.getByLabelText('Slow Span') as HTMLInputElement;
    expect(fastInput.value).toBe(String(DEFAULT_PARAMS_MAP['ema_cross'].fast_span));
    expect(slowInput.value).toBe(String(DEFAULT_PARAMS_MAP['ema_cross'].slow_span));
  });

  it('calls onChange with updated value when an input changes', () => {
    const handleChange = vi.fn();
    render(
      <StrategyParamsEditor
        selectedStrategies={['ema_cross']}
        paramsMap={buildParamsMap(['ema_cross'])}
        onChange={handleChange}
      />
    );
    const fastInput = screen.getByLabelText('Fast Span');
    fireEvent.change(fastInput, { target: { value: '20' } });
    expect(handleChange).toHaveBeenCalledOnce();
    const updatedMap = handleChange.mock.calls[0][0] as Record<string, Record<string, number>>;
    expect(updatedMap['ema_cross'].fast_span).toBe(20);
  });

  it('does not call onChange for non-numeric input', () => {
    const handleChange = vi.fn();
    render(
      <StrategyParamsEditor
        selectedStrategies={['ema_cross']}
        paramsMap={buildParamsMap(['ema_cross'])}
        onChange={handleChange}
      />
    );
    const fastInput = screen.getByLabelText('Fast Span');
    fireEvent.change(fastInput, { target: { value: 'abc' } });
    expect(handleChange).not.toHaveBeenCalled();
  });

  it('resets strategy params to defaults when Reset is clicked', () => {
    const handleChange = vi.fn();
    const customMap = { ema_cross: { fast_span: 99, slow_span: 200 } };
    render(
      <StrategyParamsEditor
        selectedStrategies={['ema_cross']}
        paramsMap={customMap}
        onChange={handleChange}
      />
    );
    fireEvent.click(screen.getByText('Reset'));
    expect(handleChange).toHaveBeenCalledOnce();
    const resetMap = handleChange.mock.calls[0][0] as Record<string, Record<string, number>>;
    expect(resetMap['ema_cross']).toEqual(DEFAULT_PARAMS_MAP['ema_cross']);
  });

  it('collapses and expands a strategy section on header click', () => {
    render(
      <StrategyParamsEditor
        selectedStrategies={['ema_cross']}
        paramsMap={buildParamsMap(['ema_cross'])}
        onChange={vi.fn()}
      />
    );
    const fastInput = screen.getByLabelText('Fast Span');
    expect(fastInput).toBeVisible();

    fireEvent.click(screen.getByText('EMA Cross'));
    expect(screen.queryByLabelText('Fast Span')).not.toBeInTheDocument();

    fireEvent.click(screen.getByText('EMA Cross'));
    expect(screen.getByLabelText('Fast Span')).toBeInTheDocument();
  });

  it('preserves other strategy params when one strategy param changes', () => {
    const handleChange = vi.fn();
    const paramsMap = buildParamsMap(['ema_cross', 'rsi']);
    render(
      <StrategyParamsEditor
        selectedStrategies={['ema_cross', 'rsi']}
        paramsMap={paramsMap}
        onChange={handleChange}
      />
    );
    const fastInput = screen.getByLabelText('Fast Span');
    fireEvent.change(fastInput, { target: { value: '5' } });
    const updatedMap = handleChange.mock.calls[0][0] as Record<string, Record<string, number>>;
    expect(updatedMap['ema_cross'].fast_span).toBe(5);
    expect(updatedMap['rsi']).toEqual(paramsMap['rsi']);
  });
});
