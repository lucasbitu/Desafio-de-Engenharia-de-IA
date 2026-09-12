"""Integration tests for reproducible E04 development training."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ticket_classifier.flow.delivery import DeliveryPredictionService
from ticket_classifier.flow.training import OUTPUT_FILES, train_and_validate_development


class DevelopmentTrainingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary_directory = tempfile.TemporaryDirectory()
        cls.output_dir = Path(cls.temporary_directory.name)
        cls.metadata = train_and_validate_development(output_dir=cls.output_dir)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary_directory.cleanup()

    def test_all_expected_artifacts_are_created(self) -> None:
        for name in OUTPUT_FILES:
            self.assertTrue((self.output_dir / name).is_file(), name)

    def test_metrics_reproduce_frozen_e04_validation(self) -> None:
        metrics = json.loads(
            (self.output_dir / "validation_metrics.json").read_text(encoding="utf-8")
        )
        self.assertAlmostEqual(metrics["accuracy"], 0.8571578505457599, places=15)
        self.assertAlmostEqual(metrics["macro_f1"], 0.8617016202371395, places=15)
        self.assertEqual(metrics["low_confidence_policy"]["flagged"], 2_450)
        self.assertEqual(metrics["low_confidence_policy"]["errors_captured"], 960)

    def test_metadata_records_reproducibility_controls(self) -> None:
        self.assertEqual(self.metadata["stage"], "development")
        self.assertFalse(self.metadata["test_accessed"])
        self.assertEqual(self.metadata["train"]["rows"], 38_109)
        self.assertEqual(self.metadata["validation"]["rows"], 9_528)
        self.assertEqual(self.metadata["vocabulary_size"], 8_544)
        self.assertTrue(self.metadata["roundtrip_predictions_identical"])
        self.assertEqual(len(self.metadata["model_sha256"]), 64)

    def test_saved_model_supports_delivery_contract(self) -> None:
        service = DeliveryPredictionService.from_model_path(self.output_dir / "model.joblib")
        output = service.predict("reset password for account access")
        self.assertEqual(set(output.model_dump(by_alias=True)), {"class", "justification"})

    def test_existing_artifacts_are_not_overwritten_without_force(self) -> None:
        with self.assertRaises(FileExistsError):
            train_and_validate_development(output_dir=self.output_dir)


if __name__ == "__main__":
    unittest.main()
