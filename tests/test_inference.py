"""Tests for validated contracts and deterministic local evidence."""

from __future__ import annotations

import unittest

import numpy as np
from pydantic import ValidationError

from ticket_classifier.config import DEFAULT_DEVELOPMENT_MODEL_PATH
from ticket_classifier.classification.inference import TicketClassifier
from ticket_classifier.schemas import PredictionOutput, TicketInput


class InferenceContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.service = TicketClassifier.from_path(DEFAULT_DEVELOPMENT_MODEL_PATH)

    def test_input_normalizes_whitespace(self) -> None:
        request = TicketInput(text="  reset\n\tpassword   for account  ")
        self.assertEqual(request.text, "reset password for account")

    def test_blank_input_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            TicketInput(text=" \n\t ")

    def test_unknown_input_fields_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            TicketInput.model_validate({"text": "reset password", "label": "Access"})

    def test_classification_contract_uses_required_class_alias(self) -> None:
        result = self.service.classify("reset password for account access")
        payload = result.model_dump(by_alias=True)
        self.assertEqual(set(payload), {"class", "confidence", "evidence"})
        self.assertIn(payload["class"], self.service.classes)
        self.assertGreaterEqual(payload["confidence"], 0.0)
        self.assertLessEqual(payload["confidence"], 1.0)

    def test_evidence_is_positive_sorted_and_limited(self) -> None:
        result = self.service.classify("reset password for account access")
        contributions = [item.contribution for item in result.evidence]
        self.assertLessEqual(len(contributions), 4)
        self.assertTrue(all(value > 0.0 for value in contributions))
        self.assertEqual(contributions, sorted(contributions, reverse=True))

    def test_evidence_matches_manual_local_contribution(self) -> None:
        text = "reset password for account access"
        result = self.service.classify(text)
        pipeline = self.service._pipeline
        vectorizer = pipeline.named_steps["tfidf"]
        classifier = pipeline.named_steps["classifier"]
        vector = vectorizer.transform([text])
        class_index = int(np.flatnonzero(classifier.classes_ == result.class_)[0])
        expected = {
            str(vectorizer.get_feature_names_out()[feature_index]): float(tfidf * coefficient)
            for feature_index, tfidf, coefficient in zip(
                vector.indices,
                vector.data,
                classifier.coef_[class_index, vector.indices],
            )
            if tfidf * coefficient > 0.0
        }
        for item in result.evidence:
            self.assertIn(item.feature, expected)
            self.assertAlmostEqual(item.contribution, expected[item.feature], places=15)

    def test_service_accepts_prevalidated_input(self) -> None:
        result = self.service.classify(TicketInput(text="keyboard and monitor problem"))
        self.assertIn(result.class_, self.service.classes)

    def test_top_k_bounds_are_validated(self) -> None:
        with self.assertRaises(ValueError):
            TicketClassifier.from_path(DEFAULT_DEVELOPMENT_MODEL_PATH, top_k_evidence=0)
        with self.assertRaises(ValueError):
            TicketClassifier.from_path(DEFAULT_DEVELOPMENT_MODEL_PATH, top_k_evidence=11)

    def test_final_public_contract_has_exact_required_shape(self) -> None:
        output = PredictionOutput(
            **{"class": "Access", "justification": "Password-related evidence."}
        )
        self.assertEqual(
            output.model_dump(by_alias=True),
            {"class": "Access", "justification": "Password-related evidence."},
        )


if __name__ == "__main__":
    unittest.main()
