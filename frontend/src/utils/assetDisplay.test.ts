import { describe, expect, it } from 'vitest';
import { formatAssetOptionLabel } from './assetDisplay';

describe('formatAssetOptionLabel', () => {
  it('returns symbol only when name is null', () => {
    expect(formatAssetOptionLabel({ symbol: 'AAPL', name: null })).toBe('AAPL');
  });

  it('returns symbol only when name matches symbol (case-insensitive)', () => {
    expect(formatAssetOptionLabel({ symbol: 'AAPL', name: 'AAPL' })).toBe('AAPL');
    expect(formatAssetOptionLabel({ symbol: 'AAPL', name: 'aapl' })).toBe('AAPL');
  });

  it('returns symbol — name when name differs', () => {
    expect(formatAssetOptionLabel({ symbol: 'AAPL', name: 'Apple Inc.' })).toBe('AAPL — Apple Inc.');
  });

  it('ignores whitespace-only name', () => {
    expect(formatAssetOptionLabel({ symbol: 'MSFT', name: '   ' })).toBe('MSFT');
  });
});
