import type { MarketSentimentPoint } from '../api/types';

export const MARKET_SENTIMENT_NEUTRAL = 50;

export interface MarketSentimentChartPoint {
  time: string;
  score: number;
  article_count: number;
  bullish_count: number;
  bearish_count: number;
  neutral_count: number;
}

export function formatMarketSentimentScore(score: number): string {
  return `${Math.round(score)} / 100`;
}

export function marketSentimentBadgeClass(score: number): string {
  if (score >= 55) return 'bg-emerald-900/50 text-emerald-300 border-emerald-700';
  if (score <= 45) return 'bg-rose-900/50 text-rose-300 border-rose-700';
  return 'bg-slate-800 text-slate-300 border-slate-700';
}

export function toMarketSentimentChartData(
  points: MarketSentimentPoint[],
): MarketSentimentChartPoint[] {
  return points.map((point) => ({
    time: point.recorded_at,
    score: point.score,
    article_count: point.article_count,
    bullish_count: point.bullish_count,
    bearish_count: point.bearish_count,
    neutral_count: point.neutral_count,
  }));
}

export function marketSentimentEmptyMessage(
  available: boolean,
  message?: string | null,
): string {
  if (!available) {
    return message ?? 'Sentiment analysis is disabled.';
  }
  return message ?? 'Enable sentiment scoring and fetch news from Ingestion → News.';
}

export function formatChartTime(value: string): string {
  const date = new Date(value);
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}
