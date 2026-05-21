export function backfillStartedMessage(symbol: string): string {
  return `Backfill for stock "${symbol}" has started.`;
}

export function deleteSuccessMessage(symbol: string): string {
  return `"${symbol}" removed from watchlist.`;
}

export function deleteConfirmMessage(symbol: string): string {
  return `Remove ${symbol} from the watchlist? All ingested OHLCV and fundamentals for this symbol will be deleted.`;
}
