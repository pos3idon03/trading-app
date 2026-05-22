import type { EnsembleParams, StrategyCatalogItem } from '../../api/backtestTypes';
import { OHLCV_TIMEFRAMES } from '../../constants/timeframes';
import {
  addLeg,
  canAddLeg,
  canRemoveLeg,
  createLeg,
  removeLeg,
} from '../../utils/ensembleConfig';
import { strategyTrendTitle } from '../../utils/backtestStrategyTrend';
import { effectiveSignalTimeframe } from '../../utils/multitimeframeBacktest';

interface EnsembleConfigFormProps {
  value: EnsembleParams;
  onChange: (value: EnsembleParams) => void;
  legStrategies: StrategyCatalogItem[];
  decisionTimeframe: string;
}

export default function EnsembleConfigForm({
  value,
  onChange,
  legStrategies,
  decisionTimeframe,
}: EnsembleConfigFormProps) {
  const updateLeg = (index: number, nextLeg: EnsembleParams['legs'][number]) => {
    onChange({
      ...value,
      legs: value.legs.map((leg, legIndex) => (legIndex === index ? nextLeg : leg)),
    });
  };

  const handleStrategyChange = (index: number, strategyId: string) => {
    const strategy = legStrategies.find((item) => item.id === strategyId);
    if (!strategy) return;
    const current = value.legs[index];
    updateLeg(
      index,
      createLeg(
        strategyId,
        strategy.params as Record<string, number>,
        current?.signal_timeframe ?? decisionTimeframe,
      ),
    );
  };

  return (
    <div className="space-y-4 md:col-span-2 xl:col-span-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <label className="space-y-1 text-sm">
          <span className="text-slate-400">Combine mode</span>
          <select
            value={value.combine_mode}
            onChange={(e) =>
              onChange({
                ...value,
                combine_mode: e.target.value as EnsembleParams['combine_mode'],
              })
            }
            className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
          >
            <option value="unanimous">Unanimous</option>
            <option value="majority">Majority</option>
            <option value="weighted">Weighted</option>
          </select>
        </label>

        {value.combine_mode === 'weighted' && (
          <label className="space-y-1 text-sm">
            <span className="text-slate-400">Threshold</span>
            <input
              type="number"
              value={value.threshold}
              min={0.1}
              max={1}
              step={0.05}
              onChange={(e) =>
                onChange({
                  ...value,
                  threshold: Number(e.target.value),
                })
              }
              className="w-full bg-surface-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
            />
          </label>
        )}
      </div>

      <div className="space-y-3">
        {value.legs.map((leg, index) => {
          const strategy = legStrategies.find((item) => item.id === leg.strategy_id);
          const legSignalTimeframe = effectiveSignalTimeframe(leg.signal_timeframe, decisionTimeframe);
          return (
            <div
              key={`${index}-${leg.strategy_id}`}
              className="rounded-lg border border-slate-800 bg-surface-950 p-4 space-y-3"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h4 className="text-sm font-medium text-slate-200">Leg {index + 1}</h4>
                {canRemoveLeg(value.legs) && (
                  <button
                    type="button"
                    onClick={() => onChange(removeLeg(value, index))}
                    className="text-xs text-red-400 hover:text-red-300"
                  >
                    Remove
                  </button>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                <label className="space-y-1 text-sm">
                  <span className="text-slate-400">Strategy</span>
                  <select
                    value={leg.strategy_id}
                    onChange={(e) => handleStrategyChange(index, e.target.value)}
                    className="w-full bg-surface-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
                  >
                    {legStrategies.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="space-y-1 text-sm">
                  <span className="text-slate-400">Signal timeframe</span>
                  <select
                    value={legSignalTimeframe}
                    onChange={(e) =>
                      updateLeg(index, {
                        ...leg,
                        signal_timeframe: e.target.value,
                      })
                    }
                    className="w-full bg-surface-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
                  >
                    {OHLCV_TIMEFRAMES.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="space-y-1 text-sm">
                  <span className="text-slate-400">Weight</span>
                  <input
                    type="number"
                    value={leg.weight}
                    min={0.1}
                    step={0.1}
                    onChange={(e) =>
                      updateLeg(index, {
                        ...leg,
                        weight: Number(e.target.value),
                      })
                    }
                    className="w-full bg-surface-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
                  />
                </label>

                {strategy &&
                  Object.entries(strategy.params as Record<string, number>).map(([key, defaultValue]) => {
                    const constraint = strategy.constraints[key];
                    return (
                      <label key={key} className="space-y-1 text-sm">
                        <span className="text-slate-400">{key.replace(/_/g, ' ')}</span>
                        <input
                          type="number"
                          value={leg.params[key] ?? defaultValue}
                          min={constraint?.min}
                          max={constraint?.max}
                          onChange={(e) =>
                            updateLeg(index, {
                              ...leg,
                              params: {
                                ...leg.params,
                                [key]: Number(e.target.value),
                              },
                            })
                          }
                          className="w-full bg-surface-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
                        />
                      </label>
                    );
                  })}
              </div>

              <p className="text-xs text-slate-500">
                Trend preview ({legSignalTimeframe}): {strategyTrendTitle(leg.strategy_id, leg.params)}
              </p>
            </div>
          );
        })}
      </div>

      {canAddLeg(value.legs) && (
        <button
          type="button"
          onClick={() => onChange(addLeg(value, legStrategies, decisionTimeframe))}
          className="px-3 py-2 rounded-lg text-sm border border-slate-700 text-slate-200 hover:border-slate-500"
        >
          Add leg
        </button>
      )}
    </div>
  );
}
