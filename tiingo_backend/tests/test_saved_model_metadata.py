from features.ml.saved_model_metadata import extract_saved_model_metadata


def test_extract_saved_model_metadata_from_train_metrics():
    row = {
        "name": "Custom name",
        "train_metrics": {
            "training_symbol": "AAPL",
            "timeframe": "1d",
        },
    }
    metadata = extract_saved_model_metadata(row)
    assert metadata == {"symbol": "AAPL", "timeframe": "1d"}


def test_extract_saved_model_metadata_falls_back_to_name_prefix():
    row = {
        "name": "MSFT ml_logistic prices_only",
        "train_metrics": {"accuracy": 0.72},
    }
    metadata = extract_saved_model_metadata(row)
    assert metadata == {"symbol": "MSFT", "timeframe": None}


def test_extract_saved_model_metadata_empty_when_no_symbol_source():
    row = {"name": "", "train_metrics": None}
    metadata = extract_saved_model_metadata(row)
    assert metadata == {"symbol": None, "timeframe": None}
