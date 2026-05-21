DOW_30_SYMBOLS = {
    "AAPL", "AMGN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "DOW",
    "GS", "HD", "HON", "IBM", "INTC", "JNJ", "JPM", "KO", "MCD", "MMM",
    "MRK", "MSFT", "NKE", "PG", "TRV", "UNH", "V", "VZ", "WMT", "WBA",
}


def is_fundamentals_entitled(symbol: str, tier: str) -> bool:
    sym = symbol.upper()
    if tier.startswith("addon_"):
        return True
    return sym in DOW_30_SYMBOLS
