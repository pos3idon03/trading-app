import pytest

from features.fred.catalog import normalize_series_id, validate_series_ids


def test_normalize_usrecnber_typo():
    assert normalize_series_id("USRECNBER") == "USRECM"


def test_validate_series_ids_rejects_unknown():
    with pytest.raises(ValueError, match="INVALID"):
        validate_series_ids(["ZZZZINVALID"])


def test_validate_series_ids_accepts_catalog_ids():
    assert validate_series_ids(["T10Y2Y", "WALCL"]) == ["T10Y2Y", "WALCL"]
