import { useState } from 'react';
import type { AttachedAlgoSignal, ComboGroupSignal, CriteriaSignal, CriterionEvaluation, ExecutionAssetMonitor, OrderItem } from '../api/types';
import { TRANSACTIONS_PAGE_SIZE } from '../hooks/useExecutionMonitor';
import {
  attachedSignalsToTimelineStrategies,
  ComboSignalTimeline,
  isIntradayTimeframe,
} from './ComboSignalTimeline';
import { STRATEGIES } from '../constants/strategies';

function resolveStrategyLabel(strategyName: string): string {
  return STRATEGIES.find((s) => s.value === strategyName)?.label ?? strategyName;
}

// ---------------------------------------------------------------------------
// Indicator formatting helpers
// ---------------------------------------------------------------------------

function fmtIndicatorValue(value: number | null | undefined, label: string | null | undefined): string {
  if (value == null || label == null) return '';
  // Use up to 4 decimal places but strip trailing zeros (e.g. 45.2 not 45.2000)
  const formatted = Number(value.toFixed(4)).toString();
  return `${label}: ${formatted}`;
}

function formatThresholdHint(strategy: string, params: Record<string, unknown> | null | undefined): string {
  if (!params) return '';

  const p = (key: string, fallback: number) => {
    const v = params[key];
    return typeof v === 'number' ? v : fallback;
  };

  switch (strategy) {
    case 'rsi':
    case 'lrsi':
    case 'reverting_market': {
      const ob = p(strategy === 'lrsi' ? 'overbought' : 'overbought', strategy === 'lrsi' ? 0.8 : 70);
      const os = p(strategy === 'lrsi' ? 'oversold' : 'oversold', strategy === 'lrsi' ? 0.2 : 30);
      return `buy ≥ ${os} / sell ≤ ${ob}`;
    }
    case 'stoch_rsi': {
      const ob = p('overbought', 0.8);
      const os = p('oversold', 0.2);
      return `buy ≥ ${os} / sell ≤ ${ob}`;
    }
    case 'macd':
      return 'buy: MACD > Signal / sell: MACD < Signal';
    case 'ma_crossover':
    case 'sma_cross': {
      const fast = p('fast_window', strategy === 'sma_cross' ? 50 : 10);
      const slow = p('slow_window', strategy === 'sma_cross' ? 200 : 50);
      return `buy: MA(${fast}) > MA(${slow}) / sell: MA(${fast}) < MA(${slow})`;
    }
    case 'ema_cross': {
      const fast = p('fast_span', 12);
      const slow = p('slow_span', 26);
      return `buy: EMA(${fast}) > EMA(${slow}) / sell: EMA(${fast}) < EMA(${slow})`;
    }
    case 'sma_break': {
      const w = p('sma_window', 200);
      return `buy: price > SMA(${w}) / sell: price < SMA(${w})`;
    }
    case 'aroon': {
      const thr = p('threshold', 50);
      return `buy: Aroon Up > Down & Up > ${thr} / sell: Down > Up`;
    }
    case 'atr_trailing_stop': {
      const mult = p('atr_multiplier', 3);
      const tma = p('trend_ma', 50);
      return `buy: price > MA(${tma}) / sell: price < close − ${mult}×ATR`;
    }
    case 'vwap_cross':
      return 'buy: price > VWAP / sell: price < VWAP';
    case 'mean_reversion':
    case 'mean_reversion_range':
    case 'mean_reversion_trend': {
      const z = p('z_threshold', 1.5);
      return `buy: Z ≤ −${z} / sell: Z ≥ ${z}`;
    }
    case 'momentum_rotation': {
      const thr = p('threshold', 0);
      return `buy: short ret > long ret + ${thr} / sell: opposite`;
    }
    case 'new_high_low': {
      const lb = p('lookback', 252);
      return `buy: new ${lb}-bar high / sell: new ${lb}-bar low`;
    }
    case 'trend_pullback': {
      const os = p('oversold', 20);
      const ob = p('overbought', 80);
      const adx = p('adx_threshold', 25);
      return `buy: ADX > ${adx} & %K crosses ${os} / sell: %K crosses ${ob}`;
    }
    case 'seasonal': {
      const sm = p('sell_month', 5);
      const bm = p('buy_month', 11);
      return `sell month ${sm} / buy month ${bm}`;
    }
    default:
      return '';
  }
}

// ---------------------------------------------------------------------------
// Signal badge
// ---------------------------------------------------------------------------

function SignalBadge({ signal }: { signal: 'BUY' | 'SELL' | 'NEUTRAL' }) {
  const styles: Record<string, string> = {
    BUY: 'bg-green-500/20 text-green-400 border-green-500/30',
    SELL: 'bg-red-500/20 text-red-400 border-red-500/30',
    NEUTRAL: 'bg-slate-700/50 text-slate-400 border-slate-600/30',
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border ${styles[signal]}`}>
      {signal}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Overall signal display
// ---------------------------------------------------------------------------

function OverallSignalBanner({ signal }: { signal: CriteriaSignal }) {
  const styles: Record<CriteriaSignal, string> = {
    BUY: 'bg-green-500/10 border-green-500/30 text-green-300',
    SELL: 'bg-red-500/10 border-red-500/30 text-red-300',
    NEUTRAL: 'bg-slate-700/30 border-slate-600/30 text-slate-400',
  };
  const icons: Record<CriteriaSignal, string> = {
    BUY: '▲',
    SELL: '▼',
    NEUTRAL: '◆',
  };
  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border ${styles[signal]}`}>
      <span className="text-xs font-bold uppercase tracking-widest">Combined Signal</span>
      <span className="text-sm font-bold ml-auto">
        {icons[signal]} {signal}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Criteria evaluation grid
// ---------------------------------------------------------------------------

function CriteriaGrid({ criteria }: { criteria: CriterionEvaluation[] }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">Criteria</p>
      <div className="grid grid-cols-2 gap-2">
        {criteria.map((c) => (
          <CriterionCell key={c.label} criterion={c} />
        ))}
      </div>
    </div>
  );
}

function CriterionCell({ criterion: c }: { criterion: CriterionEvaluation }) {
  const signalColors: Record<CriteriaSignal, string> = {
    BUY: 'text-green-400',
    SELL: 'text-red-400',
    NEUTRAL: 'text-slate-400',
  };
  const borderColors: Record<CriteriaSignal, string> = {
    BUY: 'border-green-500/30',
    SELL: 'border-red-500/30',
    NEUTRAL: 'border-slate-700',
  };

  const fmt = (v: number | null) => v == null ? '—' : v.toFixed(2);

  return (
    <div className={`bg-surface-900 rounded-lg p-2.5 border ${borderColors[c.signal]}`}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-slate-400 text-xs">{c.label}</span>
        <SignalBadge signal={c.signal} />
      </div>
      <p className={`font-mono text-sm font-semibold ${signalColors[c.signal]}`}>
        {fmt(c.value)}
      </p>
      <div className="flex gap-3 mt-1 text-xs text-slate-600">
        {c.buyThreshold != null && <span>buy ≥ {fmt(c.buyThreshold)}</span>}
        {c.sellThreshold != null && <span>sell ≤ {fmt(c.sellThreshold)}</span>}
        {c.buyThreshold == null && c.sellThreshold == null && (
          <span className="text-slate-600 italic">no threshold set</span>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Algo strategies panel (grouped by combo)
// ---------------------------------------------------------------------------

function AlgoStrategiesPanel({
  signals,
  comboSignals,
  timeframe,
}: {
  signals: AttachedAlgoSignal[];
  comboSignals: ComboGroupSignal[];
  timeframe: string;
}) {
  if (signals.length === 0) {
    return (
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">
          Algo Strategies ({timeframe})
        </p>
        <p className="text-slate-600 text-xs italic">No algo strategies configured for this asset.</p>
      </div>
    );
  }

  // Separate standalone signals from combo-grouped ones
  const standalone = signals.filter((s) => !s.comboGroup);
  const comboNames = [...new Set(signals.filter((s) => s.comboGroup).map((s) => s.comboGroup!))];

  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">
        Algo Strategies ({timeframe})
      </p>
      <div className="space-y-3">
        {/* Standalone (non-combo) strategies */}
        {standalone.length > 0 && (
          <div className="space-y-1.5">
            {standalone.map((s) => (
              <AlgoSignalRow key={s.strategy} signal={s} timeframe={timeframe} />
            ))}
          </div>
        )}

        {/* Combo groups */}
        {comboNames.map((comboName) => {
          const children = signals.filter((s) => s.comboGroup === comboName);
          const comboSig = comboSignals.find((c) => c.comboName === comboName);
          const modeLabel = comboSig?.combinationMode ?? comboName.replace('combo:', '');
          return (
            <ComboGroup
              key={comboName}
              label={`Combo: ${modeLabel}`}
              childSignals={children}
              comboSignal={comboSig ?? null}
              timeframe={timeframe}
            />
          );
        })}
      </div>
    </div>
  );
}

function StrategyTimelineChart({
  signal,
  timeframe,
}: {
  signal: AttachedAlgoSignal;
  timeframe: string;
}) {
  const strategies = attachedSignalsToTimelineStrategies([signal]);
  if (strategies.length === 0) return null;
  return (
    <ComboSignalTimeline
      strategies={strategies}
      compact
      intraday={isIntradayTimeframe(timeframe)}
      hideHeader
    />
  );
}

function ComboGroup({
  label,
  childSignals,
  comboSignal,
  timeframe,
}: {
  label: string;
  childSignals: AttachedAlgoSignal[];
  comboSignal: ComboGroupSignal | null;
  timeframe: string;
}) {
  const comboTimeline = attachedSignalsToTimelineStrategies(childSignals);
  const intraday = isIntradayTimeframe(timeframe);
  return (
    <div className="rounded-lg border border-slate-700 overflow-hidden">
      {/* Combo header */}
      <div className="flex items-center justify-between bg-slate-800 px-3 py-1.5">
        <span className="text-slate-400 text-xs font-semibold uppercase tracking-wide">{label}</span>
        {comboSignal && <SignalBadge signal={comboSignal.signal} />}
      </div>
      {comboTimeline.length > 0 && (
        <div className="px-3 py-2 bg-surface-900 border-b border-slate-800">
          <ComboSignalTimeline
            strategies={comboTimeline}
            syncId={`combo-${label}`}
            compact
            intraday={intraday}
          />
        </div>
      )}
      <div className="divide-y divide-slate-800">
        {childSignals.map((s) => (
          <div key={s.strategy} className="bg-surface-900 px-3 py-2">
            <div className="flex items-center justify-between">
              <span className="text-slate-300 text-xs truncate">{resolveStrategyLabel(s.strategy)}</span>
              <SignalBadge signal={s.signal} />
            </div>
            <IndicatorHint signal={s} />
            <StrategyTimelineChart signal={s} timeframe={timeframe} />
          </div>
        ))}
      </div>
    </div>
  );
}

function IndicatorHint({ signal: s }: { signal: AttachedAlgoSignal }) {
  const valueText = fmtIndicatorValue(s.indicatorValue, s.indicatorLabel);
  const thresholdText = formatThresholdHint(s.strategy, s.params);
  if (!valueText && !thresholdText) return null;
  return (
    <div className="mt-0.5 space-y-0.5">
      {valueText && (
        <span className="font-mono text-xs text-slate-300">{valueText}</span>
      )}
      {thresholdText && (
        <span className="block text-xs text-slate-600">{thresholdText}</span>
      )}
    </div>
  );
}

function AlgoSignalRow({ signal: s, timeframe }: { signal: AttachedAlgoSignal; timeframe: string }) {
  return (
    <div className="bg-surface-900 rounded-lg px-3 py-2 border border-slate-700">
      <div className="flex items-center justify-between">
        <span className="text-slate-300 text-xs truncate">{resolveStrategyLabel(s.strategy)}</span>
        <SignalBadge signal={s.signal} />
      </div>
      <IndicatorHint signal={s} />
      <StrategyTimelineChart signal={s} timeframe={timeframe} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Transactions table
// ---------------------------------------------------------------------------

function TransactionsTable({
  orders,
  ordersTotal,
  page,
  onPageChange,
}: {
  orders: OrderItem[];
  ordersTotal: number;
  page: number;
  onPageChange: (page: number) => void;
}) {
  const totalPages = maxOrdersPage(ordersTotal);
  const canGoPrev = page > 1;
  const canGoNext = page * TRANSACTIONS_PAGE_SIZE < ordersTotal;

  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">
        Transactions ({ordersTotal})
      </p>
      {ordersTotal === 0 ? (
        <p className="text-slate-600 text-xs italic">No orders created by this ruleset yet.</p>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
            <thead>
              <tr className="text-slate-500 border-b border-slate-700">
                <th className="text-left py-1.5 pr-3">ID</th>
                <th className="text-left py-1.5 pr-3">Side</th>
                <th className="text-right py-1.5 pr-3">Qty</th>
                <th className="text-left py-1.5 pr-3">Type</th>
                <th className="text-left py-1.5 pr-3">Status</th>
                <th className="text-right py-1.5 pr-3">Fill Price</th>
                <th className="text-left py-1.5">Time</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => (
                <OrderRow key={o.id} order={o} />
              ))}
            </tbody>
            </table>
          </div>
          {totalPages > 1 && (
            <TransactionsPagination
              page={page}
              totalPages={totalPages}
              canGoPrev={canGoPrev}
              canGoNext={canGoNext}
              onPageChange={onPageChange}
            />
          )}
        </>
      )}
    </div>
  );
}

function maxOrdersPage(total: number): number {
  if (total <= 0) return 1;
  return Math.ceil(total / TRANSACTIONS_PAGE_SIZE);
}

function TransactionsPagination({
  page,
  totalPages,
  canGoPrev,
  canGoNext,
  onPageChange,
}: {
  page: number;
  totalPages: number;
  canGoPrev: boolean;
  canGoNext: boolean;
  onPageChange: (page: number) => void;
}) {
  return (
    <div className="flex items-center justify-between mt-2">
      <span className="text-xs text-slate-500">
        Page {page} of {totalPages}
      </span>
      <div className="flex gap-2">
        <button
          type="button"
          disabled={!canGoPrev}
          onClick={() => onPageChange(page - 1)}
          className="px-2 py-1 text-xs rounded border border-slate-700 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-surface-800"
        >
          Previous
        </button>
        <button
          type="button"
          disabled={!canGoNext}
          onClick={() => onPageChange(page + 1)}
          className="px-2 py-1 text-xs rounded border border-slate-700 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-surface-800"
        >
          Next
        </button>
      </div>
    </div>
  );
}

function OrderRow({ order: o }: { order: OrderItem }) {
  return (
    <tr className="border-b border-slate-800 text-slate-300">
      <td className="py-1.5 pr-3 font-mono text-slate-500">{o.id}</td>
      <td className={`py-1.5 pr-3 font-semibold uppercase ${o.side === 'buy' ? 'text-green-400' : 'text-red-400'}`}>
        {o.side}
      </td>
      <td className="text-right py-1.5 pr-3 font-mono">{o.qty}</td>
      <td className="py-1.5 pr-3 text-slate-400">{o.order_type}</td>
      <td className="py-1.5 pr-3">
        <StatusChip status={o.status} />
      </td>
      <td className="text-right py-1.5 pr-3 font-mono">
        {o.filled_price != null ? `$${o.filled_price.toFixed(2)}` : '—'}
      </td>
      <td className="py-1.5 text-slate-500">{new Date(o.created_at).toLocaleString()}</td>
    </tr>
  );
}

function StatusChip({ status }: { status: string }) {
  const normalized = status.toLowerCase().replace(/\s+/g, '_');
  const colors: Record<string, string> = {
    filled: 'text-green-400',
    partially_filled: 'text-yellow-400',
    cancelled: 'text-slate-500',
    canceled: 'text-slate-500',
    rejected: 'text-red-400',
    pending: 'text-blue-400',
    pending_new: 'text-blue-400',
    accepted: 'text-blue-400',
    new: 'text-blue-400',
  };
  return (
    <span className={`font-medium capitalize ${colors[normalized] ?? 'text-slate-300'}`}>
      {status.replace(/_/g, ' ')}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Header
// ---------------------------------------------------------------------------

function CardHeader({
  monitor,
  expanded,
  onToggle,
  bodyId,
}: {
  monitor: ExecutionAssetMonitor;
  expanded: boolean;
  onToggle: () => void;
  bodyId: string;
}) {
  const modeLabel: Record<string, string> = { all: 'All', majority: 'Majority', any: 'Any' };

  return (
    <div className="flex items-center gap-3 flex-wrap">
      <button
        type="button"
        onClick={onToggle}
        className="flex items-center gap-2 text-left min-w-0 flex-wrap"
        aria-expanded={expanded}
        aria-controls={bodyId}
        aria-label={expanded ? 'Collapse asset details' : 'Expand asset details'}
      >
        <span className="text-slate-500 text-xs shrink-0">{expanded ? '▲' : '▼'}</span>
        <span className="text-brand-500 font-bold text-base">{monitor.symbol}</span>
        {monitor.assetName && (
          <span className="text-slate-400 text-sm">{monitor.assetName}</span>
        )}
        <span className="text-xs bg-surface-900 border border-slate-700 rounded px-2 py-0.5 text-slate-300">
          {monitor.algoTimeframe}
        </span>
        <span className="text-xs bg-surface-900 border border-slate-700 rounded px-2 py-0.5 text-slate-400">
          Combo: {modeLabel[monitor.combinationMode] ?? monitor.combinationMode}
        </span>
      </button>
      <div className="ml-auto flex items-center gap-1.5">
        <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
        <span className="text-green-400 text-xs font-medium">Running</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Latest price
// ---------------------------------------------------------------------------

function PriceDisplay({ price, updatedAt }: { price: number | null; updatedAt: string | null }) {
  return (
    <div className="flex items-center gap-4">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-0.5">Latest Price</p>
        <p className="font-mono text-lg font-bold text-slate-100">
          {price != null ? `$${price.toFixed(2)}` : '—'}
        </p>
      </div>
      {updatedAt && (
        <p className="text-xs text-slate-600 self-end mb-1">
          Updated: {new Date(updatedAt).toLocaleTimeString()}
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main card
// ---------------------------------------------------------------------------

interface Props {
  monitor: ExecutionAssetMonitor;
  onOrdersPageChange: (page: number) => void;
}

export default function ExecutionAssetCard({ monitor, onOrdersPageChange }: Props) {
  const [expanded, setExpanded] = useState(false);
  const bodyId = `execution-card-body-${monitor.strategyId}`;

  return (
    <div className="card space-y-4">
      <CardHeader
        monitor={monitor}
        expanded={expanded}
        onToggle={() => setExpanded((e) => !e)}
        bodyId={bodyId}
      />

      <div className="border-t border-slate-700 pt-3">
        <PriceDisplay price={monitor.latestPrice} updatedAt={monitor.priceUpdatedAt} />
      </div>

      <OverallSignalBanner signal={monitor.overallSignal} />

      {expanded && (
        <div id={bodyId} className="space-y-4">
          <CriteriaGrid criteria={monitor.criteria} />

          <div className="border-t border-slate-700 pt-3">
            <AlgoStrategiesPanel
              signals={monitor.algoSignals}
              comboSignals={monitor.comboSignals}
              timeframe={monitor.algoTimeframe}
            />
          </div>

          <div className="border-t border-slate-700 pt-3">
            <TransactionsTable
              orders={monitor.orders}
              ordersTotal={monitor.ordersTotal}
              page={monitor.ordersPage}
              onPageChange={onOrdersPageChange}
            />
          </div>
        </div>
      )}
    </div>
  );
}
