"""Behavioral tests for faithful deterministic justifications."""

from __future__ import annotations

import re
import unittest

from ticket_classifier.config import DEFAULT_DEVELOPMENT_MODEL_PATH
from ticket_classifier.justification.deterministic import deterministic_justification
from ticket_classifier.flow.prediction import TicketPredictionService
from ticket_classifier.schemas import ClassificationResult


class DeterministicJustificationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.service = TicketPredictionService.from_model_path(DEFAULT_DEVELOPMENT_MODEL_PATH)

    def test_public_prediction_has_exact_required_shape(self) -> None:
        output = self.service.predict("reset password for account access")
        self.assertEqual(
            set(output.model_dump(by_alias=True)),
            {"class", "justification"},
        )

    def test_justification_is_one_sentence_and_names_predicted_class(self) -> None:
        output = self.service.predict("broken monitor and keyboard")
        sentence_endings = re.findall(r"[.!?](?:\s|$)", output.justification)
        self.assertEqual(len(sentence_endings), 1)
        self.assertIn(output.class_, output.justification)

    def test_every_cited_feature_comes_from_local_evidence_and_input(self) -> None:
        text = "reset password for account access"
        result = self.service.classify(text)
        output = self.service.predict(text)
        cited = re.findall(r"'([^']+)'", output.justification)
        available = {item.feature for item in result.evidence}
        self.assertTrue(cited)
        self.assertLessEqual(len(cited), 3)
        self.assertTrue(set(cited).issubset(available))
        self.assertTrue(all(feature.casefold() in text.casefold() for feature in cited))

    def test_evidence_order_is_preserved_and_limited_for_readability(self) -> None:
        result = self.service.classify("reset password for account access")
        output = self.service.predict("reset password for account access")
        cited = re.findall(r"'([^']+)'", output.justification)
        expected = [item.feature for item in result.evidence[:3]]
        self.assertEqual(cited, expected)

    def test_fallback_does_not_invent_term_evidence(self) -> None:
        result = ClassificationResult(
            **{"class": "Hardware", "confidence": 0.25, "evidence": ()}
        )
        justification = deterministic_justification(result)
        self.assertNotIn("'", justification)
        self.assertIn("no individual positive term-level evidence", justification)

    def test_evidence_limit_is_validated(self) -> None:
        result = self.service.classify("reset password for account access")
        with self.assertRaises(ValueError):
            deterministic_justification(result, max_evidence=0)
        with self.assertRaises(ValueError):
            deterministic_justification(result, max_evidence=4)

    def test_service_accepts_prevalidated_input_through_same_path(self) -> None:
        from ticket_classifier.schemas import TicketInput

        output = self.service.predict(TicketInput(text="storage disk quota is full"))
        self.assertIn(output.class_, self.service.classes)
        self.assertTrue(output.justification)


if __name__ == "__main__":
    unittest.main()
