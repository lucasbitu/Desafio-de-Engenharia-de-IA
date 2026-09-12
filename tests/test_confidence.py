"""Tests for threshold selection and confidence-aware delivery."""

from __future__ import annotations

import unittest

import pandas as pd

from ticket_classifier.metrics.confidence import (
    LOW_CONFIDENCE_THRESHOLD,
    evaluate_threshold,
    is_low_confidence,
    select_lowest_eligible_threshold,
)
from ticket_classifier.config import (
    DEFAULT_DEVELOPMENT_MODEL_PATH,
    DEFAULT_DEVELOPMENT_PREDICTIONS_PATH,
)
from ticket_classifier.flow.delivery import DeliveryPredictionService

VALIDATION_PREDICTIONS = DEFAULT_DEVELOPMENT_PREDICTIONS_PATH


class ConfidencePolicyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.predictions = pd.read_csv(VALIDATION_PREDICTIONS, encoding="utf-8")
        cls.service = DeliveryPredictionService.from_model_path(DEFAULT_DEVELOPMENT_MODEL_PATH)

    def test_frozen_boundary_is_strictly_below_point_six(self) -> None:
        self.assertTrue(is_low_confidence(0.59))
        self.assertFalse(is_low_confidence(0.60))
        self.assertFalse(is_low_confidence(0.61))

    def test_invalid_confidence_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            is_low_confidence(-0.01)
        with self.assertRaises(ValueError):
            is_low_confidence(1.01)

    def test_validation_criterion_selects_point_six(self) -> None:
        selected = select_lowest_eligible_threshold(
            self.predictions["confidence"], self.predictions["is_correct"]
        )
        self.assertEqual(selected.threshold, LOW_CONFIDENCE_THRESHOLD)
        self.assertEqual(selected.total, 9_528)
        self.assertEqual(selected.total_errors, 1_361)
        self.assertEqual(selected.flagged, 2_450)
        self.assertEqual(selected.errors_captured, 960)
        self.assertGreaterEqual(selected.error_capture_rate, 0.70)
        self.assertLessEqual(selected.flagged_rate, 0.30)

    def test_lower_grid_candidates_do_not_meet_error_capture_criterion(self) -> None:
        for threshold in (0.40, 0.45, 0.50, 0.55):
            metrics = evaluate_threshold(
                self.predictions["confidence"],
                self.predictions["is_correct"],
                threshold,
            )
            self.assertLess(metrics.error_capture_rate, 0.70)

    def test_low_confidence_changes_wording_not_class(self) -> None:
        text = "zzzxxyyqqq"
        raw = self.service.classify(text)
        diagnostics = self.service.diagnose(text)
        output = self.service.predict(text)
        self.assertTrue(diagnostics.low_confidence)
        self.assertEqual(raw.class_, diagnostics.class_)
        self.assertEqual(raw.class_, output.class_)
        self.assertIn("confidence is low", output.justification)

    def test_regular_confidence_keeps_standard_wording(self) -> None:
        text = "reset password for account access"
        output = self.service.predict(text)
        diagnostics = self.service.diagnose(text)
        self.assertFalse(diagnostics.low_confidence)
        self.assertNotIn("confidence is low", output.justification)

    def test_public_contract_remains_exact(self) -> None:
        output = self.service.predict("zzzxxyyqqq")
        self.assertEqual(
            set(output.model_dump(by_alias=True)),
            {"class", "justification"},
        )


if __name__ == "__main__":
    unittest.main()
