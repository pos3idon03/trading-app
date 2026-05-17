import { describe, it, expect } from 'vitest';
import { isSymbolSubscribed, streamSymbolKey } from '../utils/streamSymbolMatch';

describe('streamSymbolMatch', () => {
  it('normalizes BTC-USD to BTC/USD key', () => {
    expect(streamSymbolKey('BTC-USD')).toBe('BTC/USD');
  });

  it('matches BTC-USD monitor to BTC-USD subscription', () => {
    expect(isSymbolSubscribed('BTC-USD', ['BTC-USD'])).toBe(true);
  });

  it('matches BTC-USD monitor to BTC/USD subscription', () => {
    expect(isSymbolSubscribed('BTC-USD', ['BTC/USD'])).toBe(true);
  });
});
