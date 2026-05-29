import { describe, expect, it } from 'vitest';
import { labelSearchHorizons } from '../utils/mlBacktestConfig';

describe('labelSearchHorizons', () => {
  it('centers a step-2 grid on the universe label horizon', () => {
    expect(labelSearchHorizons(24)).toEqual([20, 22, 24, 26, 28]);
  });

  it('handles small centers near the lower bound', () => {
    expect(labelSearchHorizons(5)).toEqual([1, 3, 5, 7, 9]);
    expect(labelSearchHorizons(1)).toEqual([1, 3, 5]);
  });

  it('handles centers near the upper bound', () => {
    expect(labelSearchHorizons(59)).toEqual([55, 57, 59]);
    expect(labelSearchHorizons(60)).toEqual([56, 58, 60]);
  });
});
