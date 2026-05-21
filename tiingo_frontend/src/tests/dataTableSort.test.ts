import { describe, expect, it } from 'vitest';
import { compareSortValues, maPositionSortValue, sortRows } from '../utils/dataTableSort';

describe('compareSortValues', () => {
  it('sorts numbers ascending with nulls last', () => {
    const values = [10, null, 5, -3];
    const sorted = [...values].sort((a, b) => compareSortValues(a, b, 'asc'));
    expect(sorted).toEqual([-3, 5, 10, null]);
  });

  it('sorts strings descending', () => {
    const sorted = sortRows([{ symbol: 'AAPL' }, { symbol: 'MSFT' }], (row) => row.symbol, 'desc');
    expect(sorted.map((row) => row.symbol)).toEqual(['MSFT', 'AAPL']);
  });
});

describe('sortRows', () => {
  it('sorts rows by extracted value', () => {
    const rows = [{ symbol: 'MSFT' }, { symbol: 'AAPL' }];
    const sorted = sortRows(rows, (row) => row.symbol, 'asc');
    expect(sorted.map((row) => row.symbol)).toEqual(['AAPL', 'MSFT']);
  });
});

describe('maPositionSortValue', () => {
  it('ranks above higher than below', () => {
    expect(maPositionSortValue('Above')).toBeGreaterThan(maPositionSortValue('Below'));
  });
});
