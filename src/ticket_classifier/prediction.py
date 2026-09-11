"""Public prediction service combining classification and justification."""

from __future__ import annotations

from pathlib import Path

from .inference import TicketClassifier
from .justification import deterministic_justification
from .schemas import ClassificationResult, PredictionOutput, TicketInput


class TicketPredictionService:
    """Return the exact public contract while retaining diagnostic access."""

    def __init__(self, classifier: TicketClassifier) -> None:
        self._classifier = classifier

    @classmethod
    def from_model_path(cls, path: str | Path) -> "TicketPredictionService":
        return cls(TicketClassifier.from_path(path))

    @property
    def classes(self) -> tuple[str, ...]:
        return self._classifier.classes

    def classify(self, ticket: str | TicketInput) -> ClassificationResult:
        """Return diagnostics for internal use and interactive presentation."""

        return self._classifier.classify(ticket)

    def predict(self, ticket: str | TicketInput) -> PredictionOutput:
        """Return exactly the class and one-sentence deterministic justification."""

        classification = self.classify(ticket)
        return PredictionOutput(
            **{
                "class": classification.class_,
                "justification": deterministic_justification(classification),
            }
        )

