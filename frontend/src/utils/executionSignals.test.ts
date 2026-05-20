import { describe, it, expect } from 'vitest';
import {
  evaluateCriterion,
  buildCriteriaEvaluations,
  collectUniqueAlgoTimeframes,
  strategyNamesForTimeframe,
  combineSignals,
  expandAlgoSignals,
  timeframeToMs,
} from './executionSignals';
import type {
  AlgoStrategySummary,
  AutoTradingAssetRow,
  AttachedAlgoSignal,
  ComboGroupSignal,
  CriterionEvaluation,
  LiveStrategySignalItem,
} from '../api/types';

// Helper to build a minimal LiveStrategySignalItem for tests
const makeLiveItem = (
  strategy: string,
  signal: 'BUY' | 'SELL' | 'NEUTRAL',
  overrides: Partial<LiveStrategySignalItem> = {},
): LiveStrategySignalItem => ({
  strategy,
  label: strategy,
  group: 'Test',
  signal,
  indicator_value: null,
  indicator_label: null,
  params: null,
  ...overrides,
});

// ---------------------------------------------------------------------------
// evaluateCriterion
// ---------------------------------------------------------------------------

describe('evaluateCriterion', () => {
  it('returns NEUTRAL when value is null', () => {
    expect(evaluateCriterion(null, 0.5, 0.3)).toBe('NEUTRAL');
  });

  it('returns BUY when value meets buy threshold', () => {
    expect(evaluateCriterion(0.7, 0.65, 0.4)).toBe('BUY');
  });

  it('returns BUY when value equals buy threshold (inclusive)', () => {
    expect(evaluateCriterion(0.65, 0.65, 0.4)).toBe('BUY');
  });

  it('returns SELL when value meets sell threshold', () => {
    expect(evaluateCriterion(0.3, 0.65, 0.4)).toBe('SELL');
  });

  it('returns SELL when value equals sell threshold (inclusive)', () => {
    expect(evaluateCriterion(0.4, 0.65, 0.4)).toBe('SELL');
  });

  it('returns NEUTRAL when value is between thresholds', () => {
    expect(evaluateCriterion(0.55, 0.65, 0.4)).toBe('NEUTRAL');
  });

  it('returns NEUTRAL when no thresholds are set', () => {
    expect(evaluateCriterion(0.9, null, null)).toBe('NEUTRAL');
  });

  it('returns BUY when only buy threshold is set and value qualifies', () => {
    expect(evaluateCriterion(0.8, 0.6, null)).toBe('BUY');
  });

  it('returns SELL when only sell threshold is set and value qualifies', () => {
    expect(evaluateCriterion(0.1, null, 0.3)).toBe('SELL');
  });
});

// ---------------------------------------------------------------------------
// buildCriteriaEvaluations
// ---------------------------------------------------------------------------

const baseAsset: AutoTradingAssetRow = {
  strategy_id: 1,
  asset_id: 10,
  symbol: 'AAPL',
  asset_name: 'Apple Inc.',
  mc_prob_positive: 0.72,
  mc_buy_prob_positive: 0.65,
  mc_sell_prob_positive: 0.4,
  ai_conviction: 0.85,
  ai_buy_conviction: 0.7,
  ai_sell_conviction: 0.3,
  ai_sentiment: 0.4,
  ai_buy_sentiment: 0.2,
  ai_sell_sentiment: -0.1,
  ai_macro: 0.3,
  ai_buy_macro: 0.1,
  ai_sell_macro: -0.2,
  combination_mode: 'all',
  algo_timeframe: '5m',
  auto_trading_started: true,
  max_amount_per_position: null,
  max_pct_of_capital: null,
};

describe('buildCriteriaEvaluations', () => {
  it('returns four criteria items', () => {
    const result = buildCriteriaEvaluations(baseAsset);
    expect(result).toHaveLength(4);
  });

  it('labels criteria correctly', () => {
    const labels = buildCriteriaEvaluations(baseAsset).map((c) => c.label);
    expect(labels).toEqual(['MC Prob+', 'AI Conviction', 'AI Sentiment', 'AI Macro']);
  });

  it('evaluates BUY signal for mc_prob_positive above threshold', () => {
    const result = buildCriteriaEvaluations(baseAsset);
    expect(result[0].signal).toBe('BUY');
  });

  it('evaluates BUY for conviction above threshold', () => {
    const result = buildCriteriaEvaluations(baseAsset);
    expect(result[1].signal).toBe('BUY');
  });

  it('handles null values gracefully', () => {
    const asset: AutoTradingAssetRow = { ...baseAsset, mc_prob_positive: null };
    const result = buildCriteriaEvaluations(asset);
    expect(result[0].signal).toBe('NEUTRAL');
    expect(result[0].value).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// combineSignals
// ---------------------------------------------------------------------------

const makeCriteria = (signals: ('BUY' | 'SELL' | 'NEUTRAL')[]): CriterionEvaluation[] =>
  signals.map((signal, i) => ({
    label: `C${i}`,
    value: 0.5,
    buyThreshold: null,
    sellThreshold: null,
    signal,
  }));

const noAlgos: AttachedAlgoSignal[] = [];
const noCombos: ComboGroupSignal[] = [];

describe('combineSignals – mode: all', () => {
  it('returns BUY only when all signals are BUY', () => {
    const criteria = makeCriteria(['BUY', 'BUY', 'BUY']);
    expect(combineSignals(criteria, noAlgos, noCombos, 'all')).toBe('BUY');
  });

  it('returns SELL only when all signals are SELL', () => {
    const criteria = makeCriteria(['SELL', 'SELL', 'SELL']);
    expect(combineSignals(criteria, noAlgos, noCombos, 'all')).toBe('SELL');
  });

  it('returns NEUTRAL when signals are mixed', () => {
    const criteria = makeCriteria(['BUY', 'SELL', 'NEUTRAL']);
    expect(combineSignals(criteria, noAlgos, noCombos, 'all')).toBe('NEUTRAL');
  });

  it('returns NEUTRAL when one BUY and rest NEUTRAL', () => {
    const criteria = makeCriteria(['BUY', 'NEUTRAL', 'NEUTRAL']);
    expect(combineSignals(criteria, noAlgos, noCombos, 'all')).toBe('NEUTRAL');
  });
});

describe('combineSignals – mode: majority', () => {
  it('returns BUY when majority are BUY', () => {
    const criteria = makeCriteria(['BUY', 'BUY', 'SELL']);
    expect(combineSignals(criteria, noAlgos, noCombos, 'majority')).toBe('BUY');
  });

  it('returns SELL when majority are SELL', () => {
    const criteria = makeCriteria(['SELL', 'SELL', 'BUY']);
    expect(combineSignals(criteria, noAlgos, noCombos, 'majority')).toBe('SELL');
  });

  it('returns NEUTRAL when no majority', () => {
    const criteria = makeCriteria(['BUY', 'SELL', 'NEUTRAL', 'NEUTRAL']);
    expect(combineSignals(criteria, noAlgos, noCombos, 'majority')).toBe('NEUTRAL');
  });

  it('returns NEUTRAL when criteria split and combo vote is NEUTRAL', () => {
    const criteria = makeCriteria(['BUY', 'SELL', 'NEUTRAL', 'NEUTRAL']);
    const combos: ComboGroupSignal[] = [
      { comboName: 'combo:and', combinationMode: 'and', signal: 'NEUTRAL' },
    ];
    expect(combineSignals(criteria, noAlgos, combos, 'majority')).toBe('NEUTRAL');
  });

  it('matches server: 3 criteria BUY + combo NEUTRAL is still majority BUY', () => {
    const criteria = makeCriteria(['BUY', 'BUY', 'BUY', 'SELL']);
    const combos: ComboGroupSignal[] = [
      { comboName: 'combo:and', combinationMode: 'and', signal: 'NEUTRAL' },
    ];
    expect(combineSignals(criteria, noAlgos, combos, 'majority')).toBe('BUY');
  });
});

describe('combineSignals – mode: any', () => {
  it('returns BUY when at least one signal is BUY', () => {
    const criteria = makeCriteria(['NEUTRAL', 'NEUTRAL', 'BUY']);
    expect(combineSignals(criteria, noAlgos, noCombos, 'any')).toBe('BUY');
  });

  it('returns SELL when at least one signal is SELL (no BUY)', () => {
    const criteria = makeCriteria(['NEUTRAL', 'SELL', 'NEUTRAL']);
    expect(combineSignals(criteria, noAlgos, noCombos, 'any')).toBe('SELL');
  });

  it('returns NEUTRAL when all are NEUTRAL', () => {
    const criteria = makeCriteria(['NEUTRAL', 'NEUTRAL', 'NEUTRAL']);
    expect(combineSignals(criteria, noAlgos, noCombos, 'any')).toBe('NEUTRAL');
  });

  it('returns SELL when BUY and SELL conflict (sell-first)', () => {
    const criteria = makeCriteria(['BUY', 'SELL']);
    expect(combineSignals(criteria, noAlgos, noCombos, 'any')).toBe('SELL');
  });
});

describe('combineSignals – with algo signals', () => {
  it('includes standalone algo signals as votes', () => {
    const criteria = makeCriteria(['BUY', 'BUY', 'NEUTRAL']);
    const algos: AttachedAlgoSignal[] = [
      { strategy: 'rsi', label: 'RSI', signal: 'BUY' },
      { strategy: 'macd', label: 'MACD', signal: 'NEUTRAL' },
    ];
    expect(combineSignals(criteria, algos, noCombos, 'all')).toBe('NEUTRAL');
    expect(combineSignals(criteria, algos, noCombos, 'majority')).toBe('BUY');
  });

  it('does not double-count combo legs when combo vote is provided', () => {
    const criteria = makeCriteria(['BUY', 'SELL', 'NEUTRAL', 'NEUTRAL']);
    const algos: AttachedAlgoSignal[] = [
      { strategy: 'ema_cross', label: 'EMA', signal: 'BUY', comboGroup: 'combo:and' },
      { strategy: 'range_breakout', label: 'Range', signal: 'BUY', comboGroup: 'combo:and' },
    ];
    const combos: ComboGroupSignal[] = [
      { comboName: 'combo:and', combinationMode: 'and', signal: 'NEUTRAL' },
    ];
    // Legs alone would be 2 BUY; with combo NEUTRAL vote → 2 BUY / 5 → NEUTRAL
    expect(combineSignals(criteria, algos, combos, 'majority')).toBe('NEUTRAL');
  });
});

// ---------------------------------------------------------------------------
// expandAlgoSignals
// ---------------------------------------------------------------------------

const makeAlgoSummary = (overrides: Partial<AlgoStrategySummary>): AlgoStrategySummary => ({
  algo_attachment_id: 1,
  strategy_name: 'rsi',
  params: null,
  timeframe: '1d',
  added_at: '2026-01-01T00:00:00Z',
  ...overrides,
});

describe('strategyNamesForTimeframe', () => {
  it('returns standalone and combo leg names for a timeframe', () => {
    const summaries = [
      makeAlgoSummary({ strategy_name: 'atr_trailing_stop', timeframe: '15m' }),
      makeAlgoSummary({
        strategy_name: 'combo:majority',
        timeframe: '1h',
        params: {
          combination_mode: 'majority',
          strategies: [
            { strategy_name: 'rsi', timeframe: '1h' },
            { strategy_name: 'macd', timeframe: '15m' },
          ],
        },
      }),
    ];
    expect(strategyNamesForTimeframe(summaries, '15m').sort()).toEqual(
      ['atr_trailing_stop', 'macd'].sort(),
    );
    expect(strategyNamesForTimeframe(summaries, '1h')).toEqual(['rsi']);
  });
});

describe('collectUniqueAlgoTimeframes', () => {
  it('collects standalone and combo leg timeframes', () => {
    const summaries = [
      makeAlgoSummary({ strategy_name: 'rsi', timeframe: '4h' }),
      makeAlgoSummary({
        strategy_name: 'combo:majority',
        timeframe: '1h',
        params: {
          combination_mode: 'majority',
          strategies: [
            { strategy_name: 'atr_trailing_stop', timeframe: '30m' },
            { strategy_name: 'macd' },
          ],
        },
      }),
    ];
    const tfs = collectUniqueAlgoTimeframes(summaries);
    expect(tfs).toContain('4h');
    expect(tfs).toContain('1h');
    expect(tfs).toContain('30m');
  });
});

describe('expandAlgoSignals – standalone strategy', () => {
  it('returns a single signal with live value for a non-combo strategy', () => {
    const summaries = [makeAlgoSummary({ strategy_name: 'rsi' })];
    const liveMap = new Map([['rsi', makeLiveItem('rsi', 'BUY')]]);
    const { algoSignals, comboSignals } = expandAlgoSignals(summaries, liveMap);
    expect(algoSignals).toHaveLength(1);
    expect(algoSignals[0].strategy).toBe('rsi');
    expect(algoSignals[0].signal).toBe('BUY');
    expect(algoSignals[0].comboGroup).toBeUndefined();
    expect(comboSignals).toHaveLength(0);
  });

  it('falls back to NEUTRAL when no live signal is available', () => {
    const summaries = [makeAlgoSummary({ strategy_name: 'macd' })];
    const { algoSignals } = expandAlgoSignals(summaries, new Map());
    expect(algoSignals[0].signal).toBe('NEUTRAL');
  });

  it('propagates indicator_value and indicator_label to the algo signal', () => {
    const summaries = [makeAlgoSummary({ strategy_name: 'rsi' })];
    const liveMap = new Map([
      ['rsi', makeLiveItem('rsi', 'NEUTRAL', { indicator_value: 45.2, indicator_label: 'RSI', params: { period: 14, overbought: 70, oversold: 30 } })],
    ]);
    const { algoSignals } = expandAlgoSignals(summaries, liveMap);
    expect(algoSignals[0].indicatorValue).toBe(45.2);
    expect(algoSignals[0].indicatorLabel).toBe('RSI');
    expect(algoSignals[0].params).toEqual({ period: 14, overbought: 70, oversold: 30 });
  });
});

describe('expandAlgoSignals – combo strategy', () => {
  const comboSummary = makeAlgoSummary({
    strategy_name: 'combo:majority',
    params: {
      combination_mode: 'majority',
      strategies: [
        { strategy_name: 'ma_crossover' },
        { strategy_name: 'rsi' },
        { strategy_name: 'macd' },
      ],
    },
  });

  it('expands combo into individual constituent signals', () => {
    const liveMap = new Map([
      ['ma_crossover', makeLiveItem('ma_crossover', 'BUY')],
      ['rsi', makeLiveItem('rsi', 'BUY')],
      ['macd', makeLiveItem('macd', 'SELL')],
    ]);
    const { algoSignals } = expandAlgoSignals([comboSummary], liveMap);
    expect(algoSignals).toHaveLength(3);
    expect(algoSignals.map((s) => s.strategy)).toEqual(['ma_crossover', 'rsi', 'macd']);
  });

  it('tags each constituent with the combo group name', () => {
    const { algoSignals } = expandAlgoSignals([comboSummary], new Map());
    for (const s of algoSignals) {
      expect(s.comboGroup).toBe('combo:majority');
    }
  });

  it('computes the correct combo aggregate signal', () => {
    // 2 BUY, 1 SELL → majority → BUY
    const liveMap = new Map([
      ['ma_crossover', makeLiveItem('ma_crossover', 'BUY')],
      ['rsi', makeLiveItem('rsi', 'BUY')],
      ['macd', makeLiveItem('macd', 'SELL')],
    ]);
    const { comboSignals } = expandAlgoSignals([comboSummary], liveMap);
    expect(comboSignals).toHaveLength(1);
    expect(comboSignals[0].comboName).toBe('combo:majority');
    expect(comboSignals[0].signal).toBe('BUY');
  });

  it('or mode: sell-first when legs disagree', () => {
    const orCombo = makeAlgoSummary({
      strategy_name: 'combo:or',
      params: {
        combination_mode: 'or',
        strategies: [
          { strategy_name: 'orb' },
          { strategy_name: 'ema_cross' },
        ],
      },
    });
    const liveMap = new Map([
      ['orb', makeLiveItem('orb', 'BUY')],
      ['ema_cross', makeLiveItem('ema_cross', 'SELL')],
    ]);
    const { comboSignals } = expandAlgoSignals([orCombo], liveMap);
    expect(comboSignals[0].signal).toBe('SELL');
  });

  it('propagates indicator data to combo children', () => {
    const liveMap = new Map([
      ['ma_crossover', makeLiveItem('ma_crossover', 'BUY', { indicator_value: 0.5, indicator_label: 'Fast − Slow MA' })],
      ['rsi', makeLiveItem('rsi', 'NEUTRAL', { indicator_value: 52.3, indicator_label: 'RSI' })],
      ['macd', makeLiveItem('macd', 'NEUTRAL')],
    ]);
    const { algoSignals } = expandAlgoSignals([comboSummary], liveMap);
    expect(algoSignals[0].indicatorValue).toBe(0.5);
    expect(algoSignals[0].indicatorLabel).toBe('Fast − Slow MA');
    expect(algoSignals[1].indicatorValue).toBe(52.3);
    expect(algoSignals[2].indicatorValue).toBeNull();
  });

  it('falls back to NEUTRAL for constituents with no live signal', () => {
    const { algoSignals } = expandAlgoSignals([comboSummary], new Map());
    for (const s of algoSignals) {
      expect(s.signal).toBe('NEUTRAL');
    }
  });

  it('returns NEUTRAL combo signal when all constituents are NEUTRAL', () => {
    const { comboSignals } = expandAlgoSignals([comboSummary], new Map());
    expect(comboSignals[0].signal).toBe('NEUTRAL');
  });

  it('handles missing params gracefully — shows combo row as NEUTRAL', () => {
    const noParams = makeAlgoSummary({ strategy_name: 'combo:and', params: null });
    const { algoSignals, comboSignals } = expandAlgoSignals([noParams], new Map());
    expect(algoSignals).toHaveLength(1);
    expect(algoSignals[0].signal).toBe('NEUTRAL');
    expect(algoSignals[0].comboGroup).toBeUndefined();
    expect(comboSignals).toHaveLength(0);
  });
});

describe('expandAlgoSignals – mixed standalone and combo', () => {
  it('returns signals from both standalone and combo in order', () => {
    const standalone = makeAlgoSummary({ strategy_name: 'vrp_harvest', params: null });
    const combo = makeAlgoSummary({
      strategy_name: 'combo:all',
      params: {
        combination_mode: 'all',
        strategies: [{ strategy_name: 'rsi' }, { strategy_name: 'macd' }],
      },
    });
    const liveMap = new Map([
      ['vrp_harvest', makeLiveItem('vrp_harvest', 'SELL')],
      ['rsi', makeLiveItem('rsi', 'BUY')],
      ['macd', makeLiveItem('macd', 'BUY')],
    ]);
    const { algoSignals, comboSignals } = expandAlgoSignals([standalone, combo], liveMap);
    expect(algoSignals).toHaveLength(3); // 1 standalone + 2 combo children
    expect(algoSignals[0].strategy).toBe('vrp_harvest');
    expect(algoSignals[0].comboGroup).toBeUndefined();
    expect(algoSignals[1].comboGroup).toBe('combo:all');
    expect(comboSignals[0].signal).toBe('BUY'); // all agree on BUY
  });
});

// ---------------------------------------------------------------------------
// timeframeToMs
// ---------------------------------------------------------------------------

describe('timeframeToMs', () => {
  it('converts known timeframes correctly', () => {
    expect(timeframeToMs('1m')).toBe(60_000);
    expect(timeframeToMs('5m')).toBe(300_000);
    expect(timeframeToMs('1h')).toBe(3_600_000);
    expect(timeframeToMs('1d')).toBe(86_400_000);
  });

  it('falls back to 5m for unknown timeframe', () => {
    expect(timeframeToMs('unknown')).toBe(300_000);
  });
});
