import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import RangeScoreBar from '../components/RangeScoreBar';

describe('RangeScoreBar', () => {
  it('renders label and numeric value', () => {
    render(<RangeScoreBar label="Conviction Score" value={0.38} min={0} max={1} />);
    expect(screen.getByText('Conviction Score')).toBeInTheDocument();
    expect(screen.getByText('0.38')).toBeInTheDocument();
  });

  it('renders min and max labels for 0..1 range', () => {
    render(<RangeScoreBar label="Conviction Score" value={0.5} min={0} max={1} />);
    expect(screen.getByText('0')).toBeInTheDocument();
    expect(screen.getByText('+1.0')).toBeInTheDocument();
  });

  it('renders min and max labels for -1..1 range', () => {
    render(<RangeScoreBar label="Sentiment Score" value={0} min={-1} max={1} />);
    expect(screen.getByText('-1.0')).toBeInTheDocument();
    expect(screen.getByText('+1.0')).toBeInTheDocument();
  });

  it('renders dash when value is null', () => {
    render(<RangeScoreBar label="Macro Score" value={null} min={-1} max={1} />);
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('applies green color class for value well above midpoint', () => {
    const { container } = render(
      <RangeScoreBar label="Conviction Score" value={0.9} min={0} max={1} />,
    );
    const fill = container.querySelector('.bg-green-500');
    expect(fill).toBeTruthy();
  });

  it('applies red color class for value well below midpoint', () => {
    const { container } = render(
      <RangeScoreBar label="Sentiment Score" value={-0.8} min={-1} max={1} />,
    );
    const fill = container.querySelector('.bg-red-500');
    expect(fill).toBeTruthy();
  });

  it('applies yellow color class for value near midpoint', () => {
    const { container } = render(
      <RangeScoreBar label="Macro Score" value={0.05} min={-1} max={1} />,
    );
    const fill = container.querySelector('.bg-yellow-500');
    expect(fill).toBeTruthy();
  });

  it('positions dot near left edge for minimum value', () => {
    const { container } = render(
      <RangeScoreBar label="Conviction Score" value={0} min={0} max={1} />,
    );
    const dot = container.querySelector('[style*="left: calc(0%"]');
    expect(dot).toBeTruthy();
  });

  it('positions dot near right edge for maximum value', () => {
    const { container } = render(
      <RangeScoreBar label="Conviction Score" value={1} min={0} max={1} />,
    );
    const dot = container.querySelector('[style*="left: calc(100%"]');
    expect(dot).toBeTruthy();
  });
});
