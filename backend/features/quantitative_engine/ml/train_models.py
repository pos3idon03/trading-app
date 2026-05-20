"""Offline training for MC ML models from walk-forward feature export CSV."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from features.quantitative_engine.mc_features import FEATURE_NAMES
from features.quantitative_engine.ml.model_io import save_sklearn_bundle
from features.quantitative_engine.ml.regime_model import train_regime_model
from features.quantitative_engine.ml.surrogate_model import train_surrogate_model
from features.quantitative_engine.ml.threshold_model import train_threshold_model


def _load_xy(csv_path: Path) -> tuple[np.ndarray, pd.DataFrame]:
    df = pd.read_csv(csv_path)
    missing = [c for c in FEATURE_NAMES if c not in df.columns]
    if missing:
        raise ValueError(f"CSV missing feature columns: {missing}")
    X = df[FEATURE_NAMES].to_numpy(dtype=float)
    return X, df


def train_all(csv_path: Path, out_dir: Path) -> None:
    X, df = _load_xy(csv_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    if "label_buy_threshold" in df.columns and "label_sell_threshold" in df.columns:
        model = train_threshold_model(
            X,
            df["label_buy_threshold"].to_numpy(),
            df["label_sell_threshold"].to_numpy(),
        )
        save_sklearn_bundle(
            out_dir / "threshold_model.pkl",
            model,
            {"type": "threshold", "features": FEATURE_NAMES, "rows": len(df)},
        )

    if "label_w_trend" in df.columns:
        model = train_regime_model(X, df["label_w_trend"].to_numpy())
        save_sklearn_bundle(
            out_dir / "regime_model.pkl",
            model,
            {"type": "regime", "features": FEATURE_NAMES, "rows": len(df)},
        )

    if "label_prob" in df.columns:
        model = train_surrogate_model(X, df["label_prob"].to_numpy())
        save_sklearn_bundle(
            out_dir / "surrogate_model.pkl",
            model,
            {"type": "surrogate", "features": FEATURE_NAMES, "rows": len(df)},
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Train MC ML models from feature CSV")
    parser.add_argument("csv_path", type=Path, help="Exported walk-forward features CSV")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "data" / "mc_ml_models",
    )
    args = parser.parse_args()
    train_all(args.csv_path, args.out_dir)
    print(f"Models written to {args.out_dir}")


if __name__ == "__main__":
    main()
