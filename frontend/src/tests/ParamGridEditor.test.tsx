import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ParamGridEditor from '../components/ParamGridEditor';

describe('ParamGridEditor', () => {
  const grid = { fast_window: [5, 10, 20], slow_window: [30, 50, 100] };

  it('renders a row for each grid parameter', () => {
    render(<ParamGridEditor grid={grid} onChange={vi.fn()} />);
    expect(screen.getByText('fast_window')).toBeInTheDocument();
    expect(screen.getByText('slow_window')).toBeInTheDocument();
  });

  it('displays comma-separated current values in inputs', () => {
    render(<ParamGridEditor grid={grid} onChange={vi.fn()} />);
    const inputs = screen.getAllByRole('textbox') as HTMLInputElement[];
    expect(inputs[0].value).toBe('5, 10, 20');
    expect(inputs[1].value).toBe('30, 50, 100');
  });

  it('calls onChange with updated values when input changes', () => {
    const onChange = vi.fn();
    render(<ParamGridEditor grid={grid} onChange={onChange} />);
    const inputs = screen.getAllByRole('textbox');
    fireEvent.change(inputs[0], { target: { value: '1, 2, 3' } });
    expect(onChange).toHaveBeenCalledWith({
      fast_window: [1, 2, 3],
      slow_window: [30, 50, 100],
    });
  });

  it('filters out non-numeric values', () => {
    const onChange = vi.fn();
    render(<ParamGridEditor grid={grid} onChange={onChange} />);
    const inputs = screen.getAllByRole('textbox');
    fireEvent.change(inputs[0], { target: { value: '1, abc, 3' } });
    expect(onChange).toHaveBeenCalledWith({
      fast_window: [1, 3],
      slow_window: [30, 50, 100],
    });
  });
});
