"""Persisted sklearn model load/save utilities."""
from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any

from utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_MODEL_DIR = Path(__file__).resolve().parents[3] / "data" / "mc_ml_models"


def resolve_model_path(name: str, base_dir: Path | None = None) -> Path:
    root = base_dir or DEFAULT_MODEL_DIR
    return root / name


def save_sklearn_bundle(path: Path, model: Any, metadata: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        pickle.dump({"model": model, "metadata": metadata}, fh)
    meta_path = path.with_suffix(path.suffix + ".meta.json")
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def load_sklearn_bundle(path: Path) -> tuple[Any, dict]:
    if not path.exists():
        raise FileNotFoundError(f"ML model not found: {path}")
    with path.open("rb") as fh:
        data = pickle.load(fh)
    return data["model"], data.get("metadata", {})
