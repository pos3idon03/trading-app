import { useEffect, useState } from 'react';
import { ingestionApi } from '../../api/endpoints';
import type { NewsArticle } from '../../api/types';
import Spinner from '../../components/Spinner';

export default function NewsTab() {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState<string | null>(null);

  const load = async () => {
    const data = await ingestionApi.listNews(30);
    setArticles(data.articles);
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const runIngest = async () => {
    const r = await ingestionApi.runNews({ symbols: [], limit: 100 });
    setMsg(`Job queued: ${r.job_id}`);
    setTimeout(load, 3000);
  };

  if (loading) return <div className="flex justify-center py-12"><Spinner /></div>;

  return (
    <div className="space-y-4">
      <button type="button" onClick={runIngest} className="px-4 py-2 bg-brand-600 rounded-lg text-sm">
        Fetch News (Watchlist)
      </button>
      {msg && <p className="text-brand-500 text-sm">{msg}</p>}
      <ul className="space-y-3">
        {articles.map((a) => (
          <li key={a.id} className="bg-surface-900 border border-slate-800 rounded-lg p-4">
            <a href={a.url} target="_blank" rel="noreferrer" className="text-brand-500 font-medium hover:underline">
              {a.title}
            </a>
            <p className="text-xs text-slate-500 mt-1">
              {new Date(a.published_at).toLocaleString()} — {(a.tickers ?? []).join(', ')}
            </p>
            {a.description && <p className="text-sm text-slate-400 mt-2 line-clamp-2">{a.description}</p>}
          </li>
        ))}
      </ul>
    </div>
  );
}
