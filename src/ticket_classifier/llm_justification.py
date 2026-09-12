"""Optional LLM rewriting constrained by deterministic classifier evidence."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from .schemas import ClassificationResult


DEFAULT_LLM_MODEL = "gpt-5-mini"
MAX_JUSTIFICATION_CHARACTERS = 600
MAX_SENTENCES = 3


class InvalidLLMJustification(ValueError):
    """Raised when generated prose violates the grounded-output contract."""


class OpenAIJustificationRewriter:
    """Rewrite model evidence as natural prose through the OpenAI Responses API."""

    def __init__(self, client: Any, *, model: str = DEFAULT_LLM_MODEL) -> None:
        if not model.strip():
            raise ValueError("The OpenAI model name cannot be blank.")
        self._client = client
        self._model = model.strip()

    @classmethod
    def from_environment(cls) -> "OpenAIJustificationRewriter":
        from openai import OpenAI

        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required when LLM rewriting is enabled.")
        model = os.environ.get("OPENAI_MODEL", DEFAULT_LLM_MODEL)
        return cls(OpenAI(api_key=api_key, timeout=8.0, max_retries=1), model=model)

    def rewrite(
        self,
        classification: ClassificationResult,
        fallback: str,
        *,
        low_confidence: bool,
    ) -> str:
        evidence = [item.feature for item in classification.evidence[:3]]
        if not evidence:
            return fallback

        payload = {
            "predicted_class": classification.class_,
            "confidence": round(classification.confidence, 6),
            "low_confidence": low_confidence,
            "allowed_evidence": evidence,
            "deterministic_fallback": fallback,
        }
        response = self._client.responses.create(
            model=self._model,
            instructions=(
                "Rewrite the supplied deterministic ticket-classification explanation in "
                "clear natural English. The predicted class is immutable. Use one to three "
                "sentences and only the supplied evidence; include the exact class name and "
                "at least one allowed evidence term verbatim. If low_confidence is true, say "
                "that human review may be appropriate. Do not add facts, causes, actions, "
                "recommendations, or evidence. Return only the explanation text."
            ),
            input=json.dumps(payload, ensure_ascii=True),
            max_output_tokens=180,
            store=False,
        )
        candidate = str(response.output_text).strip()
        validate_llm_justification(candidate, classification, low_confidence=low_confidence)
        return candidate


def validate_llm_justification(
    text: str,
    classification: ClassificationResult,
    *,
    low_confidence: bool,
) -> None:
    """Fail closed unless generated prose remains within the grounded contract."""

    if not text or len(text) > MAX_JUSTIFICATION_CHARACTERS or "\n" in text:
        raise InvalidLLMJustification("Generated justification has an invalid shape.")
    sentence_count = len(re.findall(r"[.!?](?:\s|$)", text))
    if not 1 <= sentence_count <= MAX_SENTENCES:
        raise InvalidLLMJustification("Generated justification must have 1-3 sentences.")
    if classification.class_.casefold() not in text.casefold():
        raise InvalidLLMJustification("Generated justification changed or omitted the class.")
    evidence = [item.feature.casefold() for item in classification.evidence[:3]]
    if evidence and not any(term in text.casefold() for term in evidence):
        raise InvalidLLMJustification("Generated justification omitted grounded evidence.")
    if low_confidence and "human review" not in text.casefold():
        raise InvalidLLMJustification("Generated justification omitted the review warning.")
    if low_confidence and not any(
        marker in text.casefold() for marker in ("low confidence", "human review", "uncertain")
    ):
        raise InvalidLLMJustification("Generated justification omitted the confidence warning.")
