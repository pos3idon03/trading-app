/**
 * Derives terminal-style activity lines by diffing successive execution monitor snapshots.
 */
import type {
  AttachedAlgoSignal,
  ComboGroupSignal,
  CriterionEvaluation,
  ExecutionAssetMonitor,
  OrderItem,
  StreamStatusResponse,
} from '../api/types';
import { STRATEGIES } from '../constants/strategies';
import { formatIndicatorReading } from './formatLiveIndicator';
import { isSymbolSubscribed } from './streamSymbolMatch';

export type LogSeverity = 'info' | 'warn' | 'success' | 'error';

export interface ExecutionLogLine {
  id: string;
  tsISO: string;
  symbol: string;
  severity?: LogSeverity;
  text: string;
}

export interface DiffContext {
  barSourceBySymbol: Map<string, string>;
  nowISO: string;
  nextLineId: () => string;
}

export interface DiffMonitorsOptions {
  /** Emit a line when a live poll completes but metrics are unchanged. */
  logPollHeartbeat?: boolean;
  /** Emit full evaluation block on each live poll (Live terminal page). */
  logPollEvaluations?: boolean;
}

export function resolveBarSourceLabel(
  symbol: string,
  streamStatus: StreamStatusResponse | null,
): string {
  if (!streamStatus?.connected || !isSymbolSubscribed(symbol, streamStatus.subscribed_symbols)) {
    return 'DB bars';
  }
  const isCrypto = symbol.includes('-') && /-(USD|USDT|USDC)$/i.test(symbol);
  if (isCrypto && streamStatus.crypto_connected === false) {
    return 'DB bars';
  }
  if (!isCrypto && streamStatus.stock_connected === false) {
    return 'DB bars';
  }
  return 'alpaca';
}

export function buildBarSourceMap(
  symbols: string[],
  streamStatus: StreamStatusResponse | null,
): Map<string, string> {
  const map = new Map<string, string>();
  for (const sym of symbols) {
    map.set(sym, resolveBarSourceLabel(sym, streamStatus));
  }
  return map;
}

function makeLine(
  ctx: DiffContext,
  symbol: string,
  text: string,
  severity: LogSeverity = 'info',
  tsISO?: string,
): ExecutionLogLine {
  return {
    id: ctx.nextLineId(),
    tsISO: tsISO ?? ctx.nowISO,
    symbol,
    severity,
    text,
  };
}

function formatClockTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString(undefined, { hour12: false });
  } catch {
    return iso;
  }
}

function strategyLabel(strategy: string, fallback: string): string {
  return STRATEGIES.find((s) => s.value === strategy)?.label ?? fallback;
}

function formatCriterionDisplay(label: string, value: number | null): string {
  if (value == null) return '—';
  if (label.includes('Prob')) return `${(value * 100).toFixed(0)}%`;
  return value.toFixed(2);
}

function formatNumericDelta(
  oldVal: number,
  newVal: number,
  label: string,
): { direction: string; detail: string } {
  const diff = newVal - oldVal;
  const direction = diff >= 0 ? 'Increased' : 'Decreased';
  if (label.includes('Prob')) {
    const oldPct = (oldVal * 100).toFixed(0);
    const newPct = (newVal * 100).toFixed(0);
    const pctDiff = Math.abs((newVal - oldVal) * 100).toFixed(0);
    return { direction, detail: `by ${pctDiff}% [${oldPct}% -> ${newPct}%]` };
  }
  const abs = Math.abs(diff);
  const formatted = Number(abs.toFixed(4)).toString();
  return {
    direction,
    detail: `by ${formatted} [${formatCriterionDisplay(label, oldVal)} -> ${formatCriterionDisplay(label, newVal)}]`,
  };
}

function valuesEqual(a: number | null | undefined, b: number | null | undefined): boolean {
  if (a == null && b == null) return true;
  if (a == null || b == null) return false;
  return Math.abs(a - b) < 1e-9;
}

function formatPriceLine(
  monitor: ExecutionAssetMonitor,
  ctx: DiffContext,
): string | null {
  const price = monitor.latestPrice;
  if (price == null) return null;
  const source = ctx.barSourceBySymbol.get(monitor.symbol) ?? 'DB bars';
  const at = monitor.priceUpdatedAt ?? ctx.nowISO;
  const clock = formatClockTime(at);
  return `${monitor.symbol} stock price is ${price.toFixed(2)} | source: ${source} | streamed on ${clock}`;
}

function diffPrice(
  prev: ExecutionAssetMonitor,
  next: ExecutionAssetMonitor,
  ctx: DiffContext,
  lines: ExecutionLogLine[],
): void {
  const priceChanged = !valuesEqual(prev.latestPrice, next.latestPrice);
  const atChanged = prev.priceUpdatedAt !== next.priceUpdatedAt;
  if (!priceChanged && !atChanged) return;
  if (next.latestPrice == null) return;

  const text = formatPriceLine(next, ctx);
  if (text) lines.push(makeLine(ctx, next.symbol, text));
}

function diffCriteria(
  prev: ExecutionAssetMonitor,
  next: ExecutionAssetMonitor,
  ctx: DiffContext,
  lines: ExecutionLogLine[],
): void {
  const prevByLabel = new Map(prev.criteria.map((c) => [c.label, c]));
  for (const criterion of next.criteria) {
    const old = prevByLabel.get(criterion.label);
    if (!old) continue;
    diffOneCriterion(old, criterion, next.symbol, ctx, lines);
  }
}

function diffOneCriterion(
  old: CriterionEvaluation,
  next: CriterionEvaluation,
  symbol: string,
  ctx: DiffContext,
  lines: ExecutionLogLine[],
): void {
  const valueChanged = !valuesEqual(old.value, next.value);
  const signalChanged = old.signal !== next.signal;
  if (!valueChanged && !signalChanged) return;

  let text = `${next.label} updated`;
  if (valueChanged && old.value != null && next.value != null) {
    const { direction, detail } = formatNumericDelta(old.value, next.value, next.label);
    text = `${next.label} updated | ${direction} ${detail}`;
  } else if (next.value != null) {
    text = `${next.label} updated | now ${formatCriterionDisplay(next.label, next.value)}`;
  }

  if (signalChanged) {
    text += ` | Signal is ${next.signal}`;
  }

  const severity: LogSeverity = next.signal === 'BUY' ? 'success' : next.signal === 'SELL' ? 'warn' : 'info';
  lines.push(makeLine(ctx, symbol, text, severity));
}

function algoKey(signal: AttachedAlgoSignal): string {
  return signal.comboGroup ? `${signal.comboGroup}:${signal.strategy}` : signal.strategy;
}

function diffAlgoSignals(
  prev: ExecutionAssetMonitor,
  next: ExecutionAssetMonitor,
  ctx: DiffContext,
  lines: ExecutionLogLine[],
): void {
  const prevByKey = new Map(prev.algoSignals.map((s) => [algoKey(s), s]));
  for (const algo of next.algoSignals) {
    const old = prevByKey.get(algoKey(algo));
    if (!old) continue;
    diffOneAlgoSignal(old, algo, next.symbol, ctx, lines);
  }
}

function diffOneAlgoSignal(
  old: AttachedAlgoSignal,
  next: AttachedAlgoSignal,
  symbol: string,
  ctx: DiffContext,
  lines: ExecutionLogLine[],
): void {
  const valueChanged = !valuesEqual(old.indicatorValue, next.indicatorValue);
  const signalChanged = old.signal !== next.signal;
  if (!valueChanged && !signalChanged) return;

  const name = strategyLabel(next.strategy, next.label);
  let text = `${name} recalculated`;

  if (valueChanged && old.indicatorValue != null && next.indicatorValue != null) {
    const diff = next.indicatorValue - old.indicatorValue;
    const direction = diff >= 0 ? 'Increased' : 'Decreased';
    const abs = Math.abs(diff);
    const formatted = Number(abs.toFixed(4)).toString();
    const oldFmt = Number(old.indicatorValue.toFixed(4)).toString();
    const newFmt = Number(next.indicatorValue.toFixed(4)).toString();
    text = `${name} recalculated | ${direction} by ${formatted} [${oldFmt} -> ${newFmt}]`;
    if (next.indicatorLabel) {
      text = `${name} recalculated | ${next.indicatorLabel} ${direction.toLowerCase()} by ${formatted} [${oldFmt} -> ${newFmt}]`;
    }
  }

  if (signalChanged || next.signal !== 'NEUTRAL') {
    text += ` | Signal is ${next.signal}`;
  }

  const severity: LogSeverity = next.signal === 'BUY' ? 'success' : next.signal === 'SELL' ? 'warn' : 'info';
  lines.push(makeLine(ctx, symbol, text, severity));
}

function diffComboSignals(
  prev: ExecutionAssetMonitor,
  next: ExecutionAssetMonitor,
  ctx: DiffContext,
  lines: ExecutionLogLine[],
): void {
  const prevByName = new Map(prev.comboSignals.map((c) => [c.comboName, c]));
  for (const combo of next.comboSignals) {
    const old = prevByName.get(combo.comboName);
    if (!old || old.signal === combo.signal) continue;
    diffOneCombo(old, combo, next.symbol, ctx, lines);
  }
}

function diffOneCombo(
  _old: ComboGroupSignal,
  next: ComboGroupSignal,
  symbol: string,
  ctx: DiffContext,
  lines: ExecutionLogLine[],
): void {
  const name = strategyLabel(next.comboName, next.comboName);
  const text = `${name} (${next.combinationMode}) | Signal is ${next.signal}`;
  const severity: LogSeverity = next.signal === 'BUY' ? 'success' : next.signal === 'SELL' ? 'warn' : 'info';
  lines.push(makeLine(ctx, symbol, text, severity));
}

function diffOverallSignal(
  prev: ExecutionAssetMonitor,
  next: ExecutionAssetMonitor,
  ctx: DiffContext,
  lines: ExecutionLogLine[],
): void {
  if (prev.overallSignal === next.overallSignal) return;
  const text = `Overall signal (${next.combinationMode}) | ${prev.overallSignal} -> ${next.overallSignal}`;
  const severity: LogSeverity =
    next.overallSignal === 'BUY' ? 'success' : next.overallSignal === 'SELL' ? 'warn' : 'info';
  lines.push(makeLine(ctx, next.symbol, text, severity));
}

function orderFingerprint(orders: OrderItem[]): string {
  return orders.map((o) => `${o.id}:${o.status}`).join('|');
}

/** First orders fetch after mount — historical rows, not new activity. */
export function isInitialOrderHydration(
  prevOrders: OrderItem[],
  nextOrders: OrderItem[],
): boolean {
  return prevOrders.length === 0 && nextOrders.length > 0;
}

function diffOrders(
  prev: ExecutionAssetMonitor,
  next: ExecutionAssetMonitor,
  ctx: DiffContext,
  lines: ExecutionLogLine[],
): void {
  if (isInitialOrderHydration(prev.orders, next.orders)) {
    return;
  }

  const prevMap = new Map(prev.orders.map((o) => [o.id, o]));
  for (const order of next.orders) {
    const old = prevMap.get(order.id);
    if (!old) {
      lines.push(makeLine(
        ctx,
        next.symbol,
        `Order #${order.id} submitted | ${order.side} ${order.qty} @ ${order.order_type} | status: ${order.status}`,
        'info',
        order.created_at,
      ));
      continue;
    }
    if (old.status !== order.status) {
      const severity: LogSeverity =
        order.status === 'filled' ? 'success' : order.status === 'rejected' ? 'error' : 'info';
      const ts = order.updated_at ?? order.filled_at ?? order.created_at;
      lines.push(makeLine(
        ctx,
        next.symbol,
        `Order #${order.id} status | ${old.status} -> ${order.status}`,
        severity,
        ts,
      ));
    }
  }
}

function signalSeverity(signal: string): LogSeverity {
  if (signal === 'BUY') return 'success';
  if (signal === 'SELL') return 'warn';
  return 'info';
}

export function formatCriterionEvaluation(c: CriterionEvaluation): string {
  const value = formatCriterionDisplay(c.label, c.value);
  return `${c.label} evaluated | ${value} | signal ${c.signal}`;
}

export function formatAlgoEvaluation(algo: AttachedAlgoSignal): string {
  const name = strategyLabel(algo.strategy, algo.label);
  const reading = formatIndicatorReading(algo.indicatorValue, algo.indicatorLabel);
  return `${name} evaluated | ${reading} | signal ${algo.signal}`;
}

function shouldEmitPollEvaluation(
  prev: ExecutionAssetMonitor,
  next: ExecutionAssetMonitor,
): boolean {
  return Boolean(
    next.lastLivePollAt
    && prev.lastLivePollAt !== next.lastLivePollAt,
  );
}

/** Full per-poll snapshot for the Live terminal. */
export function buildPollEvaluationLines(
  monitor: ExecutionAssetMonitor,
  ctx: DiffContext,
): ExecutionLogLine[] {
  const ts = monitor.lastLivePollAt ?? ctx.nowISO;
  const source = ctx.barSourceBySymbol.get(monitor.symbol) ?? 'DB bars';
  const lines: ExecutionLogLine[] = [];

  lines.push(makeLine(
    ctx,
    monitor.symbol,
    `Live evaluation (${monitor.algoTimeframe}) | source: ${source}`,
    'info',
    ts,
  ));

  const price = monitor.latestPrice != null ? `$${monitor.latestPrice.toFixed(2)}` : '—';
  lines.push(makeLine(ctx, monitor.symbol, `  Price ${price}`, 'info', ts));

  for (const c of monitor.criteria) {
    lines.push(makeLine(
      ctx,
      monitor.symbol,
      `  ${formatCriterionEvaluation(c)}`,
      signalSeverity(c.signal),
      ts,
    ));
  }

  for (const algo of monitor.algoSignals) {
    lines.push(makeLine(
      ctx,
      monitor.symbol,
      `  ${formatAlgoEvaluation(algo)}`,
      signalSeverity(algo.signal),
      ts,
    ));
  }

  for (const combo of monitor.comboSignals) {
    const name = strategyLabel(combo.comboName, combo.comboName);
    lines.push(makeLine(
      ctx,
      monitor.symbol,
      `  ${name} evaluated | signal ${combo.signal}`,
      signalSeverity(combo.signal),
      ts,
    ));
  }

  lines.push(makeLine(
    ctx,
    monitor.symbol,
    `  Combined signal (${monitor.combinationMode}) | ${monitor.overallSignal}`,
    signalSeverity(monitor.overallSignal),
    ts,
  ));

  return lines;
}

function diffPollHeartbeat(
  prev: ExecutionAssetMonitor,
  next: ExecutionAssetMonitor,
  ctx: DiffContext,
): ExecutionLogLine | null {
  if (!prev.lastLivePollAt || !next.lastLivePollAt || prev.lastLivePollAt === next.lastLivePollAt) {
    return null;
  }
  const price = next.latestPrice != null ? `$${next.latestPrice.toFixed(2)}` : '—';
  const text = `Poll complete | price ${price} | overall ${next.overallSignal} | no metric changes`;
  return makeLine(ctx, next.symbol, text, 'info', next.lastLivePollAt);
}

function diffOneMonitor(
  prev: ExecutionAssetMonitor,
  next: ExecutionAssetMonitor,
  ctx: DiffContext,
  options: DiffMonitorsOptions,
): ExecutionLogLine[] {
  const logPollHeartbeat = options.logPollHeartbeat ?? false;
  const logPollEvaluations = options.logPollEvaluations ?? false;

  if (logPollEvaluations && shouldEmitPollEvaluation(prev, next)) {
    const evalLines = buildPollEvaluationLines(next, ctx);
    if (orderFingerprint(prev.orders) !== orderFingerprint(next.orders)) {
      diffOrders(prev, next, ctx, evalLines);
    }
    return evalLines;
  }

  const lines: ExecutionLogLine[] = [];
  if (logPollEvaluations) {
    diffCriteria(prev, next, ctx, lines);
    if (orderFingerprint(prev.orders) !== orderFingerprint(next.orders)) {
      diffOrders(prev, next, ctx, lines);
    }
    return lines;
  }
  diffPrice(prev, next, ctx, lines);
  diffCriteria(prev, next, ctx, lines);
  diffAlgoSignals(prev, next, ctx, lines);
  diffComboSignals(prev, next, ctx, lines);
  diffOverallSignal(prev, next, ctx, lines);
  if (orderFingerprint(prev.orders) !== orderFingerprint(next.orders)) {
    diffOrders(prev, next, ctx, lines);
  }
  if (logPollHeartbeat && lines.length === 0) {
    const heartbeat = diffPollHeartbeat(prev, next, ctx);
    if (heartbeat) lines.push(heartbeat);
  }
  return lines;
}

/** Compare monitor snapshots; skip assets with no prior snapshot (baseline). */
export function diffMonitors(
  prev: Map<number, ExecutionAssetMonitor>,
  next: ExecutionAssetMonitor[],
  ctx: DiffContext,
  options: DiffMonitorsOptions = {},
): ExecutionLogLine[] {
  const lines: ExecutionLogLine[] = [];
  for (const monitor of next) {
    const old = prev.get(monitor.strategyId);
    if (!old) continue;
    lines.push(...diffOneMonitor(old, monitor, ctx, options));
  }
  return lines;
}

/** Build a baseline map from current monitors (no log emission). */
export function snapshotMonitors(
  monitors: ExecutionAssetMonitor[],
): Map<number, ExecutionAssetMonitor> {
  return new Map(monitors.map((m) => [m.strategyId, m]));
}
