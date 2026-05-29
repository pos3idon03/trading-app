import { describe, expect, it } from 'vitest';

import type { NewsArticle } from '../api/types';
import {
  effectiveBadgeClass,
  effectiveBadgeLabel,
  formatSentimentConfidence,
  sentimentLabel,
  sentimentOverrideText,
} from '../utils/newsSentiment';

describe('newsSentiment utils', () => {
  it('maps labels to badge classes', () => {
    expect(effectiveBadgeClass({ effective_label: 'positive' })).toContain('emerald');
    expect(effectiveBadgeClass({ effective_label: 'negative' })).toContain('rose');
  });

  it('formats refined confidence', () => {
    expect(formatSentimentConfidence({ refined_confidence: 0.812 })).toBe('81%');
  });

  it('shows override text when gemini refines neutral', () => {
    const article: NewsArticle = {
      id: 1,
      published_at: '2024-01-01',
      title: 'Test',
      url: 'https://example.com',
      tickers: [],
      tags: [],
      sentiment: { label: 'neutral', confidence: 0.58, score_positive: 0.2, score_negative: 0.2, score_neutral: 0.6 },
      sentiment_refined: { refined_label: 'positive', refined_confidence: 0.72, rationale: 'Growth' },
      effective_sentiment: { label: 'positive', confidence: 0.72, source: 'gemini' },
    };
    expect(sentimentOverrideText(article)).toBe('FinBERT: Neutral → Gemini: Bullish');
    expect(effectiveBadgeLabel(article)).toBe('Bullish');
  });

  it('labels unscored articles', () => {
    expect(sentimentLabel(undefined)).toBe('Unscored');
  });
});
