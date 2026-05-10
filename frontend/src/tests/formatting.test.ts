import { describe, it, expect } from 'vitest';
import { fmt, fmtPct } from '../utils/formatting';

describe('fmt', () => {
  it('returns em-dash for null', () => {
    expect(fmt(null)).toBe('—');
  });

  it('returns em-dash for undefined', () => {
    expect(fmt(undefined)).toBe('—');
  });

  it('formats a number with default 4 decimals', () => {
    expect(fmt(1.23456789)).toBe('1.2346');
  });

  it('respects custom decimals', () => {
    expect(fmt(1.5, 2)).toBe('1.50');
  });

  it('appends suffix', () => {
    expect(fmt(1.5, 2, '%')).toBe('1.50%');
  });

  it('formats zero correctly', () => {
    expect(fmt(0, 2)).toBe('0.00');
  });
});

describe('fmtPct', () => {
  it('returns em-dash for null', () => {
    expect(fmtPct(null)).toBe('—');
  });

  it('returns em-dash for undefined', () => {
    expect(fmtPct(undefined)).toBe('—');
  });

  it('formats a decimal as percentage', () => {
    expect(fmtPct(0.1234)).toBe('12.34%');
  });

  it('formats negative values', () => {
    expect(fmtPct(-0.05)).toBe('-5.00%');
  });

  it('formats zero', () => {
    expect(fmtPct(0)).toBe('0.00%');
  });
});
