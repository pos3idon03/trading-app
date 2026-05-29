SERIES_ID_ALIASES: dict[str, str] = {
    "USRECNBER": "USRECM",
}

SERIES_CATALOG: dict[str, dict] = {
    "GDPC1": {"title": "Real Gross Domestic Product", "frequency": "Quarterly", "category": "growth"},
    "INDPRO": {"title": "Industrial Production Index", "frequency": "Monthly", "category": "growth"},
    "USRECM": {"title": "NBER Recession Indicator", "frequency": "Monthly", "category": "growth"},
    "UNRATE": {"title": "Unemployment Rate", "frequency": "Monthly", "category": "labor"},
    "PAYEMS": {"title": "Total Nonfarm Payrolls", "frequency": "Monthly", "category": "labor"},
    "ICSA": {"title": "Initial Claims", "frequency": "Weekly", "category": "labor"},
    "JTSJOL": {"title": "Job Openings (JOLTS)", "frequency": "Monthly", "category": "labor"},
    "CPIAUCSL": {"title": "CPI All Urban Consumers", "frequency": "Monthly", "category": "inflation"},
    "CPILFESL": {"title": "Core CPI", "frequency": "Monthly", "category": "inflation"},
    "PCEPI": {"title": "PCE Price Index", "frequency": "Monthly", "category": "inflation"},
    "RSAFS": {"title": "Real Retail Sales", "frequency": "Monthly", "category": "consumer"},
    "UMCSENT": {"title": "Michigan Consumer Sentiment", "frequency": "Monthly", "category": "consumer"},
    "PSAVERT": {"title": "Personal Saving Rate", "frequency": "Monthly", "category": "consumer"},
    "DFF": {"title": "Effective Federal Funds Rate", "frequency": "Daily", "category": "rates"},
    "DGS2": {"title": "2-Year Treasury", "frequency": "Daily", "category": "rates"},
    "DGS10": {"title": "10-Year Treasury", "frequency": "Daily", "category": "rates"},
    "T10Y2Y": {"title": "10Y-2Y Spread", "frequency": "Daily", "category": "rates"},
    "STLFSI4": {"title": "St. Louis Fed Financial Stress Index", "frequency": "Weekly", "category": "rates"},
    "WALCL": {"title": "Fed Total Assets (Balance Sheet)", "frequency": "Weekly", "category": "rates"},
    "WTREGEN": {
        "title": "Treasury General Account (TGA)",
        "frequency": "Weekly",
        "category": "rates",
    },
    "CSUSHPINSA": {"title": "Case-Shiller Home Price", "frequency": "Monthly", "category": "housing"},
    "HOUST": {"title": "Housing Starts", "frequency": "Monthly", "category": "housing"},
    "MSACSR": {"title": "Housing Inventory", "frequency": "Monthly", "category": "housing"},
    "DCOILWTICO": {"title": "WTI Crude Oil", "frequency": "Daily", "category": "energy"},
    "GASREGW": {"title": "US Regular Gas Price", "frequency": "Weekly", "category": "energy"},
    "PPIACO": {"title": "PPI All Commodities", "frequency": "Monthly", "category": "goods"},
}


def normalize_series_id(series_id: str) -> str:
    key = series_id.strip().upper()
    return SERIES_ID_ALIASES.get(key, key)


def validate_series_ids(series_ids: list[str]) -> list[str]:
    if not series_ids:
        return []
    normalized = [normalize_series_id(item) for item in series_ids if item.strip()]
    unknown = [sid for sid in normalized if sid not in SERIES_CATALOG]
    if unknown:
        hints = [f"{sid} (did you mean USRECM?)" for sid in unknown if "USREC" in sid]
        detail = f" Unknown: {', '.join(unknown)}."
        if hints:
            detail += f" Hints: {', '.join(hints)}."
        raise ValueError(f"Invalid FRED series id(s).{detail}")
    return normalized


def catalog_rows() -> list[dict]:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    return [
        {
            "series_id": sid,
            "title": meta["title"],
            "frequency": meta["frequency"],
            "category": meta["category"],
            "is_enabled": False,
            "created_at": now,
            "updated_at": now,
        }
        for sid, meta in SERIES_CATALOG.items()
    ]
