from features.execution.order_qty import floor_crypto_sell_qty, resolve_sell_qty


def test_floor_crypto_sell_qty_truncates_upward_request():
    assert floor_crypto_sell_qty(0.0676) == 0.0676
    assert floor_crypto_sell_qty(0.0676000009) == 0.0676


def test_resolve_sell_qty_min_of_net_position_and_available():
    qty = resolve_sell_qty(
        0.0676,
        asset_type="crypto",
        position_qty=0.0676,
        qty_available=0.067409372,
    )
    assert qty == 0.067409372


def test_resolve_sell_qty_returns_zero_when_no_caps():
    assert resolve_sell_qty(0, asset_type="stock") == 0.0


def test_resolve_sell_qty_stock_rounds():
    qty = resolve_sell_qty(
        2.5555555,
        asset_type="stock",
        position_qty=3.0,
        qty_available=3.0,
    )
    assert qty == 2.555556
