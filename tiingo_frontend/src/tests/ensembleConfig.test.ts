import { describe, expect, it } from 'vitest';
import type { StrategyCatalogItem } from '../api/backtestTypes';
import {
  ENSEMBLE_STRATEGY_ID,
  addLeg,
  canAddLeg,
  canRemoveLeg,
  combineModeLabel,
  createLeg,
  defaultEnsembleParams,
  parseEnsembleLegs,
  parseEnsembleParams,
  removeLeg,
} from '../utils/ensembleConfig';

const catalog: StrategyCatalogItem[] = [
  {
    id: 'sma_crossover',
    label: 'SMA Crossover',
    description: '',
    params: { fast_period: 20, slow_period: 50 },
    constraints: {},
    ensemble_eligible: true,
  },
  {
    id: 'rsi_reversion',
    label: 'RSI Mean Reversion',
    description: '',
    params: { period: 14, oversold: 30, overbought: 70 },
    constraints: {},
    ensemble_eligible: true,
  },
  {
    id: ENSEMBLE_STRATEGY_ID,
    label: 'Strategy Ensemble',
    description: '',
    params: {
      combine_mode: 'majority',
      threshold: 0.5,
      legs: [
        { strategy_id: 'sma_crossover', params: { fast_period: 20, slow_period: 50 }, weight: 1 },
        { strategy_id: 'rsi_reversion', params: { period: 14, oversold: 30, overbought: 70 }, weight: 1 },
      ],
    },
    constraints: {},
    ensemble_eligible: false,
  },
];

describe('ensembleConfig', () => {
  it('builds default ensemble params from catalog', () => {
    const params = defaultEnsembleParams(catalog);
    expect(params.combine_mode).toBe('majority');
    expect(params.legs).toHaveLength(2);
  });

  it('parses nested ensemble params for API payload', () => {
    const params = parseEnsembleParams(catalog.find((item) => item.id === ENSEMBLE_STRATEGY_ID)?.params);
    expect(params.legs[0].strategy_id).toBe('sma_crossover');
    expect(params.threshold).toBe(0.5);
  });

  it('enforces leg add/remove limits', () => {
    const base = defaultEnsembleParams(catalog);
    expect(canRemoveLeg(base.legs)).toBe(false);
    const withThree = addLeg(base, catalog);
    expect(withThree.legs).toHaveLength(3);
    expect(canRemoveLeg(withThree.legs)).toBe(true);
    const withFive = [0, 1].reduce((current) => addLeg(current, catalog), withThree);
    expect(withFive.legs).toHaveLength(5);
    expect(canAddLeg(withFive.legs)).toBe(false);
    const removed = removeLeg(withFive, 0);
    expect(removed.legs).toHaveLength(4);
  });

  it('does not remove below minimum legs', () => {
    const base = defaultEnsembleParams(catalog);
    expect(removeLeg(base, 0).legs).toHaveLength(2);
    expect(canRemoveLeg(base.legs)).toBe(false);
    const oneLeg = { ...base, legs: [base.legs[0]] };
    expect(canRemoveLeg(oneLeg.legs)).toBe(false);
  });

  it('extracts legs from results params', () => {
    const legs = parseEnsembleLegs({
      combine_mode: 'weighted',
      threshold: 0.6,
      legs: defaultEnsembleParams(catalog).legs,
    });
    expect(legs).toHaveLength(2);
  });

  it('labels combine modes', () => {
    expect(combineModeLabel('majority')).toBe('Majority');
  });

  it('stores leg signal timeframe when provided', () => {
    const leg = createLeg('rsi_reversion', { period: 14, oversold: 30, overbought: 70 }, '30m');
    expect(leg.signal_timeframe).toBe('30m');
  });

  it('adds legs with decision timeframe default', () => {
    const base = defaultEnsembleParams(catalog);
    const next = addLeg(base, catalog, '15m');
    expect(next.legs.at(-1)?.signal_timeframe).toBe('15m');
  });

  it('parses leg signal timeframe from params', () => {
    const legs = parseEnsembleLegs({
      combine_mode: 'majority',
      threshold: 0.5,
      legs: [
        {
          strategy_id: 'rsi_reversion',
          signal_timeframe: '30m',
          params: { period: 14, oversold: 30, overbought: 70 },
          weight: 1,
        },
      ],
    });
    expect(legs[0].signal_timeframe).toBe('30m');
  });
});
