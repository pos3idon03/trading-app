ALTER TABLE ohlcv
  ADD COLUMN IF NOT EXISTS div_cash DOUBLE PRECISION NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS split_factor DOUBLE PRECISION NOT NULL DEFAULT 1;

COMMENT ON COLUMN ohlcv.div_cash IS 'Tiingo EOD divCash — dividend on ex-date';
COMMENT ON COLUMN ohlcv.split_factor IS 'Tiingo EOD splitFactor — split ratio (1.0 = none)';
