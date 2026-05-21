export function backfillStartedMessage(symbol: string): string {
  return `Full ingest for "${symbol}" has started. Track progress in the Jobs tab.`;
}

export function ingestStartedMessage(symbol: string, jobId: string): string {
  return `"${symbol}" added. Full ingest queued (job ${jobId.slice(0, 8)}…). See Jobs tab.`;
}

export function deleteSuccessMessage(symbol: string): string {
  return `"${symbol}" removed from watchlist.`;
}

export function deleteConfirmMessage(symbol: string): string {
  return `Remove ${symbol} from the watchlist? All ingested OHLCV and fundamentals for this symbol will be deleted.`;
}
