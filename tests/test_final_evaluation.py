"""Tests for the final executor using synthetic splits only."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from ticket_classifier.config import ID_COLUMN, LABEL_COLUMN, TEXT_COLUMN
from ticket_classifier.final_evaluation import (
    FINAL_CONFIRMATION,
    OUTPUT_FILES,
    FinalEvaluationPlan,
    SplitExpectation,
    run_final_evaluation,
)

CLASSES = (
    "Access",
    "Administrative rights",
    "HR Support",
    "Hardware",
    "Internal Project",
    "Miscellaneous",
    "Purchase",
    "Storage",
)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def write_split(path: Path, split: str, examples_per_class: int, offset: int) -> None:
    rows = []
    for class_index, label in enumerate(CLASSES):
        token = label.casefold().replace(" ", "_")
        for example_index in range(examples_per_class):
            source_row = offset + class_index * examples_per_class + example_index
            rows.append(
                {
                    ID_COLUMN: f"{split}-{source_row}",
                    "source_row": source_row,
                    TEXT_COLUMN: f"{token} {token} support request example {example_index}",
                    LABEL_COLUMN: label,
                }
            )
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8")


class FinalEvaluationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        train_path = root / "train.csv"
        validation_path = root / "validation.csv"
        test_path = root / "synthetic_holdout.csv"
        write_split(train_path, "train", 3, 0)
        write_split(validation_path, "validation", 2, 1_000)
        write_split(test_path, "holdout", 2, 2_000)
        self.output_dir = root / "final-output"
        self.plan = FinalEvaluationPlan(
            train=SplitExpectation(train_path, 24, file_hash(train_path), "train"),
            validation=SplitExpectation(
                validation_path, 16, file_hash(validation_path), "validation"
            ),
            test=SplitExpectation(test_path, 16, file_hash(test_path), "test"),
            output_dir=self.output_dir,
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_confirmation_is_required_before_any_output_is_created(self) -> None:
        with self.assertRaises(PermissionError):
            run_final_evaluation(self.plan, confirmation="no")
        self.assertFalse(self.output_dir.exists())

    def test_synthetic_release_writes_complete_auditable_artifact_set(self) -> None:
        metadata = run_final_evaluation(
            self.plan,
            confirmation=FINAL_CONFIRMATION,
            release_commit="synthetic-test-commit",
        )
        self.assertEqual(set(path.name for path in self.output_dir.iterdir()), set(OUTPUT_FILES))
        self.assertEqual(metadata["combined_training_rows"], 40)
        self.assertEqual(metadata["test"]["rows"], 16)
        self.assertEqual(metadata["release_commit"], "synthetic-test-commit")
        self.assertTrue(metadata["final_test_accessed"])
        self.assertTrue(metadata["roundtrip_predictions_identical"])
        self.assertEqual(len(metadata["classes"]), 8)
        metrics = json.loads((self.output_dir / "final_metrics.json").read_text("utf-8"))
        self.assertEqual(metrics["sample_size"], 16)

    def test_existing_final_output_cannot_be_overwritten(self) -> None:
        self.output_dir.mkdir()
        (self.output_dir / "marker.txt").write_text("preserve", encoding="utf-8")
        with self.assertRaisesRegex(FileExistsError, "cannot be overwritten"):
            run_final_evaluation(self.plan, confirmation=FINAL_CONFIRMATION)
        self.assertEqual((self.output_dir / "marker.txt").read_text("utf-8"), "preserve")

    def test_wrong_hash_fails_closed_and_removes_staging_output(self) -> None:
        bad_plan = FinalEvaluationPlan(
            train=SplitExpectation(self.plan.train.path, 24, "0" * 64, "train"),
            validation=self.plan.validation,
            test=self.plan.test,
            output_dir=self.output_dir,
        )
        with self.assertRaisesRegex(ValueError, "Unexpected train SHA-256"):
            run_final_evaluation(bad_plan, confirmation=FINAL_CONFIRMATION)
        self.assertFalse(self.output_dir.exists())
        self.assertFalse(list(self.output_dir.parent.glob(".final-output.staging-*")))

    def test_overlap_is_rejected_before_training(self) -> None:
        validation = pd.read_csv(self.plan.validation.path)
        train = pd.read_csv(self.plan.train.path)
        validation.loc[0, ID_COLUMN] = train.loc[0, ID_COLUMN]
        validation.loc[0, "source_row"] = train.loc[0, "source_row"]
        validation.to_csv(self.plan.validation.path, index=False, encoding="utf-8")
        overlap_plan = FinalEvaluationPlan(
            train=self.plan.train,
            validation=SplitExpectation(
                self.plan.validation.path,
                16,
                file_hash(self.plan.validation.path),
                "validation",
            ),
            test=self.plan.test,
            output_dir=self.output_dir,
        )
        with self.assertRaisesRegex(ValueError, "overlap"):
            run_final_evaluation(overlap_plan, confirmation=FINAL_CONFIRMATION)
        self.assertFalse(self.output_dir.exists())


if __name__ == "__main__":
    unittest.main()
