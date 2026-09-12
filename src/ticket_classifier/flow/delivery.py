"""Confidence-aware delivery service built on the frozen E04 classifier."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from ..metrics.confidence import is_low_confidence
from ..classification.inference import TicketClassifier
from ..justification.deterministic import deterministic_justification, is_informative_evidence
from ..schemas import ClassificationResult, Evidence, PredictionOutput, TicketInput


class PredictionDiagnostics(BaseModel):
    """Internal information for tests, logging and the interactive interface."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    class_: str = Field(alias="class", min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    low_confidence: bool
    evidence: tuple[Evidence, ...]


class JustificationRewriter(Protocol):
    """Optional presentation-only rewriter; it has no authority over classification."""

    def rewrite(
        self,
        classification: ClassificationResult,
        fallback: str,
        *,
        low_confidence: bool,
    ) -> str: ...


class DeliveryPredictionService:
    """Apply the frozen confidence policy without changing the predicted class."""

    def __init__(
        self,
        classifier: TicketClassifier,
        *,
        justification_rewriter: JustificationRewriter | None = None,
    ) -> None:
        self._classifier = classifier
        self._justification_rewriter = justification_rewriter

    @classmethod
    def from_model_path(
        cls,
        path: str | Path,
        *,
        justification_rewriter: JustificationRewriter | None = None,
    ) -> "DeliveryPredictionService":
        return cls(
            TicketClassifier.from_path(path),
            justification_rewriter=justification_rewriter,
        )

    @property
    def classes(self) -> tuple[str, ...]:
        return self._classifier.classes

    def classify(self, ticket: str | TicketInput) -> ClassificationResult:
        return self._classifier.classify(ticket)

    def diagnose(self, ticket: str | TicketInput) -> PredictionDiagnostics:
        classification = self.classify(ticket)
        return PredictionDiagnostics(
            **{
                "class": classification.class_,
                "confidence": classification.confidence,
                "low_confidence": is_low_confidence(classification.confidence),
                "evidence": classification.evidence,
            }
        )

    def predict(self, ticket: str | TicketInput) -> PredictionOutput:
        diagnostics = self.diagnose(ticket)
        classification = ClassificationResult(
            **{
                "class": diagnostics.class_,
                "confidence": diagnostics.confidence,
                "evidence": diagnostics.evidence,
            }
        )
        fallback = (
            _low_confidence_justification(classification)
            if diagnostics.low_confidence
            else deterministic_justification(classification)
        )
        justification = fallback
        if self._justification_rewriter is not None:
            try:
                justification = self._justification_rewriter.rewrite(
                    classification,
                    fallback,
                    low_confidence=diagnostics.low_confidence,
                )
            except Exception:
                justification = fallback
        return PredictionOutput(
            **{"class": diagnostics.class_, "justification": justification}
        )


def _low_confidence_justification(result: ClassificationResult) -> str:
    features: list[str] = []
    for item in result.evidence:
        if not is_informative_evidence(item.feature):
            continue
        if item.feature not in features:
            features.append(item.feature)
        if len(features) == 3:
            break

    if not features:
        return (
            f"The available evidence most closely supports {result.class_}, but confidence is "
            "low because the ticket contains limited or ambiguous signals."
        )

    quoted = [f"'{feature}'" for feature in features]
    if len(quoted) == 1:
        evidence_text = f"the term {quoted[0]}"
    else:
        evidence_text = f"the terms {', '.join(quoted[:-1])} and {quoted[-1]}"
    return (
        f"The available evidence most closely supports {result.class_}, based on {evidence_text}, "
        "but confidence is low because the ticket contains limited or ambiguous signals."
    )
