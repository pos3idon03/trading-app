import type { NewsArticle } from '../api/types';

export function sentimentBadgeClass(label: string | undefined): string {
  if (label === 'positive') return 'bg-emerald-900/50 text-emerald-300 border-emerald-700';
  if (label === 'negative') return 'bg-rose-900/50 text-rose-300 border-rose-700';
  return 'bg-slate-800 text-slate-300 border-slate-700';
}

export function sentimentLabel(label: string | undefined): string {
  if (label === 'positive') return 'Bullish';
  if (label === 'negative') return 'Bearish';
  if (label === 'neutral') return 'Neutral';
  return 'Unscored';
}

export function formatSentimentConfidence(
  sentiment: { confidence?: number; refined_confidence?: number } | null | undefined,
): string {
  if (!sentiment) return '';
  const value = sentiment.confidence ?? sentiment.refined_confidence;
  if (value == null) return '';
  return `${Math.round(value * 100)}%`;
}

export function effectiveBadgeLabel(article: {
  effective_label?: string | null;
  effective_sentiment?: { label?: string } | null;
  sentiment?: { label?: string } | null;
}): string {
  const label = article.effective_label ?? article.effective_sentiment?.label ?? article.sentiment?.label;
  return sentimentLabel(label);
}

export function effectiveBadgeClass(article: {
  effective_label?: string | null;
  effective_sentiment?: { label?: string } | null;
  sentiment?: { label?: string } | null;
}): string {
  const label = article.effective_label ?? article.effective_sentiment?.label ?? article.sentiment?.label;
  return sentimentBadgeClass(label);
}

export function sentimentOverrideText(article: {
  sentiment?: { label?: string } | null;
  sentiment_refined?: { refined_label?: string; label?: string } | null;
  effective_sentiment?: { source?: string } | null;
}): string | null {
  if (article.effective_sentiment?.source !== 'gemini') return null;
  const finbert = sentimentLabel(article.sentiment?.label);
  const gemini = sentimentLabel(
    article.sentiment_refined?.refined_label ?? article.sentiment_refined?.label,
  );
  return `FinBERT: ${finbert} → Gemini: ${gemini}`;
}
