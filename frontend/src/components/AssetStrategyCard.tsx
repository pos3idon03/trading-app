import { useEffect, useRef, useState } from 'react';
import { strategyBuilderApi } from '../api/endpoints';
import type {
  AIAgentSummary,
  AlgoStrategySummary,
  FinancialsSummary,
  MonteCarloSummary,
  StrategyFullResponse,
  StrategyRecord,
  UpdateThresholdsRequest,
} from '../api/types';
import { STRATEGIES } from '../constants/strategies';
import { fmt, fmtPct } from '../utils/formatting';
import ErrorAlert from './ErrorAlert';
import RangeScoreBar from './RangeScoreBar';
import Spinner from './Spinner';

interface Props {
  strategy: StrategyRecord;
  onRemove: (strategyId: number) => void;
  onUpdated: (record: StrategyRecord) => void;
}

// ---------------------------------------------------------------------------
// Threshold range slider
// ---------------------------------------------------------------------------

function ThresholdSlider({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  value: string;
  min: number;
  max: number;
  step?: number;
  onChange: (v: string) => void;
}) {
  const numValue = value === '' ? null : parseFloat(value);
  const isSet = numValue !== null && !isNaN(numValue);
  const effectiveStep = step ?? 0.01;
  const midpoint = parseFloat(((min + max) / 2).toFixed(2));

  return (
    <div className="flex items-center gap-2 min-w-0">
      <label className="text-slate-500 text-xs w-44 shrink-0">{label}</label>
      {isSet ? (
        <>
          <input
            type="range"
            min={min}
            max={max}
            step={effectiveStep}
            value={numValue}
            onChange={(e) => onChange(e.target.value)}
            className="threshold-slider flex-1 min-w-0"
          />
          <span className="text-slate-200 text-xs font-mono w-10 text-right shrink-0">
            {numValue.toFixed(2)}
          </span>
          <button
            onClick={() => onChange('')}
            className="text-slate-500 hover:text-red-400 text-xs shrink-0 leading-none"
            title="Clear threshold"
          >
            ✕
          </button>
        </>
      ) : (
        <button
          onClick={() => onChange(String(midpoint))}
          className="text-xs text-brand-400 hover:text-brand-300 transition-colors"
        >
          + Set threshold
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Monte Carlo Section
// ---------------------------------------------------------------------------

type MCThresholds = { buyProb: string; sellProb: string };
type MCThresholdKey = keyof MCThresholds;

function MonteCarloSection({
  data,
  error,
  thresholds,
  onThresholdChange,
}: {
  data: MonteCarloSummary | null;
  error: string | null;
  thresholds: MCThresholds;
  onThresholdChange: (key: MCThresholdKey, v: string) => void;
}) {
  if (error) return <ErrorAlert message={`Monte Carlo: ${error}`} />;
  if (!data) return <p className="text-slate-500 text-sm">No simulation data available.</p>;

  const rows: { label: string; value: string }[] = [
    { label: '5th Pct', value: fmt(data.p5, 2) },
    { label: '25th Pct', value: fmt(data.p25, 2) },
    { label: '50th Pct', value: fmt(data.p50, 2) },
    { label: '75th Pct', value: fmt(data.p75, 2) },
    { label: '95th Pct', value: fmt(data.p95, 2) },
  ];

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-surface-900 rounded-lg p-3 border border-slate-700">
          <p className="metric-label">Prob. Positive Return</p>
          <p className={`metric-value ${data.prob_positive_return >= 0.5 ? 'positive' : 'negative'}`}>
            {fmtPct(data.prob_positive_return)}
          </p>
        </div>
        <div className="bg-surface-900 rounded-lg p-3 border border-slate-700">
          <p className="metric-label">Mean Max Drawdown</p>
          <p className="metric-value negative">{fmtPct(data.mean_max_drawdown)}</p>
        </div>
      </div>

      <div>
        <p className="metric-label mb-2">Terminal Price Percentiles (10 000 paths, 126d)</p>
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr>
              {rows.map((r) => (
                <th key={r.label} className="text-slate-400 font-medium text-center pb-1 border-b border-slate-700">
                  {r.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              {rows.map((r) => (
                <td key={r.label} className="text-slate-200 text-center py-1">{r.value}</td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      {data.cached && (
        <p className="text-xs text-slate-500 italic">Using cached simulation (less than 24h old)</p>
      )}

      <div className="border-t border-slate-700/60 pt-3 space-y-2">
        <p className="text-xs text-slate-500 font-medium uppercase tracking-wide">Auto-Trading Thresholds</p>
        <ThresholdSlider
          label="Min Prob. Positive (BUY)"
          value={thresholds.buyProb}
          min={0} max={1}
          onChange={(v) => onThresholdChange('buyProb', v)}
        />
        <ThresholdSlider
          label="Max Prob. Positive (SELL)"
          value={thresholds.sellProb}
          min={0} max={1}
          onChange={(v) => onThresholdChange('sellProb', v)}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// AI Agents Section
// ---------------------------------------------------------------------------

type AIThresholds = {
  buyConviction: string; sellConviction: string;
  buySentiment: string; sellSentiment: string;
  buyMacro: string; sellMacro: string;
};
type AIThresholdKey = keyof AIThresholds;

function AIAgentsSection({
  data,
  error,
  thresholds,
  onThresholdChange,
}: {
  data: AIAgentSummary | null;
  error: string | null;
  thresholds: AIThresholds;
  onThresholdChange: (key: AIThresholdKey, v: string) => void;
}) {
  if (error) return <ErrorAlert message={`AI Agents: ${error}`} />;
  if (!data) return <p className="text-slate-500 text-sm">No agent analysis available. Run an analysis from the AI Agents page.</p>;

  const biasColor = data.bias === 'bullish' ? 'positive' : data.bias === 'bearish' ? 'negative' : 'neutral';

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <span className="metric-label">Bias:</span>
        <span className={`font-semibold text-sm capitalize ${biasColor}`}>{data.bias ?? '—'}</span>
      </div>

      <RangeScoreBar value={data.conviction_score} label="Conviction Score" min={0} max={1} />
      <RangeScoreBar value={data.sentiment_score} label="Sentiment Score" min={-1} max={1} />
      <RangeScoreBar value={data.macro_score} label="Macro Score" min={-1} max={1} />

      {data.key_risk && (
        <div className="bg-surface-900 rounded-lg p-3 border border-slate-700">
          <p className="metric-label mb-1">Key Risk</p>
          <p className="text-slate-300 text-xs leading-relaxed">{data.key_risk}</p>
        </div>
      )}

      {data.created_at && (
        <p className="text-xs text-slate-500">
          Last updated: {new Date(data.created_at).toLocaleDateString()}
        </p>
      )}

      <div className="border-t border-slate-700/60 pt-3 space-y-2">
        <p className="text-xs text-slate-500 font-medium uppercase tracking-wide">Auto-Trading Thresholds</p>
        <ThresholdSlider label="Min Conviction (BUY)" value={thresholds.buyConviction} min={-1} max={1} onChange={(v) => onThresholdChange('buyConviction', v)} />
        <ThresholdSlider label="Max Conviction (SELL)" value={thresholds.sellConviction} min={-1} max={1} onChange={(v) => onThresholdChange('sellConviction', v)} />
        <ThresholdSlider label="Min Sentiment (BUY)" value={thresholds.buySentiment} min={-1} max={1} onChange={(v) => onThresholdChange('buySentiment', v)} />
        <ThresholdSlider label="Max Sentiment (SELL)" value={thresholds.sellSentiment} min={-1} max={1} onChange={(v) => onThresholdChange('sellSentiment', v)} />
        <ThresholdSlider label="Min Macro (BUY)" value={thresholds.buyMacro} min={-1} max={1} onChange={(v) => onThresholdChange('buyMacro', v)} />
        <ThresholdSlider label="Max Macro (SELL)" value={thresholds.sellMacro} min={-1} max={1} onChange={(v) => onThresholdChange('sellMacro', v)} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Financials Section
// ---------------------------------------------------------------------------

function FinRow({ label, value, isPercent = false, isMoney = false }: {
  label: string;
  value: number | null;
  isPercent?: boolean;
  isMoney?: boolean;
}) {
  const formatted = value === null ? '—'
    : isPercent ? fmtPct(value)
    : isMoney ? formatLargeNumber(value)
    : fmt(value, 2);

  return (
    <div className="flex justify-between items-center py-1.5 border-b border-slate-700/50 last:border-0">
      <span className="text-slate-400 text-xs">{label}</span>
      <span className="text-slate-200 text-xs font-mono">{formatted}</span>
    </div>
  );
}

function formatLargeNumber(v: number): string {
  if (Math.abs(v) >= 1e12) return `$${(v / 1e12).toFixed(2)}T`;
  if (Math.abs(v) >= 1e9) return `$${(v / 1e9).toFixed(2)}B`;
  if (Math.abs(v) >= 1e6) return `$${(v / 1e6).toFixed(2)}M`;
  return `$${v.toFixed(0)}`;
}

function FinancialsSection({ data, error }: { data: FinancialsSummary | null; error: string | null }) {
  if (error) return <ErrorAlert message={`Financials: ${error}`} />;
  if (!data) return <p className="text-slate-500 text-sm">No financial data available.</p>;

  return (
    <div className="space-y-1">
      <FinRow label="Revenue Growth" value={data.revenue_growth} isPercent />
      <FinRow label="Free Cash Flow" value={data.free_cash_flow} isMoney />
      <FinRow label="Current Ratio" value={data.current_ratio} />
      <FinRow label="P/E (TTM)" value={data.pe_ttm} />
      <FinRow label="P/E (Forward)" value={data.pe_forward} />
      <FinRow label="P/B Ratio" value={data.pb_ratio} />
      <FinRow label="EPS (TTM)" value={data.eps_ttm} />
      <FinRow label="EPS (Forward)" value={data.eps_forward} />
      <FinRow label="Market Cap" value={data.market_cap} isMoney />
      {data.is_stale && (
        <p className="text-xs text-yellow-500 pt-1">Data may be stale — refresh triggered on last load.</p>
      )}
      {data.fetched_at && (
        <p className="text-xs text-slate-500">
          Fetched: {new Date(data.fetched_at).toLocaleDateString()}
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Algo Strategies Section
// ---------------------------------------------------------------------------

const COMBO_MODE_LABELS: Record<string, string> = {
  and: 'AND (Unanimous)',
  or: 'OR (Any)',
  any: 'OR (Any)',
  majority: 'Majority Vote',
  weighted: 'Weighted',
};

interface ComboSubStrategy {
  strategy_name: string;
  strategy_params: Record<string, number>;
  weight: number;
  timeframe?: string;
}

interface ComboParams {
  combination_mode: string;
  threshold: number;
  strategies: ComboSubStrategy[];
}

function ParamChips({ params }: { params: Record<string, unknown> }) {
  const entries = Object.entries(params);
  if (entries.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1 mt-1">
      {entries.map(([k, v]) => (
        <span
          key={k}
          className="bg-slate-800 border border-slate-600 rounded px-1.5 py-0.5 text-xs text-slate-400 font-mono"
        >
          {k}: <span className="text-slate-300">{String(v)}</span>
        </span>
      ))}
    </div>
  );
}

function AlgoAddedAt({ item }: { item: AlgoStrategySummary }) {
  const date = new Date(item.added_at).toLocaleDateString();
  return <span className="text-xs text-slate-500">Added {date}</span>;
}

function ComboAlgoRow({
  item,
  onDetach,
}: {
  item: AlgoStrategySummary;
  onDetach: (algoAttachmentId: number) => void;
}) {
  const params = item.params as unknown as ComboParams | null;
  const mode = params?.combination_mode ?? item.strategy_name.replace('combo:', '');
  const modeLabel = COMBO_MODE_LABELS[mode] ?? mode;
  const subStrategies: ComboSubStrategy[] = params?.strategies ?? [];
  const isWeighted = mode === 'weighted';

  return (
    <div className="bg-surface-900 rounded-lg p-3 border border-slate-700 space-y-2">
      <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0 space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-slate-200 text-sm font-medium">Combo Strategy</p>
            <span className="bg-brand-500/20 text-brand-400 text-xs px-2 py-0.5 rounded-full font-medium">
              {modeLabel}
            </span>
            {params?.threshold !== undefined && isWeighted && (
              <span className="text-xs text-slate-500">threshold: {params.threshold}</span>
            )}
          </div>
          <AlgoAddedAt item={item} />
        </div>
        <button
          onClick={() => onDetach(item.algo_attachment_id)}
          className="text-slate-500 hover:text-red-400 text-xs shrink-0 transition-colors"
          title="Remove"
        >
          ✕
        </button>
      </div>

      {subStrategies.length > 0 && (
        <div className="border-t border-slate-700/60 pt-2 space-y-2">
          {subStrategies.map((sub) => {
            const subLabel =
              STRATEGIES.find((s) => s.value === sub.strategy_name)?.label ?? sub.strategy_name;
            return (
              <div key={sub.strategy_name} className="pl-2 border-l-2 border-slate-600">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-slate-300 text-xs font-medium">{subLabel}</span>
                  {sub.timeframe && <TimeframeBadge tf={sub.timeframe} />}
                  {isWeighted && (
                    <span className="text-xs text-slate-500">weight: {sub.weight}</span>
                  )}
                </div>
                {sub.strategy_params && Object.keys(sub.strategy_params).length > 0 && (
                  <ParamChips params={sub.strategy_params} />
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function TimeframeBadge({ tf }: { tf: string }) {
  return (
    <span className="bg-slate-800 text-slate-400 text-xs px-2 py-0.5 rounded font-mono">
      {tf}
    </span>
  );
}

function AlgoRow({
  item,
  onDetach,
}: {
  item: AlgoStrategySummary;
  onDetach: (algoAttachmentId: number) => void;
}) {
  const label = STRATEGIES.find((s) => s.value === item.strategy_name)?.label ?? item.strategy_name;
  const params = item.params as Record<string, unknown> | null;

  return (
    <div className="bg-surface-900 rounded-lg p-3 border border-slate-700 flex items-start justify-between gap-2">
      <div className="flex-1 min-w-0 space-y-1">
        <div className="flex items-center gap-2 flex-wrap">
          <p className="text-slate-200 text-sm font-medium truncate">{label}</p>
          <TimeframeBadge tf={item.timeframe} />
        </div>
        <AlgoAddedAt item={item} />
        {params && Object.keys(params).length > 0 && <ParamChips params={params} />}
      </div>
      <button
        onClick={() => onDetach(item.algo_attachment_id)}
        className="text-slate-500 hover:text-red-400 text-xs shrink-0 transition-colors"
        title="Remove"
      >
        ✕
      </button>
    </div>
  );
}

function AlgoStrategiesSection({
  items,
  strategyId,
  onDetached,
}: {
  items: AlgoStrategySummary[];
  strategyId: number;
  onDetached: (algoAttachmentId: number) => void;
}) {
  return (
    <div className="space-y-3">
      {items.length === 0 ? (
        <p className="text-slate-500 text-sm">
          No algo strategies yet. Use &quot;+ Strategy&quot; on a backtest result to attach
          strategies with their signal timeframes.
        </p>
      ) : (
        <div className="space-y-2">
          {items.map((item) =>
            item.strategy_name.startsWith('combo:') ? (
              <ComboAlgoRow key={item.algo_attachment_id} item={item} onDetach={onDetached} />
            ) : (
              <AlgoRow key={item.algo_attachment_id} item={item} onDetach={onDetached} />
            ),
          )}
        </div>
      )}

      <p className="text-xs text-slate-500 italic hidden" data-strategy-id={strategyId} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Collapsible Section Wrapper
// ---------------------------------------------------------------------------

function Section({
  title,
  children,
  defaultOpen = false,
}: {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="border-t border-slate-700 pt-3">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between text-left mb-2"
      >
        <span className="text-slate-300 text-sm font-semibold">{title}</span>
        <span className="text-slate-500 text-xs">{open ? '▲' : '▼'}</span>
      </button>
      {open && children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Threshold state helpers
// ---------------------------------------------------------------------------

function numToStr(v: number | null | undefined): string {
  return v != null ? String(v) : '';
}

function strToNum(v: string): number | null {
  const parsed = parseFloat(v);
  return v === '' || isNaN(parsed) ? null : parsed;
}

// ---------------------------------------------------------------------------
// Main Card
// ---------------------------------------------------------------------------

export default function AssetStrategyCard({ strategy, onRemove, onUpdated }: Props) {
  const [data, setData] = useState<StrategyFullResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [removing, setRemoving] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const successTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // MC thresholds (BUY / SELL)
  const [mcBuyProb, setMcBuyProb] = useState(numToStr(strategy.mc_buy_prob_positive));
  const [mcSellProb, setMcSellProb] = useState(numToStr(strategy.mc_sell_prob_positive));

  // AI thresholds (BUY / SELL per score)
  const [aiBuyConviction, setAiBuyConviction] = useState(numToStr(strategy.ai_buy_conviction));
  const [aiSellConviction, setAiSellConviction] = useState(numToStr(strategy.ai_sell_conviction));
  const [aiBuySentiment, setAiBuySentiment] = useState(numToStr(strategy.ai_buy_sentiment));
  const [aiSellSentiment, setAiSellSentiment] = useState(numToStr(strategy.ai_sell_sentiment));
  const [aiBuyMacro, setAiBuyMacro] = useState(numToStr(strategy.ai_buy_macro));
  const [aiSellMacro, setAiSellMacro] = useState(numToStr(strategy.ai_sell_macro));

  // Signal configuration
  const [comboMode, setComboMode] = useState<'all' | 'majority' | 'any'>(strategy.combination_mode);

  // Auto-trading toggle
  const [autoEnabled, setAutoEnabled] = useState(strategy.auto_trading_enabled);
  const [togglingAuto, setTogglingAuto] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const bodyId = `strategy-card-body-${strategy.id}`;

  useEffect(() => {
    strategyBuilderApi
      .getFull(strategy.id)
      .then((d) => {
        setData(d);
        setMcBuyProb(numToStr(d.mc_buy_prob_positive));
        setMcSellProb(numToStr(d.mc_sell_prob_positive));
        setAiBuyConviction(numToStr(d.ai_buy_conviction));
        setAiSellConviction(numToStr(d.ai_sell_conviction));
        setAiBuySentiment(numToStr(d.ai_buy_sentiment));
        setAiSellSentiment(numToStr(d.ai_sell_sentiment));
        setAiBuyMacro(numToStr(d.ai_buy_macro));
        setAiSellMacro(numToStr(d.ai_sell_macro));
        setComboMode(d.combination_mode);
        setAutoEnabled(d.auto_trading_enabled);
      })
      .catch(() => setLoadError('Failed to load strategy data'))
      .finally(() => setLoading(false));
  }, [strategy.id]);

  const handleRemove = async () => {
    setRemoving(true);
    try {
      await strategyBuilderApi.remove(strategy.id);
      onRemove(strategy.id);
    } catch {
      setRemoving(false);
    }
  };

  const handleDetach = async (algoAttachmentId: number) => {
    if (!data) return;
    try {
      await strategyBuilderApi.detachAlgo({
        strategy_id: strategy.id,
        algo_attachment_id: algoAttachmentId,
      });
      setData((prev) =>
        prev
          ? { ...prev, algo_strategies: prev.algo_strategies.filter((a) => a.algo_attachment_id !== algoAttachmentId) }
          : prev,
      );
    } catch {
      // silently ignore
    }
  };

  const handleSaveThresholds = async () => {
    setSaveError(null);
    setSaveSuccess(false);
    setSaving(true);
    try {
      const req: UpdateThresholdsRequest = {
        mc_buy_prob_positive: strToNum(mcBuyProb),
        mc_sell_prob_positive: strToNum(mcSellProb),
        ai_buy_conviction: strToNum(aiBuyConviction),
        ai_sell_conviction: strToNum(aiSellConviction),
        ai_buy_sentiment: strToNum(aiBuySentiment),
        ai_sell_sentiment: strToNum(aiSellSentiment),
        ai_buy_macro: strToNum(aiBuyMacro),
        ai_sell_macro: strToNum(aiSellMacro),
        combination_mode: comboMode,
        auto_trading_enabled: autoEnabled,
      };
      const updated = await strategyBuilderApi.updateThresholds(strategy.id, req);
      onUpdated(updated);
      setSaveSuccess(true);
      successTimerRef.current = setTimeout(() => setSaveSuccess(false), 3000);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        ?? 'Failed to save thresholds.';
      setSaveError(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleToggleAutoTrading = async (enabled: boolean) => {
    setTogglingAuto(true);
    try {
      const updated = await strategyBuilderApi.updateThresholds(strategy.id, {
        auto_trading_enabled: enabled,
      });
      setAutoEnabled(enabled);
      onUpdated(updated);
    } catch {
      // revert on failure
    } finally {
      setTogglingAuto(false);
    }
  };

  const mcThresholds: MCThresholds = { buyProb: mcBuyProb, sellProb: mcSellProb };
  const aiThresholds: AIThresholds = {
    buyConviction: aiBuyConviction, sellConviction: aiSellConviction,
    buySentiment: aiBuySentiment, sellSentiment: aiSellSentiment,
    buyMacro: aiBuyMacro, sellMacro: aiSellMacro,
  };

  return (
    <div className="card space-y-3">
      {/* Card header */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setExpanded((e) => !e)}
            className="flex items-center gap-2 text-left min-w-0"
            aria-expanded={expanded}
            aria-controls={bodyId}
            aria-label={expanded ? 'Collapse strategy details' : 'Expand strategy details'}
          >
            <span className="text-slate-500 text-xs shrink-0">{expanded ? '▲' : '▼'}</span>
            <span className="text-brand-500 font-bold text-base">{strategy.symbol}</span>
            {strategy.asset_name && (
              <span className="text-slate-400 text-sm truncate">{strategy.asset_name}</span>
            )}
          </button>
          {!expanded && loading && <Spinner size="sm" />}
        </div>

        <div className="flex items-center gap-3">
          {/* Auto-trading toggle */}
          <div className="flex items-center gap-2">
            <span className="text-slate-400 text-xs">Auto-Trading</span>
            {togglingAuto ? (
              <Spinner size="sm" />
            ) : (
              <button
                onClick={() => handleToggleAutoTrading(!autoEnabled)}
                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none ${
                  autoEnabled ? 'bg-brand-500' : 'bg-slate-700'
                }`}
                aria-label="Toggle auto-trading"
              >
                <span
                  className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                    autoEnabled ? 'translate-x-4.5' : 'translate-x-0.5'
                  }`}
                />
              </button>
            )}
          </div>

          <button
            onClick={handleRemove}
            disabled={removing}
            className="text-slate-500 hover:text-red-400 text-xs transition-colors"
            title="Delete strategy card"
          >
            {removing ? <Spinner size="sm" /> : 'Delete'}
          </button>
        </div>
      </div>

      {loadError && <ErrorAlert message={loadError} />}

      {expanded && (
        <div id={bodyId} className="space-y-3">
          {loading && (
            <div className="flex justify-center py-6">
              <Spinner />
            </div>
          )}

          {data && (
            <>
              <Section title="Monte Carlo (Merton Jump-Diffusion)">
            <MonteCarloSection
              data={data.monte_carlo}
              error={data.monte_carlo_error}
              thresholds={mcThresholds}
              onThresholdChange={(key, v) => {
                if (key === 'buyProb') setMcBuyProb(v);
                else setMcSellProb(v);
              }}
            />
          </Section>

          <Section title="AI Agents">
            <AIAgentsSection
              data={data.ai_agents}
              error={data.ai_agents_error}
              thresholds={aiThresholds}
              onThresholdChange={(key, v) => {
                const setters: Record<AIThresholdKey, (val: string) => void> = {
                  buyConviction: setAiBuyConviction,
                  sellConviction: setAiSellConviction,
                  buySentiment: setAiBuySentiment,
                  sellSentiment: setAiSellSentiment,
                  buyMacro: setAiBuyMacro,
                  sellMacro: setAiSellMacro,
                };
                setters[key](v);
              }}
            />
          </Section>

          <Section title="Financials">
            <FinancialsSection data={data.financials} error={data.financials_error} />
          </Section>

          <Section title="Algo Strategies">
            <AlgoStrategiesSection
              items={data.algo_strategies}
              strategyId={strategy.id}
              onDetached={handleDetach}
            />
          </Section>

          {/* Combination mode + Save */}
          <div className="border-t border-slate-700 pt-4 space-y-3">
            <div className="flex items-center gap-3">
              <label className="text-slate-400 text-xs w-36 shrink-0">Signal Combination</label>
              <select
                value={comboMode}
                onChange={(e) => setComboMode(e.target.value as 'all' | 'majority' | 'any')}
                className="bg-surface-800 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
              >
                <option value="all">All Agree (AND)</option>
                <option value="majority">Majority Vote</option>
                <option value="any">Any One (OR)</option>
              </select>
            </div>

            {saveError && <p className="text-xs text-red-400">{saveError}</p>}
            {saveSuccess && <p className="text-xs text-green-400">Thresholds saved successfully.</p>}

            <div className="flex justify-end">
              <button
                onClick={handleSaveThresholds}
                disabled={saving}
                className="btn-primary flex items-center gap-2 text-sm"
              >
                {saving ? <Spinner size="sm" /> : null}
                Save Thresholds
              </button>
            </div>
          </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
