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
        news_names=["news_sent_avg_score_1d"],
        news_rows=[[0.5], [0.6]],
    )
    assert names == ["ret_1", "DFF_level", "news_sent_avg_score_1d"]
    assert rows == [[0.1, 4.0, 0.5], None]


def test_omitted_context_names_when_rows_inactive():
    names, rows = assemble_feature_matrix(
        "prices_macro",
        ["ret_1"],
        [[0.1], [0.2]],
        ["DFF_level"],
        [[4.0], [4.1]],
        context_names=["ctx_1w_ret_5", "ctx_1w_ret_20"],
        context_rows=[None, None],
        strategy_names=["strat_rsi_reversion_signal"],
        strategy_rows=[[0.0], [1.0]],
    )
    assert names == ["ret_1", "DFF_level", "strat_rsi_reversion_signal"]
    assert rows == [[0.1, 4.0, 0.0], [0.2, 4.1, 1.0]]


def test_omitted_news_placeholder_does_not_nullify_rows():
    """Empty news names with all-None rows must not participate in merge."""
    names, rows = assemble_feature_matrix(
        "prices_macro",
        ["ret_1"],
        [[0.1], [0.2]],
        ["DFF_level"],
        [[4.0], [4.1]],
        news_names=[],
        news_rows=[None, None],
    )
    assert names == ["ret_1", "DFF_level"]
    assert rows == [[0.1, 4.0], [0.2, 4.1]]


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
