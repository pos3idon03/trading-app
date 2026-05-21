import { describe, expect, it } from 'vitest';
import {
  backfillStartedMessage,
  deleteConfirmMessage,
  deleteSuccessMessage,
} from '../utils/watchlistMessages';

describe('watchlistMessages', () => {
  it('builds backfill started message', () => {
    expect(backfillStartedMessage('AAPL')).toBe('Backfill for stock "AAPL" has started.');
  });

  it('builds delete success message', () => {
    expect(deleteSuccessMessage('AAPL')).toBe('"AAPL" removed from watchlist.');
  });

  it('builds delete confirm message', () => {
    expect(deleteConfirmMessage('AAPL')).toContain('Remove AAPL from the watchlist');
    expect(deleteConfirmMessage('AAPL')).toContain('OHLCV and fundamentals');
  });
});
