import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import StrategyMultiSelect from '../components/StrategyMultiSelect';
import { STRATEGIES } from '../constants/strategies';

describe('StrategyMultiSelect', () => {
  it('renders all strategies as checkboxes', () => {
    render(<StrategyMultiSelect selected={[]} onChange={vi.fn()} />);
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes.length).toBe(STRATEGIES.length);
  });

  it('shows the count of selected strategies', () => {
    render(<StrategyMultiSelect selected={['ma_crossover', 'rsi']} onChange={vi.fn()} />);
    expect(screen.getByText(/2 selected/)).toBeInTheDocument();
  });

  it('calls onChange with added strategy when unchecked checkbox is clicked', () => {
    const onChange = vi.fn();
    render(<StrategyMultiSelect selected={[]} onChange={onChange} />);
    const maCheckbox = screen.getAllByRole('checkbox')[0];
    fireEvent.click(maCheckbox);
    expect(onChange).toHaveBeenCalledWith(expect.arrayContaining(['ma_crossover']));
  });

  it('calls onChange without strategy when checked checkbox is clicked', () => {
    const onChange = vi.fn();
    render(<StrategyMultiSelect selected={['ma_crossover']} onChange={onChange} />);
    const maCheckbox = screen.getAllByRole('checkbox')[0];
    fireEvent.click(maCheckbox);
    expect(onChange).toHaveBeenCalledWith([]);
  });

  it('selects all strategies when "All" button is clicked', () => {
    const onChange = vi.fn();
    render(<StrategyMultiSelect selected={[]} onChange={onChange} />);
    fireEvent.click(screen.getByText('All'));
    const call = onChange.mock.calls[0][0] as string[];
    expect(call.length).toBe(STRATEGIES.length);
  });

  it('clears all strategies when "None" button is clicked', () => {
    const onChange = vi.fn();
    render(<StrategyMultiSelect selected={['ma_crossover', 'rsi']} onChange={onChange} />);
    fireEvent.click(screen.getByText('None'));
    expect(onChange).toHaveBeenCalledWith([]);
  });

  it('checks the checkboxes for selected strategies', () => {
    render(<StrategyMultiSelect selected={['ma_crossover']} onChange={vi.fn()} />);
    const checkboxes = screen.getAllByRole('checkbox') as HTMLInputElement[];
    expect(checkboxes[0].checked).toBe(true);
    expect(checkboxes[1].checked).toBe(false);
  });
});
