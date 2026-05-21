from features.market_data.stock_kpis import (
    KpiItem,
    _compute_ttm_eps,
    _valuation_kpis,
)


def test_compute_ttm_eps_requires_four_quarters():
    rows = [
        {"period": "2024-Q1", "value": 1.0},
        {"period": "2023-Q4", "value": 1.1},
        {"period": "2023-Q3", "value": 0.9},
    ]
    assert _compute_ttm_eps(rows) is None


def test_compute_ttm_eps_sums_four_quarters():
    rows = [
        {"period": "2024-Q1", "value": 1.0},
        {"period": "2023-Q4", "value": 1.1},
        {"period": "2023-Q3", "value": 0.9},
        {"period": "2023-Q2", "value": 0.8},
    ]
    assert _compute_ttm_eps(rows) == 3.8


def test_valuation_kpis_pe_ratio():
    kpis = _valuation_kpis(price=150.0, ttm_eps=3.0, div_yield=2.5)
    by_key = {k.key: k for k in kpis}
    assert by_key["pe_ratio"].value == 50.0
    assert by_key["dividend_yield"].value == 2.5
    assert by_key["eps_ttm"].value == 3.0


def test_valuation_kpis_pe_none_when_no_eps():
    kpis = _valuation_kpis(price=150.0, ttm_eps=None, div_yield=None)
    assert kpis[0].value is None
