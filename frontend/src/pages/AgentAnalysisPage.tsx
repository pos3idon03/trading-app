import { useEffect, useState } from 'react';
import { agentApi, dataApi } from '../api/endpoints';
import type { AgentAnalysisResponse, AgentReports, AssetItem, TradingSignal } from '../api/types';
import Spinner from '../components/Spinner';
import ErrorAlert from '../components/ErrorAlert';
import StatusBadge from '../components/StatusBadge';
import RangeScoreBar from '../components/RangeScoreBar';
import { formatAssetOptionLabel } from '../utils/assetDisplay';

const LLM_OPTIONS = [
  { group: 'OpenAI', value: 'gpt-4o-mini', label: 'GPT-4o Mini — fast (fallback: Gemini 3 Flash)' },
  { group: 'OpenAI', value: 'gpt-4o', label: 'GPT-4o — thorough (fallback: Gemini 3.1 Pro)' },
  { group: 'Gemini (Google AI Studio)', value: 'gemini-3-flash-preview', label: 'Gemini 3 Flash Preview — fast (fallback: GPT-4o Mini)' },
  { group: 'Gemini (Google AI Studio)', value: 'gemini-3.1-pro-preview', label: 'Gemini 3.1 Pro Preview — thorough (fallback: GPT-4o)' },
];

const LLM_GROUPS = ['OpenAI', 'Gemini (Google AI Studio)'];


function BiasChip({ bias }: { bias: string }) {
  const styles: Record<string, string> = {
    bullish: 'bg-green-500/20 text-green-400 border border-green-500/40',
    bearish: 'bg-red-500/20 text-red-400 border border-red-500/40',
    neutral: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/40',
  };
  return (
    <span className={`px-3 py-1 rounded-full text-sm font-semibold uppercase tracking-wide ${styles[bias] ?? styles.neutral}`}>
      {bias}
    </span>
  );
}

function AgentReportCard({ title, report }: { title: string; report?: string | null }) {
  const [expanded, setExpanded] = useState(false);
  if (!report) return null;
  const preview = report.slice(0, 300);
  return (
    <div className="card">
      <button
        className="w-full flex items-center justify-between text-left"
        onClick={() => setExpanded((v) => !v)}
      >
        <h3 className="text-slate-200 font-semibold text-sm">{title}</h3>
        <span className="text-slate-400 text-xs">{expanded ? '▲ collapse' : '▼ expand'}</span>
      </button>
      <div className={`mt-3 text-slate-400 text-xs font-mono leading-relaxed whitespace-pre-wrap overflow-hidden transition-all ${expanded ? 'max-h-none' : 'max-h-24'}`}>
        {expanded ? report : preview + (report.length > 300 ? '…' : '')}
      </div>
    </div>
  );
}

function SignalCard({ signal, duration_ms }: { signal: TradingSignal; duration_ms?: number }) {
  return (
    <div className="space-y-4">
      <div className="card border border-slate-600">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <span className="text-2xl font-bold text-slate-100">{signal.asset}</span>
            <BiasChip bias={signal.bias} />
          </div>
          {duration_ms && (
            <span className="text-slate-500 text-xs">{(duration_ms / 1000).toFixed(1)}s</span>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-4">
          <RangeScoreBar label="Conviction" value={signal.conviction_score} min={0} max={1} />
          <RangeScoreBar label="Sentiment Score" value={signal.sentiment_score} min={-1} max={1} />
          <RangeScoreBar label="Macro Score" value={signal.macro_score} min={-1} max={1} />
        </div>

        <div className="space-y-3 border-t border-slate-700 pt-4">
          <div>
            <span className="text-slate-500 text-xs uppercase tracking-wide">Reasoning</span>
            <p className="text-slate-300 text-sm mt-1">{signal.reasoning}</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <span className="text-slate-500 text-xs uppercase tracking-wide">Fundamental</span>
              <p className="text-slate-400 text-xs mt-1">{signal.fundamental_summary}</p>
            </div>
            <div>
              <span className="text-slate-500 text-xs uppercase tracking-wide">Macro</span>
              <p className="text-slate-400 text-xs mt-1">{signal.macro_summary}</p>
            </div>
          </div>
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20">
            <span className="text-red-400 text-xs font-semibold uppercase tracking-wide">Key Risk</span>
            <p className="text-slate-300 text-sm mt-1">{signal.key_risk}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AgentAnalysisPage() {
  const [assets, setAssets] = useState<AssetItem[]>([]);
  const [symbol, setSymbol] = useState('');
  const [customSymbol, setCustomSymbol] = useState('');
  const [useCustom, setUseCustom] = useState(false);
  const [llm, setLlm] = useState('gpt-4o-mini');
  const [result, setResult] = useState<AgentAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    dataApi.getAssets().then((resp) => {
      const active = resp.assets.filter((a) => a.is_active);
      setAssets(active);
      if (active.length > 0) setSymbol(active[0].symbol);
    });
  }, []);

  const activeSymbol = useCustom ? customSymbol.trim().toUpperCase() : symbol;

  const runAnalysis = async () => {
    if (!activeSymbol) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await agentApi.analyze({ symbol: activeSymbol, llm });
      setResult(resp);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">AI Agent Analysis</h1>
        <p className="text-slate-400 text-sm mt-1">
          Multi-agent research crew: fundamental (SEC), macroeconomic (FRED), and sentiment (news) analysts
          synthesized by a manager agent into a structured trading signal.
        </p>
      </div>

      {error && <ErrorAlert message={error} />}

      <div className="card">
        <h2 className="text-slate-200 font-semibold mb-4">Analysis Configuration</h2>
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="metric-label block mb-1">Asset</label>
            <div className="flex items-center gap-2">
              {!useCustom ? (
                <select
                  className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  disabled={assets.length === 0}
                >
                  {assets.length === 0 && <option value="">Loading…</option>}
                  {assets.map((a) => (
                    <option key={a.id} value={a.symbol}>
                      {formatAssetOptionLabel(a)}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500 w-32 uppercase"
                  placeholder="e.g. NVDA"
                  value={customSymbol}
                  onChange={(e) => setCustomSymbol(e.target.value)}
                />
              )}
              <button
                className="text-slate-400 text-xs hover:text-slate-200 underline"
                onClick={() => setUseCustom((v) => !v)}
              >
                {useCustom ? 'Use list' : 'Custom ticker'}
              </button>
            </div>
          </div>

          <div>
            <label className="metric-label block mb-1">LLM Model</label>
            <select
              className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
              value={llm}
              onChange={(e) => setLlm(e.target.value)}
            >
              {LLM_GROUPS.map((group) => (
                <optgroup key={group} label={group}>
                  {LLM_OPTIONS.filter((o) => o.group === group).map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>

          <button
            onClick={runAnalysis}
            disabled={loading || !activeSymbol}
            className="btn-primary disabled:opacity-50"
          >
            {loading ? 'Analyzing…' : 'Run Analysis'}
          </button>
        </div>

        <div className="mt-4 p-3 bg-surface-900 rounded-lg border border-slate-700">
          <p className="text-slate-500 text-xs">
            <strong className="text-slate-400">Agents:</strong> Fundamental (SEC EDGAR 10-K/10-Q) &bull;
            Macroeconomic (FRED rates, CPI, yield curve) &bull; Sentiment (NewsAPI headlines) &bull;
            Manager (synthesis into trading signal)
          </p>
          <p className="text-slate-500 text-xs mt-1">
            OpenAI models require <code className="text-slate-400">OPENAI_API_KEY</code>.
            Gemini models require <code className="text-slate-400">GEMINI_API_KEY</code> (Google AI Studio).
            Each model automatically falls back to its paired provider on failure when{' '}
            <code className="text-slate-400">LLM_FALLBACK_ENABLED=true</code>.
            Also requires <code className="text-slate-400">NEWSAPI_KEY</code> and{' '}
            <code className="text-slate-400">FRED_API_KEY</code>. Analysis typically takes 60–120 seconds.
          </p>
        </div>
      </div>

      {loading && (
        <div className="space-y-3">
          <Spinner label={`Running multi-agent analysis for ${activeSymbol}…`} />
          <div className="flex gap-2 flex-wrap">
            {['Fundamental Agent', 'Macro Agent', 'Sentiment Agent', 'Manager Synthesis'].map((step) => (
              <span key={step} className="px-2 py-1 text-xs rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20 animate-pulse">
                {step}
              </span>
            ))}
          </div>
        </div>
      )}

      {result && !loading && (
        <>
          <div className="flex items-center gap-3 flex-wrap">
            <StatusBadge status={result.status} />
            <span className="text-slate-400 text-sm">
              Analysis #{result.analysis_id} &bull; {result.symbol}
            </span>
            {result.provider_used && (
              <span className="text-slate-500 text-xs font-mono px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                {result.provider_used}
              </span>
            )}
          </div>

          {result.error_message && <ErrorAlert message={result.error_message} />}

          {result.signal && (
            <SignalCard signal={result.signal} duration_ms={result.duration_ms} />
          )}

          {result.reports && (
            <div className="space-y-3">
              <h3 className="text-slate-300 font-semibold text-sm">Agent Reports</h3>
              <AgentReportCard title="Fundamental Analysis (SEC Filings)" report={result.reports.fundamental} />
              <AgentReportCard title="Macroeconomic Analysis (FRED)" report={result.reports.macro} />
              <AgentReportCard title="News Sentiment Analysis" report={result.reports.sentiment} />
            </div>
          )}
        </>
      )}
    </div>
  );
}
