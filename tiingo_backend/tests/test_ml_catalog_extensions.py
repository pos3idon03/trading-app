from features.ml.catalog import validate_ml_params


def test_validate_denoise_method():
    params = validate_ml_params("ml_logistic", {"denoise_method": "kalman"})
    assert params["denoise_method"] == "kalman"


def test_validate_sizing_method_hrp():
    params = validate_ml_params("ml_logistic", {"sizing_method": "hrp"})
    assert params["sizing_method"] == "hrp"
