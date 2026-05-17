/**
 * Match app symbols (BTC-USD) to Alpaca stream tickers (BTC/USD) for subscription checks.
 */

/** Normalize to a comparable stream key (Alpaca-style slash form). */
export function streamSymbolKey(symbol: string): string {
  const upper = symbol.trim().toUpperCase();
  if (upper.includes('/')) {
    return upper;
  }
  if (upper.includes('-') && /^[A-Z0-9]+-[A-Z]{3,}$/.test(upper)) {
    const [base, quote] = upper.split('-', 2);
    return `${base}/${quote}`;
  }
  return upper;
}

/** True when monitor symbol is covered by a subscribed_symbols entry. */
export function isSymbolSubscribed(
  symbol: string,
  subscribed: string[],
): boolean {
  const key = streamSymbolKey(symbol);
  return subscribed.some((s) => streamSymbolKey(s) === key);
}
