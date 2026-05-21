SERIES_CATALOG: dict[str, dict] = {
    "CPIAUCSL": {"title": "CPI All Urban Consumers", "frequency": "Monthly", "category": "inflation"},
    "CPILFESL": {"title": "Core CPI", "frequency": "Monthly", "category": "inflation"},
    "PCEPI": {"title": "PCE Price Index", "frequency": "Monthly", "category": "inflation"},
    "UNRATE": {"title": "Unemployment Rate", "frequency": "Monthly", "category": "labor"},
    "PAYEMS": {"title": "Total Nonfarm Payrolls", "frequency": "Monthly", "category": "labor"},
    "DFF": {"title": "Federal Funds Rate", "frequency": "Daily", "category": "rates"},
    "DGS2": {"title": "2-Year Treasury", "frequency": "Daily", "category": "rates"},
    "DGS10": {"title": "10-Year Treasury", "frequency": "Daily", "category": "rates"},
    "T10Y2Y": {"title": "10Y-2Y Spread", "frequency": "Daily", "category": "rates"},
    "CSUSHPINSA": {"title": "Case-Shiller Home Price", "frequency": "Monthly", "category": "housing"},
    "HOUST": {"title": "Housing Starts", "frequency": "Monthly", "category": "housing"},
    "MSACSR": {"title": "Housing Inventory", "frequency": "Monthly", "category": "housing"},
    "DCOILWTICO": {"title": "WTI Crude Oil", "frequency": "Daily", "category": "energy"},
    "GASREGW": {"title": "US Regular Gas Price", "frequency": "Weekly", "category": "energy"},
    "PPIACO": {"title": "PPI All Commodities", "frequency": "Monthly", "category": "goods"},
}


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
