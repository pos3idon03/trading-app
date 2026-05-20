import { describe, it, expect } from 'vitest';
import { countValidBacktestCombos } from '../utils/mcBacktestPreset';
import { DEFAULT_MC_BACKTEST_GRID } from '../constants/monteCarlo';

describe('countValidBacktestCombos', () => {
  it('counts valid threshold combos for default grid', () => {
    const count = countValidBacktestCombos(DEFAULT_MC_BACKTEST_GRID);
    expect(count).toBe(36);
  });

  it('returns zero when all threshold orders invalid', () => {
    const count = countValidBacktestCombos({
      buy_threshold: [40],
      sell_threshold: [60],
    });
    expect(count).toBe(0);
  });
});
