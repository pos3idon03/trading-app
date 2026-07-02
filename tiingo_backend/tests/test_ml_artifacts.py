from uuid import uuid4

import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from features.ml.artifacts import (
    align_feature_matrix_to_schema,
    build_feature_schema,
    load_model_artifact,
    load_model_bundle,
    save_model_artifact,
    validate_feature_schema,
)
from features.ml.feature_preprocessor import fit_feature_preprocessor
from features.ml.price_features import FEATURE_NAMES
from features.ml.trainer import train_model


@pytest.fixture
def artifact_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("ML_ARTIFACT_DIR", str(tmp_path))
    from config import get_settings

    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def test_save_and_load_model_round_trip(artifact_dir):
    model = LogisticRegression(max_iter=200, random_state=42)
    model.fit([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6], [0.7, 0.8]], [0, 1, 0, 1])
    model_id = uuid4()

    path = save_model_artifact(model, model_id)
    loaded = load_model_artifact(path)

    assert loaded.predict([[0.1, 0.2]]).tolist() == model.predict([[0.1, 0.2]]).tolist()


def test_save_and_load_scaled_pipeline_round_trip(artifact_dir):
    x_rows = [[0.01, 50.0], [0.02, 60.0], [-0.01, 40.0], [0.03, 70.0]]
    y_rows = [0, 1, 0, 1]
    trained = train_model("ml_logistic", x_rows, y_rows, {})
    assert isinstance(trained.model, Pipeline)
    model_id = uuid4()

    path = save_model_artifact(trained.model, model_id)
    loaded = load_model_artifact(path)

    assert loaded.predict([[0.01, 50.0]]).tolist() == trained.model.predict([[0.01, 50.0]]).tolist()

def test_save_and_load_bundle_with_preprocessor_round_trip(artifact_dir):
    rows = [[float(value) for value in range(len(FEATURE_NAMES))] for _ in range(20)]
    labels = [index % 2 for index in range(20)]
    preprocessor = fit_feature_preprocessor(
        rows,
        labels,
        list(FEATURE_NAMES),
        {"correlation_prune_threshold": 0.0},
    )
    model = LogisticRegression(max_iter=200, random_state=42)
    transformed = preprocessor.transform(rows)
    model.fit(transformed, labels)
    model_id = uuid4()

    path = save_model_artifact(model, model_id, preprocessor=preprocessor)
    loaded_model, loaded_preprocessor = load_model_bundle(path)

    sample = preprocessor.transform([rows[0]])[0]
    assert loaded_model.predict([sample]).tolist() == model.predict([sample]).tolist()
    assert loaded_preprocessor.output_feature_names == preprocessor.output_feature_names
    assert load_model_artifact(path).predict([sample]).tolist() == model.predict([sample]).tolist()


def test_validate_feature_schema_rejects_mismatch():
    saved = build_feature_schema(["a", "b", "c"])
    with pytest.raises(ValueError, match="Feature schema mismatch"):
        validate_feature_schema(saved, ["a", "c", "b"])


def test_validate_feature_schema_accepts_match():
    saved = build_feature_schema(["a", "b"])
    validate_feature_schema(saved, ["a", "b"])


def test_align_feature_matrix_to_schema_selects_saved_order():
    saved = build_feature_schema(["a", "c"])
    names, rows = align_feature_matrix_to_schema(
        saved,
        ["a", "b", "c"],
        [[1.0, 2.0, 3.0], None, [4.0, 5.0, 6.0]],
    )
    assert names == ["a", "c"]
    assert rows == [[1.0, 3.0], None, [4.0, 6.0]]


def test_align_feature_matrix_to_schema_raises_when_feature_missing():
    saved = build_feature_schema(["a", "missing"])
    with pytest.raises(ValueError, match="missing from current build"):
        align_feature_matrix_to_schema(saved, ["a", "b"], [[1.0, 2.0]])


def test_align_feature_matrix_to_schema_nulls_short_rows():
    saved = build_feature_schema(["a", "c"])
    names, rows = align_feature_matrix_to_schema(
        saved,
        ["a", "b", "c"],
        [[1.0, 2.0], [1.0]],
    )
    assert names == ["a", "c"]
    assert rows == [None, None]
