/**
 * Client-side signal evaluation for auto-trading execution monitoring.
 * Mirrors the combination_mode logic applied server-side for order execution.
 */
import type {
  AlgoStrategySummary,
  AttachedAlgoSignal,
  AutoTradingAssetRow,
  ComboGroupSignal,
  CriteriaSignal,
  CriterionEvaluation,
  LiveStrategySignalItem,
} from '../api/types';

// ---------------------------------------------------------------------------
// Single-criterion evaluation
// ---------------------------------------------------------------------------

export function evaluateCriterion(
  value: number | null,
  buyThreshold: number | null,
  sellThreshold: number | null,
): CriteriaSignal {
  if (value == null) return 'NEUTRAL';
  if (buyThreshold != null && value >= buyThreshold) return 'BUY';
  if (sellThreshold != null && value <= sellThreshold) return 'SELL';
  return 'NEUTRAL';
}

// ---------------------------------------------------------------------------
// Build criteria evaluations from AutoTradingAssetRow
// ---------------------------------------------------------------------------

export function buildCriteriaEvaluations(
  asset: AutoTradingAssetRow,
): CriterionEvaluation[] {
  return [
    {
      label: 'MC Prob+',
      value: asset.mc_prob_positive,
      buyThreshold: asset.mc_buy_prob_positive,
      sellThreshold: asset.mc_sell_prob_positive,
      signal: evaluateCriterion(
        asset.mc_prob_positive,
        asset.mc_buy_prob_positive,
        asset.mc_sell_prob_positive,
      ),
    },
    {
      label: 'AI Conviction',
      value: asset.ai_conviction,
      buyThreshold: asset.ai_buy_conviction,
      sellThreshold: asset.ai_sell_conviction,
      signal: evaluateCriterion(
        asset.ai_conviction,
        asset.ai_buy_conviction,
        asset.ai_sell_conviction,
      ),
    },
    {
      label: 'AI Sentiment',
      value: asset.ai_sentiment,
      buyThreshold: asset.ai_buy_sentiment,
      sellThreshold: asset.ai_sell_sentiment,
      signal: evaluateCriterion(
        asset.ai_sentiment,
        asset.ai_buy_sentiment,
        asset.ai_sell_sentiment,
      ),
    },
    {
      label: 'AI Macro',
      value: asset.ai_macro,
      buyThreshold: asset.ai_buy_macro,
      sellThreshold: asset.ai_sell_macro,
      signal: evaluateCriterion(
        asset.ai_macro,
        asset.ai_buy_macro,
        asset.ai_sell_macro,
      ),
    },
  ];
}

// ---------------------------------------------------------------------------
// Combine individual signals using the configured combination mode.
// Algo strategy signals are treated as one vote each (same weight as criteria).
// ---------------------------------------------------------------------------

export function combineSignals(
  criteria: CriterionEvaluation[],
  algoSignals: AttachedAlgoSignal[],
  mode: 'all' | 'majority' | 'any',
): CriteriaSignal {
  const allSignals: CriteriaSignal[] = [
    ...criteria.map((c) => c.signal),
    ...algoSignals.map((a) => a.signal as CriteriaSignal),
  ];

  const active = allSignals.filter((s) => s !== 'NEUTRAL');
  if (active.length === 0) return 'NEUTRAL';

  const buys = active.filter((s) => s === 'BUY').length;
  const sells = active.filter((s) => s === 'SELL').length;
  const total = allSignals.length;

  if (mode === 'all') {
    if (buys === total) return 'BUY';
    if (sells === total) return 'SELL';
    return 'NEUTRAL';
  }

  if (mode === 'majority') {
    if (buys > total / 2) return 'BUY';
    if (sells > total / 2) return 'SELL';
    return 'NEUTRAL';
  }

  // 'any'
  if (buys > 0) return 'BUY';
  if (sells > 0) return 'SELL';
  return 'NEUTRAL';
}

// ---------------------------------------------------------------------------
// Combo strategy expansion
// ---------------------------------------------------------------------------

interface ComboParams {
  combination_mode: string;
  strategies: { strategy_name: string }[];
}

function parseComboParams(params: Record<string, unknown> | null): ComboParams | null {
  if (!params) return null;
  const mode = params['combination_mode'];
  const strategies = params['strategies'];
  if (typeof mode !== 'string' || !Array.isArray(strategies)) return null;
  return { combination_mode: mode, strategies };
}

/**
 * Given the list of attached algo summaries and the live per-strategy signal items,
 * returns the expanded flat list of individual signals (with comboGroup set for
 * strategies that belong to a combo) and a list of per-combo combined signals.
 *
 * The map value is the full LiveStrategySignalItem so indicator data can be
 * forwarded into each AttachedAlgoSignal row.
 */
export function expandAlgoSignals(
  algoSummaries: AlgoStrategySummary[],
  liveByStrategy: Map<string, LiveStrategySignalItem>,
): { algoSignals: AttachedAlgoSignal[]; comboSignals: ComboGroupSignal[] } {
  const algoSignals: AttachedAlgoSignal[] = [];
  const comboSignals: ComboGroupSignal[] = [];

  for (const summary of algoSummaries) {
    const isCombo = summary.strategy_name.startsWith('combo:');

    if (isCombo) {
      const comboParams = parseComboParams(summary.params);
      if (comboParams) {
        const childSignals: AttachedAlgoSignal[] = comboParams.strategies.map((s) => {
          const live = liveByStrategy.get(s.strategy_name);
          return {
            strategy: s.strategy_name,
            label: s.strategy_name,
            signal: live?.signal ?? 'NEUTRAL',
            comboGroup: summary.strategy_name,
            indicatorValue: live?.indicator_value ?? null,
            indicatorLabel: live?.indicator_label ?? null,
            params: live?.params ?? null,
          };
        });
        algoSignals.push(...childSignals);

        const comboSignal = computeComboModeSignal(
          childSignals.map((c) => c.signal),
          comboParams.combination_mode,
        );
        comboSignals.push({
          comboName: summary.strategy_name,
          combinationMode: comboParams.combination_mode,
          signal: comboSignal,
        });
      } else {
        // Params missing — show the combo row as-is with NEUTRAL
        algoSignals.push({
          strategy: summary.strategy_name,
          label: summary.strategy_name,
          signal: 'NEUTRAL',
        });
      }
    } else {
      const live = liveByStrategy.get(summary.strategy_name);
      algoSignals.push({
        strategy: summary.strategy_name,
        label: summary.strategy_name,
        signal: live?.signal ?? 'NEUTRAL',
        indicatorValue: live?.indicator_value ?? null,
        indicatorLabel: live?.indicator_label ?? null,
        params: live?.params ?? null,
      });
    }
  }

  return { algoSignals, comboSignals };
}

/**
 * Apply a combination mode to a list of raw signals.
 * Mirrors the combo_runner logic from the backend.
 */
function computeComboModeSignal(
  signals: ('BUY' | 'SELL' | 'NEUTRAL')[],
  mode: string,
): CriteriaSignal {
  const total = signals.length;
  if (total === 0) return 'NEUTRAL';

  const buys = signals.filter((s) => s === 'BUY').length;
  const sells = signals.filter((s) => s === 'SELL').length;

  if (mode === 'and' || mode === 'all') {
    if (buys === total) return 'BUY';
    if (sells === total) return 'SELL';
    return 'NEUTRAL';
  }

  if (mode === 'majority') {
    if (buys > total / 2) return 'BUY';
    if (sells > total / 2) return 'SELL';
    return 'NEUTRAL';
  }

  // 'any' / 'or' / weighted fallback
  if (buys > 0) return 'BUY';
  if (sells > 0) return 'SELL';
  return 'NEUTRAL';
}

// ---------------------------------------------------------------------------
// Convert algo_timeframe string to milliseconds for polling interval
// ---------------------------------------------------------------------------

const TIMEFRAME_MS: Record<string, number> = {
  '1m': 60_000,
  '5m': 300_000,
  '15m': 900_000,
  '30m': 1_800_000,
  '1h': 3_600_000,
  '3h': 10_800_000,
  '1d': 86_400_000,
  '1w': 604_800_000,
};

export function timeframeToMs(tf: string): number {
  return TIMEFRAME_MS[tf] ?? 300_000;
}
