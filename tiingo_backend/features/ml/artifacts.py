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


def _artifact_dir() -> Path:
    settings = get_settings()
    path = Path(settings.ml_artifact_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_model_artifact(model: Any, model_id: UUID) -> str:
    directory = _artifact_dir()
    filename = f"{model_id}.joblib"
    full_path = directory / filename
    joblib.dump(model, full_path)
    return str(full_path)


def load_model_artifact(artifact_path: str) -> Any:
    path = Path(artifact_path)
    if not path.is_file():
        raise FileNotFoundError(f"Model artifact not found: {artifact_path}")
    return joblib.load(path)
