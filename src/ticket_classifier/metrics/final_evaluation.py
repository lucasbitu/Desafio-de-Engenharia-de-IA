"""Explicit, single-use final evaluation for the frozen E04 release candidate.

This module is intentionally isolated from development training and interactive
inference. Importing it has no side effects and does not read any split. The real
final test is opened only after an explicit confirmation reaches ``run_final_evaluation``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import pydantic
import sklearn
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

from .confidence import LOW_CONFIDENCE_THRESHOLD, evaluate_threshold, is_low_confidence
from ..config import (
    DEFAULT_TRAIN_PATH,
    DEFAULT_VALIDATION_PATH,
    EXPECTED_TRAIN_ROWS,
    EXPECTED_TRAIN_SHA256,
    EXPECTED_VALIDATION_ROWS,
    EXPECTED_VALIDATION_SHA256,
    ID_COLUMN,
    LABEL_COLUMN,
    PROJECT_ROOT,
    RANDOM_SEED,
    TEXT_COLUMN,
)
from ..flow.delivery import DeliveryPredictionService
from ..classification.inference import TicketClassifier
from ..classification.model import build_e04_pipeline
from ..flow.training import load_frozen_split, sha256_file

FINAL_CONFIRMATION = "I_UNDERSTAND_THIS_OPENS_THE_FINAL_TEST"
EXPECTED_FINAL_TEST_ROWS = 200
EXPECTED_FINAL_TEST_SHA256 = "E857B8873DE34B47EC39360F82BD25A04497A811D9D985E835F9D1EEF27F5B6D"
DEFAULT_FINAL_TEST_PATH = PROJECT_ROOT / "data" / "splits" / "test.csv"
DEFAULT_FINAL_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "final"
OUTPUT_FILES = (
    "model.joblib",
    "final_metrics.json",
    "final_predictions.csv",
    "confusion_matrix.csv",
    "run_metadata.json",
)


@dataclass(frozen=True)
class SplitExpectation:
    path: Path
    rows: int
    sha256: str
    name: str


@dataclass(frozen=True)
class FinalEvaluationPlan:
    train: SplitExpectation
    validation: SplitExpectation
    test: SplitExpectation
    output_dir: Path


def default_plan() -> FinalEvaluationPlan:
    return FinalEvaluationPlan(
        train=SplitExpectation(
            DEFAULT_TRAIN_PATH, EXPECTED_TRAIN_ROWS, EXPECTED_TRAIN_SHA256, "train"
        ),
        validation=SplitExpectation(
            DEFAULT_VALIDATION_PATH,
            EXPECTED_VALIDATION_ROWS,
            EXPECTED_VALIDATION_SHA256,
            "validation",
        ),
        test=SplitExpectation(
            DEFAULT_FINAL_TEST_PATH,
            EXPECTED_FINAL_TEST_ROWS,
            EXPECTED_FINAL_TEST_SHA256,
            "test",
        ),
        output_dir=DEFAULT_FINAL_OUTPUT_DIR,
    )


def validate_release_splits(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
) -> None:
    split_ids = {
        "train": set(train[ID_COLUMN]),
        "validation": set(validation[ID_COLUMN]),
        "test": set(test[ID_COLUMN]),
    }
    pairs = (("train", "validation"), ("train", "test"), ("validation", "test"))
    for left, right in pairs:
        if not split_ids[left].isdisjoint(split_ids[right]):
            raise ValueError(f"Frozen {left} and {right} splits overlap.")

    class_sets = {
        "train": set(train[LABEL_COLUMN]),
        "validation": set(validation[LABEL_COLUMN]),
        "test": set(test[LABEL_COLUMN]),
    }
    if len(class_sets["train"]) != 8:
        raise ValueError("Release data must contain exactly eight classes.")
    if not (class_sets["train"] == class_sets["validation"] == class_sets["test"]):
        raise ValueError("Train, validation and test class sets differ.")

    all_source_rows = pd.concat(
        [train["source_row"], validation["source_row"], test["source_row"]],
        ignore_index=True,
    )
    if all_source_rows.duplicated().any():
        raise ValueError("A source row is assigned to more than one release split.")


def _load(expectation: SplitExpectation) -> tuple[pd.DataFrame, str]:
    frame, digest = load_frozen_split(
        expectation.path,
        expected_rows=expectation.rows,
        expected_sha256=expectation.sha256,
        split_name=expectation.name,
    )
    return frame, digest


def _git_commit(project_root: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(project_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _write_json(path: Path, content: dict[str, Any]) -> None:
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")


def _prepare_staging(output_dir: Path) -> Path:
    if output_dir.exists():
        raise FileExistsError(
            f"Final output already exists: {output_dir}. It cannot be overwritten."
        )
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = output_dir.parent / f".{output_dir.name}.staging-{uuid.uuid4().hex}"
    staging.mkdir()
    return staging


def run_final_evaluation(
    plan: FinalEvaluationPlan,
    *,
    confirmation: str,
    release_commit: str | None = None,
) -> dict[str, Any]:
    """Train on train+validation and evaluate the sealed split exactly once.

    Callers must provide the literal confirmation. Outputs are staged and moved
    atomically; an existing final directory is never replaced.
    """

    if confirmation != FINAL_CONFIRMATION:
        raise PermissionError(
            "Final evaluation requires the explicit confirmation token."
        )

    staging = _prepare_staging(plan.output_dir)
    accessed_at = datetime.now(timezone.utc).isoformat()
    try:
        train, train_hash = _load(plan.train)
        validation, validation_hash = _load(plan.validation)
        test, test_hash = _load(plan.test)
        validate_release_splits(train, validation, test)

        development = pd.concat([train, validation], ignore_index=True)
        pipeline = build_e04_pipeline(development[LABEL_COLUMN])
        pipeline.fit(development[TEXT_COLUMN], development[LABEL_COLUMN])

        predicted = pipeline.predict(test[TEXT_COLUMN])
        probabilities = pipeline.predict_proba(test[TEXT_COLUMN])
        confidence = probabilities.max(axis=1)
        correct = predicted == test[LABEL_COLUMN].to_numpy()
        threshold = evaluate_threshold(confidence, correct, LOW_CONFIDENCE_THRESHOLD)

        model_path = staging / "model.joblib"
        joblib.dump(pipeline, model_path)
        reloaded = joblib.load(model_path)
        if not np.array_equal(predicted, reloaded.predict(test[TEXT_COLUMN])):
            raise RuntimeError("Final predictions changed after model reload.")

        service = DeliveryPredictionService(TicketClassifier(reloaded))
        justifications = [service.predict(text).justification for text in test[TEXT_COLUMN]]
        predictions = test[[ID_COLUMN, "source_row", LABEL_COLUMN]].copy()
        predictions["predicted_class"] = predicted
        predictions["confidence"] = confidence
        predictions["low_confidence"] = [is_low_confidence(value) for value in confidence]
        predictions["is_correct"] = correct
        predictions["justification"] = justifications
        predictions.to_csv(staging / "final_predictions.csv", index=False, encoding="utf-8")

        labels = sorted(str(value) for value in pipeline.named_steps["classifier"].classes_)
        matrix = confusion_matrix(test[LABEL_COLUMN], predicted, labels=labels)
        pd.DataFrame(matrix, index=labels, columns=labels).to_csv(
            staging / "confusion_matrix.csv", encoding="utf-8"
        )

        report = classification_report(
            test[LABEL_COLUMN], predicted, output_dict=True, zero_division=0
        )
        metrics: dict[str, Any] = {
            "sample_size": len(test),
            "accuracy": float(accuracy_score(test[LABEL_COLUMN], predicted)),
            "macro_f1": float(
                f1_score(test[LABEL_COLUMN], predicted, average="macro", zero_division=0)
            ),
            "weighted_f1": float(
                f1_score(test[LABEL_COLUMN], predicted, average="weighted", zero_division=0)
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
        _write_json(staging / "final_metrics.json", metrics)

        classifier = pipeline.named_steps["classifier"]
        vectorizer = pipeline.named_steps["tfidf"]
        metadata: dict[str, Any] = {
            "stage": "final",
            "experiment": "E04_tfidf_unigram_logreg_moderate_weights",
            "final_test_accessed": True,
            "accessed_at_utc": accessed_at,
            "single_use_output_guard": True,
            "release_commit": release_commit or _git_commit(PROJECT_ROOT),
            "random_seed": RANDOM_SEED,
            "train": {"rows": len(train), "sha256": train_hash},
            "validation": {"rows": len(validation), "sha256": validation_hash},
            "test": {"rows": len(test), "sha256": test_hash},
            "combined_training_rows": len(development),
            "classes": labels,
            "vocabulary_size": len(vectorizer.get_feature_names_out()),
            "class_weight": {
                str(key): float(value) for key, value in classifier.class_weight.items()
            },
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
        _write_json(staging / "run_metadata.json", metadata)

        missing = [name for name in OUTPUT_FILES if not (staging / name).is_file()]
        if missing:
            raise RuntimeError(f"Final artifact set is incomplete: {missing}")
        staging.rename(plan.output_dir)
        return metadata
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the explicit, single-use final evaluation for frozen E04."
    )
    parser.add_argument(
        "--confirm",
        required=True,
        help=f"Must equal {FINAL_CONFIRMATION!r}.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metadata = run_final_evaluation(default_plan(), confirmation=args.confirm)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
