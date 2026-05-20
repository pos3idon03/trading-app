-- Reclassify yfinance-style crypto tickers (BASE-QUOTE) misstored as stock/etf.
-- Matches backend _looks_like_yfinance_crypto_pair (excludes BRK-B, BARC.L, etc.).

UPDATE assets
SET asset_type = 'crypto'
WHERE asset_type IN ('stock', 'etf')
  AND symbol !~ '\.'
  AND symbol ~ '^[A-Z0-9]{2,}-(USD|USDT|USDC|GBP|EUR|JPY|AUD|CAD|CHF|INR|KRW|TRY|BRL|MXN|HKD|NOK|SEK|NZD|PLN|ZAR|SGD|CNY|BTC|ETH|DAI|BUSD)$';
