import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import PositionSizingModal from '../components/PositionSizingModal';

describe('PositionSizingModal', () => {
  const onConfirm = vi.fn().mockResolvedValue(undefined);
  const onClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders with symbol in title', () => {
    render(<PositionSizingModal symbol="AAPL" onConfirm={onConfirm} onClose={onClose} />);
    expect(screen.getByText(/Start Auto-Trading/)).toBeInTheDocument();
    expect(screen.getByText('AAPL')).toBeInTheDocument();
  });

  it('renders amount and percent inputs', () => {
    render(<PositionSizingModal symbol="AAPL" onConfirm={onConfirm} onClose={onClose} />);
    expect(screen.getByPlaceholderText('e.g. 1000')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('e.g. 5')).toBeInTheDocument();
  });

  it('calls onClose when Cancel is clicked', () => {
    render(<PositionSizingModal symbol="AAPL" onConfirm={onConfirm} onClose={onClose} />);
    fireEvent.click(screen.getByText('Cancel'));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('calls onClose when X button is clicked', () => {
    render(<PositionSizingModal symbol="AAPL" onConfirm={onConfirm} onClose={onClose} />);
    fireEvent.click(screen.getByLabelText('Close'));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('calls onConfirm with empty object when no inputs set', async () => {
    render(<PositionSizingModal symbol="AAPL" onConfirm={onConfirm} onClose={onClose} />);
    fireEvent.click(screen.getByText('Start Trading'));
    await waitFor(() => {
      expect(onConfirm).toHaveBeenCalledWith({});
    });
  });

  it('calls onConfirm with max_amount when amount is set', async () => {
    render(<PositionSizingModal symbol="AAPL" onConfirm={onConfirm} onClose={onClose} />);
    fireEvent.change(screen.getByPlaceholderText('e.g. 1000'), { target: { value: '500' } });
    fireEvent.click(screen.getByText('Start Trading'));
    await waitFor(() => {
      expect(onConfirm).toHaveBeenCalledWith({ max_amount_per_position: 500 });
    });
  });

  it('calls onConfirm with max_pct when pct is set', async () => {
    render(<PositionSizingModal symbol="AAPL" onConfirm={onConfirm} onClose={onClose} />);
    fireEvent.change(screen.getByPlaceholderText('e.g. 5'), { target: { value: '10' } });
    fireEvent.click(screen.getByText('Start Trading'));
    await waitFor(() => {
      expect(onConfirm).toHaveBeenCalledWith({ max_pct_of_capital: 10 });
    });
  });

  it('calls onConfirm with both values when both are set', async () => {
    render(<PositionSizingModal symbol="AAPL" onConfirm={onConfirm} onClose={onClose} />);
    fireEvent.change(screen.getByPlaceholderText('e.g. 1000'), { target: { value: '1000' } });
    fireEvent.change(screen.getByPlaceholderText('e.g. 5'), { target: { value: '5' } });
    fireEvent.click(screen.getByText('Start Trading'));
    await waitFor(() => {
      expect(onConfirm).toHaveBeenCalledWith({ max_amount_per_position: 1000, max_pct_of_capital: 5 });
    });
  });

  it('shows priority note when both inputs are filled', async () => {
    render(<PositionSizingModal symbol="AAPL" onConfirm={onConfirm} onClose={onClose} />);
    fireEvent.change(screen.getByPlaceholderText('e.g. 1000'), { target: { value: '1000' } });
    fireEvent.change(screen.getByPlaceholderText('e.g. 5'), { target: { value: '5' } });
    expect(screen.getByText(/max dollar amount takes priority/i)).toBeInTheDocument();
  });

  it('shows validation error for invalid amount', async () => {
    render(<PositionSizingModal symbol="AAPL" onConfirm={onConfirm} onClose={onClose} />);
    fireEvent.change(screen.getByPlaceholderText('e.g. 1000'), { target: { value: '-50' } });
    fireEvent.click(screen.getByText('Start Trading'));
    await waitFor(() => {
      expect(screen.getByText(/Max amount must be a positive number/i)).toBeInTheDocument();
    });
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it('shows validation error for pct over 100', async () => {
    render(<PositionSizingModal symbol="AAPL" onConfirm={onConfirm} onClose={onClose} />);
    fireEvent.change(screen.getByPlaceholderText('e.g. 5'), { target: { value: '150' } });
    fireEvent.click(screen.getByText('Start Trading'));
    await waitFor(() => {
      expect(screen.getByText(/Max % must be between 0 and 100/i)).toBeInTheDocument();
    });
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it('closes on Escape key', () => {
    render(<PositionSizingModal symbol="AAPL" onConfirm={onConfirm} onClose={onClose} />);
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });
});
