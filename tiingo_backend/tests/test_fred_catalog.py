from features.fred.catalog import SERIES_CATALOG, catalog_rows

_FIVE_PILLAR_SERIES = {
    "growth": ["GDPC1", "INDPRO", "USRECM"],
    "labor": ["UNRATE", "PAYEMS", "ICSA", "JTSJOL"],
    "inflation": ["CPIAUCSL", "CPILFESL", "PCEPI"],
    "consumer": ["RSAFS", "UMCSENT", "PSAVERT"],
    "rates": ["DFF", "T10Y2Y", "STLFSI4", "WALCL"],
}


def test_catalog_has_inflation():
    assert "CPIAUCSL" in SERIES_CATALOG
    assert SERIES_CATALOG["CPIAUCSL"]["category"] == "inflation"


def test_catalog_covers_five_pillars():
    assert len(SERIES_CATALOG) == 25
    for category, series_ids in _FIVE_PILLAR_SERIES.items():
        for series_id in series_ids:
            assert series_id in SERIES_CATALOG
            assert SERIES_CATALOG[series_id]["category"] == category


def test_catalog_rows_shape():
    rows = catalog_rows()
    assert len(rows) == len(SERIES_CATALOG)
    assert "series_id" in rows[0]
