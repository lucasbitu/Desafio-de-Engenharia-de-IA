"""Tests for the optional, evidence-grounded LLM presentation layer."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from ticket_classifier.delivery import DeliveryPredictionService
from ticket_classifier.llm_justification import (
    InvalidLLMJustification,
    GeminiJustificationRewriter,
    OpenAIJustificationRewriter,
    rewriter_from_environment,
    validate_llm_justification,
)
from ticket_classifier.schemas import ClassificationResult, Evidence


def classification(*, confidence: float = 0.91) -> ClassificationResult:
    return ClassificationResult(
        **{
            "class": "Access",
            "confidence": confidence,
            "evidence": (
                Evidence(feature="password", tfidf=0.8, coefficient=2.0, contribution=1.6),
                Evidence(feature="account", tfidf=0.5, coefficient=1.0, contribution=0.5),
            ),
        }
    )


class FakeResponses:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=self.output_text)


class FakeGeminiModels:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls: list[dict] = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(text=self.text)


class FakeClassifier:
    classes = ("Access",)

    def __init__(self, result: ClassificationResult) -> None:
        self.result = result

    def classify(self, ticket):
        return self.result


class RaisingRewriter:
    def rewrite(self, classification, fallback, *, low_confidence):
        raise TimeoutError("simulated provider timeout")


class LLMJustificationTest(unittest.TestCase):
    def test_valid_rewrite_uses_responses_api_without_storage(self) -> None:
        responses = FakeResponses(
            "The Access classification is supported by the password evidence."
        )
        rewriter = OpenAIJustificationRewriter(
            SimpleNamespace(responses=responses), model="test-model"
        )

        output = rewriter.rewrite(
            classification(), "fallback", low_confidence=False
        )

        self.assertIn("Access", output)
        self.assertEqual(responses.calls[0]["model"], "test-model")
        self.assertFalse(responses.calls[0]["store"])
        self.assertEqual(responses.calls[0]["max_output_tokens"], 180)

    def test_generated_text_must_preserve_grounded_evidence(self) -> None:
        with self.assertRaises(InvalidLLMJustification):
            validate_llm_justification(
                "The Access classification follows from an unspecified signal.",
                classification(),
                low_confidence=False,
            )

    def test_valid_gemini_rewrite_uses_same_grounded_contract(self) -> None:
        models = FakeGeminiModels(
            "The Access classification is supported by the password evidence."
        )
        rewriter = GeminiJustificationRewriter(
            SimpleNamespace(models=models), model="gemini-test-model"
        )

        output = rewriter.rewrite(
            classification(), "fallback", low_confidence=False
        )

        self.assertIn("Access", output)
        self.assertEqual(models.calls[0]["model"], "gemini-test-model")
        self.assertEqual(models.calls[0]["config"]["max_output_tokens"], 180)
        self.assertNotIn("reset password", models.calls[0]["contents"])

    def test_provider_factory_rejects_unknown_provider(self) -> None:
        with patch.dict("os.environ", {"LLM_PROVIDER": "unknown"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "gemini.*openai"):
                rewriter_from_environment()

    def test_low_confidence_rewrite_must_preserve_warning(self) -> None:
        with self.assertRaises(InvalidLLMJustification):
            validate_llm_justification(
                "The Access classification is supported by password evidence.",
                classification(confidence=0.4),
                low_confidence=True,
            )

    def test_provider_failure_falls_back_without_changing_class(self) -> None:
        service = DeliveryPredictionService(
            FakeClassifier(classification()),
            justification_rewriter=RaisingRewriter(),
        )

        output = service.predict("reset password")

        self.assertEqual(output.class_, "Access")
        self.assertIn("password", output.justification)
        self.assertIn("strongest positive model evidence", output.justification)


if __name__ == "__main__":
    unittest.main()
