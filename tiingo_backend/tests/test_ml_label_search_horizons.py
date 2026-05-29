from features.ml.catalog import label_search_horizons


def test_label_search_horizons_centers_on_universe_value():
    assert label_search_horizons(24) == [20, 22, 24, 26, 28]


def test_label_search_horizons_handles_lower_bound():
    assert label_search_horizons(5) == [1, 3, 5, 7, 9]
    assert label_search_horizons(1) == [1, 3, 5]


def test_label_search_horizons_handles_upper_bound():
    assert label_search_horizons(59) == [55, 57, 59]
    assert label_search_horizons(60) == [56, 58, 60]
