from pathlib import Path
from typing import Any
from uuid import UUID

import joblib

from config import get_settings

FEATURE_SCHEMA_VERSION = 1


def build_feature_schema(feature_names: list[str]) -> dict:
    return {
        "version": FEATURE_SCHEMA_VERSION,
        "feature_names": list(feature_names),
    }


def validate_feature_schema(saved_schema: dict, actual_feature_names: list[str]) -> None:
    expected = list(saved_schema.get("feature_names") or [])
    actual = list(actual_feature_names)
    if expected != actual:
        raise ValueError(
            "Feature schema mismatch for inference: "
            f"expected {len(expected)} features in order {expected}, "
            f"got {len(actual)} features in order {actual}"
        )


def align_feature_matrix_to_schema(
    saved_schema: dict,
    feature_names: list[str],
    feature_rows: list[list[float] | None],
) -> tuple[list[str], list[list[float] | None]]:
    expected = list(saved_schema.get("feature_names") or [])
    if not expected or expected == feature_names:
        return feature_names, feature_rows

    index_by_name = {name: index for index, name in enumerate(feature_names)}
    missing = [name for name in expected if name not in index_by_name]
    if missing:
        raise ValueError(
            "Saved model requires features missing from current build: "
            f"{missing}. Retrain the model to use the updated feature set."
        )

    indices = [index_by_name[name] for name in expected]
    aligned_rows: list[list[float] | None] = []
    for row in feature_rows:
        if row is None or len(row) < len(feature_names):
            aligned_rows.append(None)
            continue
        aligned_rows.append([row[index] for index in indices])
    return expected, aligned_rows


def _artifact_dir() -> Path:
    settings = get_settings()
    path = Path(settings.ml_artifact_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def unpack_model_artifact(loaded: Any) -> tuple[Any, Any | None]:
    if isinstance(loaded, dict) and "model" in loaded:
        return loaded["model"], loaded.get("preprocessor")
    return loaded, None


def save_model_artifact(
    model: Any,
    model_id: UUID,
    *,
    preprocessor: Any | None = None,
) -> str:
    directory = _artifact_dir()
    filename = f"{model_id}.joblib"
    full_path = directory / filename
    payload: Any = model
    if preprocessor is not None:
        payload = {"model": model, "preprocessor": preprocessor}
    joblib.dump(payload, full_path)
    return str(full_path)


def load_model_artifact(artifact_path: str) -> Any:
    model, _ = load_model_bundle(artifact_path)
    return model


def load_model_bundle(artifact_path: str) -> tuple[Any, Any | None]:
    path = Path(artifact_path)
    if not path.is_file():
        raise FileNotFoundError(f"Model artifact not found: {artifact_path}")
    loaded = joblib.load(path)
    return unpack_model_artifact(loaded)


def delete_model_artifact(artifact_path: str | None) -> None:
    if not artifact_path:
        return
    path = Path(artifact_path)
    if path.is_file():
        path.unlink()
