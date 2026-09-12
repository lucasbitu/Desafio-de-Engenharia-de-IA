"""Reproducible development training for the E04 pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import pydantic
import sklearn
from sklearn.metrics import accuracy_score, classification_report, f1_score

from .confidence import LOW_CONFIDENCE_THRESHOLD, evaluate_threshold, is_low_confidence
from .config import (
    DEFAULT_TRAIN_PATH,
    DEFAULT_VALIDATION_PATH,
    DEFAULT_DEVELOPMENT_ARTIFACT_DIR,
    EXPECTED_TRAIN_ROWS,
    EXPECTED_TRAIN_SHA256,
    EXPECTED_VALIDATION_ROWS,
    EXPECTED_VALIDATION_SHA256,
    ID_COLUMN,
    LABEL_COLUMN,
    RANDOM_SEED,
    TEXT_COLUMN,
)
from .model import build_e04_pipeline

DEFAULT_OUTPUT_DIR = DEFAULT_DEVELOPMENT_ARTIFACT_DIR
OUTPUT_FILES = (
    "model.joblib",
    "validation_metrics.json",
    "validation_predictions.csv",
    "run_metadata.json",
)
REQUIRED_COLUMNS = {ID_COLUMN, "source_row", TEXT_COLUMN, LABEL_COLUMN}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_frozen_split(
    path: Path,
    *,
    expected_rows: int,
    expected_sha256: str,
    split_name: str,
) -> tuple[pd.DataFrame, str]:
    if not path.is_file():
        raise FileNotFoundError(f"Frozen {split_name} split not found: {path}")
    actual_hash = sha256_file(path)
    if actual_hash != expected_sha256:
        raise ValueError(
            f"Unexpected {split_name} SHA-256: expected {expected_sha256}, found {actual_hash}."
        )
    frame = pd.read_csv(path, encoding="utf-8")
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"{split_name} is missing columns: {sorted(missing)}")
    if len(frame) != expected_rows:
        raise ValueError(
            f"{split_name} must contain {expected_rows:,} rows; found {len(frame):,}."
        )
    if frame[ID_COLUMN].isna().any() or frame[ID_COLUMN].duplicated().any():
        raise ValueError(f"{split_name} contains missing or duplicate record_id values.")
    if frame[TEXT_COLUMN].isna().any() or frame[TEXT_COLUMN].astype(str).str.strip().eq("").any():
        raise ValueError(f"{split_name} contains null or blank ticket text.")
    if frame[LABEL_COLUMN].isna().any() or frame[LABEL_COLUMN].astype(str).str.strip().eq("").any():
        raise ValueError(f"{split_name} contains null or blank labels.")
    return frame, actual_hash


def validate_development_splits(train: pd.DataFrame, validation: pd.DataFrame) -> None:
    if not set(train[ID_COLUMN]).isdisjoint(validation[ID_COLUMN]):
        raise ValueError("Frozen train and validation splits overlap.")
    if set(train[LABEL_COLUMN]) != set(validation[LABEL_COLUMN]):
        raise ValueError("Train and validation class sets differ.")
    if train[LABEL_COLUMN].nunique() != 8:
        raise ValueError("The development data must contain exactly eight classes.")


def _prepare_output(output_dir: Path, force: bool) -> None:
    existing = [output_dir / name for name in OUTPUT_FILES if (output_dir / name).exists()]
    if existing and not force:
        names = ", ".join(path.name for path in existing)
        raise FileExistsError(f"Development artifacts already exist: {names}. Use --force to replace them.")
    output_dir.mkdir(parents=True, exist_ok=True)
    if force:
        for path in existing:
            path.unlink()


def _write_json(path: Path, content: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(content, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def train_and_validate_development(
    *,
    train_path: Path = DEFAULT_TRAIN_PATH,
    validation_path: Path = DEFAULT_VALIDATION_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    force: bool = False,
) -> dict[str, Any]:
    """Train the frozen E04 configuration and reproduce development metrics."""

    _prepare_output(output_dir, force)
    train, train_hash = load_frozen_split(
        train_path,
        expected_rows=EXPECTED_TRAIN_ROWS,
        expected_sha256=EXPECTED_TRAIN_SHA256,
        split_name="train",
    )
    validation, validation_hash = load_frozen_split(
        validation_path,
        expected_rows=EXPECTED_VALIDATION_ROWS,
        expected_sha256=EXPECTED_VALIDATION_SHA256,
        split_name="validation",
    )
    validate_development_splits(train, validation)

    pipeline = build_e04_pipeline(train[LABEL_COLUMN])
    pipeline.fit(train[TEXT_COLUMN], train[LABEL_COLUMN])
    predicted = pipeline.predict(validation[TEXT_COLUMN])
    probabilities = pipeline.predict_proba(validation[TEXT_COLUMN])
    confidence = probabilities.max(axis=1)
    correct = predicted == validation[LABEL_COLUMN].to_numpy()

    report = classification_report(
        validation[LABEL_COLUMN], predicted, output_dict=True, zero_division=0
    )
    threshold = evaluate_threshold(confidence, correct, LOW_CONFIDENCE_THRESHOLD)
    metrics: dict[str, Any] = {
        "sample_size": len(validation),
        "accuracy": float(accuracy_score(validation[LABEL_COLUMN], predicted)),
        "macro_f1": float(
            f1_score(validation[LABEL_COLUMN], predicted, average="macro", zero_division=0)
        ),
        "weighted_f1": float(
            f1_score(validation[LABEL_COLUMN], predicted, average="weighted", zero_division=0)
        ),
        "classification_report": report,
        "low_confidence_policy": {
            "threshold": threshold.threshold,
            "flagged": threshold.flagged,
            "flagged_rate": threshold.flagged_rate,
            "errors_captured": threshold.errors_captured,
            "error_capture_rate": threshold.error_capture_rate,
            "accuracy_below": threshold.accuracy_below,
            "accuracy_at_or_above": threshold.accuracy_at_or_above,
        },
    }

    predictions = validation[[ID_COLUMN, "source_row", LABEL_COLUMN]].copy()
    predictions["predicted_class"] = predicted
    predictions["confidence"] = confidence
    predictions["low_confidence"] = [is_low_confidence(value) for value in confidence]
    predictions["is_correct"] = correct

    model_path = output_dir / "model.joblib"
    joblib.dump(pipeline, model_path)
    reloaded = joblib.load(model_path)
    reloaded_predictions = reloaded.predict(validation[TEXT_COLUMN])
    if not np.array_equal(predicted, reloaded_predictions):
        raise RuntimeError("Predictions changed after saving and reloading the model.")

    predictions.to_csv(output_dir / "validation_predictions.csv", index=False, encoding="utf-8")
    _write_json(output_dir / "validation_metrics.json", metrics)

    vectorizer = pipeline.named_steps["tfidf"]
    classifier = pipeline.named_steps["classifier"]
    metadata: dict[str, Any] = {
        "stage": "development",
        "experiment": "E04_tfidf_unigram_logreg_moderate_weights",
        "test_accessed": False,
        "random_seed": RANDOM_SEED,
        "train": {"rows": len(train), "sha256": train_hash},
        "validation": {"rows": len(validation), "sha256": validation_hash},
        "classes": [str(label) for label in classifier.classes_],
        "vocabulary_size": len(vectorizer.get_feature_names_out()),
        "class_weight": {str(key): float(value) for key, value in classifier.class_weight.items()},
        "model_sha256": sha256_file(model_path),
        "roundtrip_predictions_identical": True,
        "metrics": {
            "accuracy": metrics["accuracy"],
            "macro_f1": metrics["macro_f1"],
            "weighted_f1": metrics["weighted_f1"],
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "pydantic": pydantic.__version__,
            "scikit_learn": sklearn.__version__,
            "joblib": joblib.__version__,
        },
    }
    _write_json(output_dir / "run_metadata.json", metadata)
    return metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train and validate the frozen E04 development pipeline."
    )
    parser.add_argument("--train", type=Path, default=DEFAULT_TRAIN_PATH)
    parser.add_argument("--validation", type=Path, default=DEFAULT_VALIDATION_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metadata = train_and_validate_development(
        train_path=args.train,
        validation_path=args.validation,
        output_dir=args.output_dir,
        force=args.force,
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
