import { useCallback, useEffect, useMemo, useState } from 'react';
import { marketDataApi } from '../../api/endpoints';
import type { MarketSentimentResponse } from '../../api/types';
import MarketSentimentChart from '../charts/MarketSentimentChart';
import ErrorAlert from '../ErrorAlert';
import Spinner from '../Spinner';
import {
  formatMarketSentimentScore,
  marketSentimentBadgeClass,
  marketSentimentEmptyMessage,
  toMarketSentimentChartData,
} from '../../utils/marketSentimentChart';

const POLL_MS = 60_000;

export default function MarketSentimentPanel() {
  const [data, setData] = useState<MarketSentimentResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const response = await marketDataApi.getMarketSentiment();
      setData(response);
      setError(null);
    } catch (e) {
      setData(null);
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const timer = window.setInterval(load, POLL_MS);
    return () => window.clearInterval(timer);
  }, [load]);

  const chartData = useMemo(
    () => toMarketSentimentChartData(data?.points ?? []),
    [data?.points],
  );
  const emptyMessage = marketSentimentEmptyMessage(
    data?.available ?? false,
    data?.message,
  );

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-200">Market Sentiment</h2>
          <p className="text-sm text-slate-500 mt-1">
            Rolling {data?.window_hours ?? 24}h confidence-weighted score (0–100) from watchlist news.
          </p>
        </div>
        {data?.available && data.points.length > 0 && (
          <span
            className={`text-sm px-3 py-1 rounded border ${marketSentimentBadgeClass(data.current_score)}`}
          >
            {formatMarketSentimentScore(data.current_score)} · {data.window_hours}h rolling
            {' · '}
            {data.current_article_count} articles
          </span>
        )}
      </div>
      {error && <ErrorAlert message={error} />}
      {loading ? (
        <div className="flex justify-center py-10">
          <Spinner />
        </div>
      ) : (
        <MarketSentimentChart data={chartData} emptyMessage={emptyMessage} />
      )}
    </section>
  );
}
