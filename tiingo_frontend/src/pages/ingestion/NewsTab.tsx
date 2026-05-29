import { useEffect, useState } from 'react';
import { ingestionApi } from '../../api/endpoints';
import type { NewsArticle } from '../../api/types';
import Spinner from '../../components/Spinner';
import {
  effectiveBadgeClass,
  effectiveBadgeLabel,
  formatSentimentConfidence,
  sentimentOverrideText,
} from '../../utils/newsSentiment';

export default function NewsTab() {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const load = async () => {
    const data = await ingestionApi.listNews(30, true);
    setArticles(data.articles);
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const runIngest = async () => {
    const r = await ingestionApi.runNews({ symbols: [], limit: 100 });
    setMsg(`Job queued: ${r.job_id}`);
    setTimeout(load, 3000);
  };

  const runSentiment = async () => {
    const r = await ingestionApi.runNewsSentiment({ backfill: true });
    setMsg(`Sentiment job queued: ${r.job_id}`);
    setTimeout(load, 5000);
  };

  const runEnrichment = async () => {
    const r = await ingestionApi.runNewsSentimentEnrich({});
    setMsg(`Gemini enrichment job queued: ${r.job_id}`);
    setTimeout(load, 8000);
  };

  if (loading) return <div className="flex justify-center py-12"><Spinner /></div>;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={runIngest} className="px-4 py-2 bg-brand-600 rounded-lg text-sm">
          Fetch News (Watchlist)
        </button>
        <button type="button" onClick={runSentiment} className="px-4 py-2 bg-slate-700 rounded-lg text-sm">
          Score Pending Sentiment
        </button>
        <button type="button" onClick={runEnrichment} className="px-4 py-2 bg-slate-700 rounded-lg text-sm">
          Enrich Neutral (Gemini)
        </button>
      </div>
      {msg && <p className="text-brand-500 text-sm">{msg}</p>}
      <ul className="space-y-3">
        {articles.map((a) => {
          const override = sentimentOverrideText(a);
          const confidence = a.effective_sentiment ?? a.sentiment_refined ?? a.sentiment;
          return (
            <li key={a.id} className="bg-surface-900 border border-slate-800 rounded-lg p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <a href={a.url} target="_blank" rel="noreferrer" className="text-brand-500 font-medium hover:underline">
                  {a.title}
                </a>
                <span className={`text-xs px-2 py-1 rounded border ${effectiveBadgeClass(a)}`}>
                  {effectiveBadgeLabel(a)}
                  {confidence ? ` · ${formatSentimentConfidence(confidence)}` : ''}
                </span>
              </div>
              {override && <p className="text-xs text-slate-400 mt-1">{override}</p>}
              <p className="text-xs text-slate-500 mt-1">
                {new Date(a.published_at).toLocaleString()} — {(a.tickers ?? []).join(', ')}
              </p>
              {a.description && <p className="text-sm text-slate-400 mt-2 line-clamp-2">{a.description}</p>}
              {a.sentiment_refined?.rationale && (
                <div className="mt-3">
                  <button
                    type="button"
                    className="text-xs text-brand-400 hover:underline"
                    onClick={() => setExpandedId(expandedId === a.id ? null : a.id)}
                  >
                    {expandedId === a.id ? 'Hide Gemini analysis' : 'Show Gemini analysis'}
                  </button>
                  {expandedId === a.id && (
                    <div className="mt-2 space-y-2 text-sm text-slate-300">
                      <p>{a.sentiment_refined.rationale}</p>
                      {(a.sentiment_refined.citations ?? []).length > 0 && (
                        <ul className="text-xs text-slate-400 space-y-1">
                          {(a.sentiment_refined.citations ?? []).map((citation) => (
                            <li key={citation.url ?? citation.title ?? Math.random()}>
                              {citation.url ? (
                                <a href={citation.url} target="_blank" rel="noreferrer" className="hover:underline">
                                  {citation.title ?? citation.url}
                                </a>
                              ) : (
                                citation.title
                              )}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
