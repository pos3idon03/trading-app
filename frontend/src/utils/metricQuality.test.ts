import { describe, it, expect } from 'vitest';
import {
  getSharpeTier,
  getProfitFactorTier,
  normalizeSharpeFill,
  normalizeProfitFactorFill,
} from './metricQuality';

describe('getSharpeTier', () => {
  it('returns suboptimal below 1.0', () => {
    expect(getSharpeTier(0.99)?.label).toBe('Suboptimal');
    expect(getSharpeTier(0.99)?.tierIndex).toBe(0);
  });

  it('returns good at 1.0 and below 2.0', () => {
    expect(getSharpeTier(1.0)?.label).toBe('Good');
    expect(getSharpeTier(1.99)?.label).toBe('Good');
    expect(getSharpeTier(1.5)?.tierIndex).toBe(1);
  });

  it('returns very good at 2.0 and below 3.0', () => {
    expect(getSharpeTier(2.0)?.label).toBe('Very Good');
    expect(getSharpeTier(2.99)?.label).toBe('Very Good');
  });

  it('returns excellent at 3.0 and above', () => {
    expect(getSharpeTier(3.0)?.label).toBe('Excellent');
    expect(getSharpeTier(5.0)?.tierIndex).toBe(3);
  });

  it('returns null for invalid values', () => {
    expect(getSharpeTier(null)).toBeNull();
    expect(getSharpeTier(undefined)).toBeNull();
    expect(getSharpeTier(NaN)).toBeNull();
  });
});

describe('getProfitFactorTier', () => {
  it('returns losing below 1.0', () => {
    expect(getProfitFactorTier(0.99)?.label).toBe('Losing');
  });

  it('returns moderate from 1.0 to below 1.5', () => {
    expect(getProfitFactorTier(1.0)?.label).toBe('Moderate');
    expect(getProfitFactorTier(1.49)?.label).toBe('Moderate');
  });

  it('returns strong from 1.5 to below 2.5', () => {
    expect(getProfitFactorTier(1.5)?.label).toBe('Strong');
    expect(getProfitFactorTier(2.49)?.label).toBe('Strong');
  });

  it('returns exceptional at 2.5 and above', () => {
    expect(getProfitFactorTier(2.5)?.label).toBe('Exceptional');
    expect(getProfitFactorTier(4.0)?.tierIndex).toBe(3);
  });

  it('returns null for invalid values', () => {
    expect(getProfitFactorTier(null)).toBeNull();
    expect(getProfitFactorTier(undefined)).toBeNull();
  });
});

describe('normalizeSharpeFill', () => {
  it('scales value against cap', () => {
    expect(normalizeSharpeFill(1.75)).toBeCloseTo(1.75 / 3.5);
  });

  it('clamps above cap', () => {
    expect(normalizeSharpeFill(10)).toBe(1);
  });

  it('clamps negative values to 0', () => {
    expect(normalizeSharpeFill(-1)).toBe(0);
  });

  it('returns null for invalid values', () => {
    expect(normalizeSharpeFill(null)).toBeNull();
    expect(normalizeSharpeFill(NaN)).toBeNull();
  });
});

describe('normalizeProfitFactorFill', () => {
  it('scales value against cap', () => {
    expect(normalizeProfitFactorFill(1.75)).toBeCloseTo(1.75 / 3.5);
  });

  it('clamps above cap', () => {
    expect(normalizeProfitFactorFill(10)).toBe(1);
  });

  it('returns null for invalid values', () => {
    expect(normalizeProfitFactorFill(undefined)).toBeNull();
  });
});
