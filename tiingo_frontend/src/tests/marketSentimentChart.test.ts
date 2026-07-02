import { describe, expect, it } from 'vitest';
import {
  formatMarketSentimentScore,
  MARKET_SENTIMENT_NEUTRAL,
  marketSentimentBadgeClass,
  marketSentimentEmptyMessage,
  toMarketSentimentChartData,
} from '../utils/marketSentimentChart';

describe('marketSentimentChart utils', () => {
  it('formats score as 0-100 display', () => {
    expect(formatMarketSentimentScore(72.5)).toBe('73 / 100');
    expect(formatMarketSentimentScore(50)).toBe('50 / 100');
    expect(formatMarketSentimentScore(0)).toBe('0 / 100');
  });

  it('uses neutral midpoint constant', () => {
    expect(MARKET_SENTIMENT_NEUTRAL).toBe(50);
  });

  it('maps badge classes by 0-100 score', () => {
    expect(marketSentimentBadgeClass(72)).toContain('emerald');
    expect(marketSentimentBadgeClass(30)).toContain('rose');
    expect(marketSentimentBadgeClass(50)).toContain('slate');
  });

  it('builds chart data from API points', () => {
    const data = toMarketSentimentChartData([
      {
        recorded_at: '2024-06-01T12:00:00Z',
        score: 72.5,
        article_count: 3,
        bullish_count: 2,
        bearish_count: 0,
        neutral_count: 1,
      },
    ]);
    expect(data).toEqual([
      {
        time: '2024-06-01T12:00:00Z',
        score: 72.5,
        article_count: 3,
        bullish_count: 2,
        bearish_count: 0,
        neutral_count: 1,
      },
    ]);
  });

  it('returns disabled message when sentiment unavailable', () => {
    expect(marketSentimentEmptyMessage(false, 'Sentiment disabled')).toBe('Sentiment disabled');
    expect(marketSentimentEmptyMessage(true)).toContain('Ingestion');
  });
});
