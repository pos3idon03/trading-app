from features.ml.assembler import assemble_feature_matrix


def test_prices_only_returns_price_matrix():
    names, rows = assemble_feature_matrix(
        "prices_only",
        ["ret_1"],
        [[0.1], None],
        [],
        [],
    )
    assert names == ["ret_1"]
    assert rows == [[0.1], None]


def test_prices_macro_concatenates_columns():
    names, rows = assemble_feature_matrix(
        "prices_macro",
        ["ret_1"],
        [[0.1], [0.2]],
        ["DFF_level"],
        [[4.0], None],
    )
    assert names == ["ret_1", "DFF_level"]
    assert rows == [[0.1, 4.0], None]


def test_prices_macro_fundamentals_concatenates_all_blocks():
    names, rows = assemble_feature_matrix(
        "prices_macro_fundamentals",
        ["ret_1"],
        [[0.1], [0.2]],
        ["DFF_level"],
        [[4.0], [4.1]],
        ["revenue_level"],
        [[100.0], None],
    )
    assert names == ["ret_1", "DFF_level", "revenue_level"]
    assert rows == [[0.1, 4.0, 100.0], None]
