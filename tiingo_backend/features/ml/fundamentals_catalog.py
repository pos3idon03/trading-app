FUNDAMENTAL_METRIC_CODES: list[str] = [
    "revenue",
    "grossProfit",
    "opinc",
    "netinc",
    "eps",
    "ebitda",
    "freeCashFlow",
    "ncfo",
    "totalAssets",
    "debt",
    "equity",
    "roe",
    "roa",
    "debtEquity",
    "grossMargin",
    "profitMargin",
    "currentRatio",
]

DEFAULT_FUNDAMENTAL_METRICS: list[str] = list(FUNDAMENTAL_METRIC_CODES)

SUPPORTED_PERIOD_TYPES = frozenset({"quarterly", "annual"})

FUNDAMENTAL_METRIC_CODES_SET = frozenset(FUNDAMENTAL_METRIC_CODES)
