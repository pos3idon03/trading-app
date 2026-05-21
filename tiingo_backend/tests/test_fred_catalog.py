from features.fred.catalog import SERIES_CATALOG, catalog_rows


def test_catalog_has_inflation():
    assert "CPIAUCSL" in SERIES_CATALOG
    assert SERIES_CATALOG["CPIAUCSL"]["category"] == "inflation"


def test_catalog_rows_shape():
    rows = catalog_rows()
    assert len(rows) == len(SERIES_CATALOG)
    assert "series_id" in rows[0]
