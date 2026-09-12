"""Reusable deterministic inference for the frozen E04 pipeline."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.exceptions import NotFittedError
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.utils.validation import check_is_fitted

from .schemas import ClassificationResult, Evidence, TicketInput


class TicketClassifier:
    """Validate tickets and expose class, confidence and faithful local evidence."""

    def __init__(self, pipeline: Pipeline, *, top_k_evidence: int = 4) -> None:
        if not 1 <= top_k_evidence <= 10:
            raise ValueError("top_k_evidence must be between 1 and 10.")
        self._pipeline = pipeline
        self._top_k_evidence = top_k_evidence
        self._validate_pipeline()

    @classmethod
    def from_path(
        cls,
        path: str | Path,
        *,
        top_k_evidence: int = 4,
    ) -> "TicketClassifier":
        model_path = Path(path)
        if not model_path.is_file():
            raise FileNotFoundError(f"Model artifact not found: {model_path}")
        pipeline = joblib.load(model_path)
        if not isinstance(pipeline, Pipeline):
            raise TypeError("Model artifact must contain a scikit-learn Pipeline.")
        return cls(pipeline, top_k_evidence=top_k_evidence)

    @property
    def classes(self) -> tuple[str, ...]:
        return tuple(str(label) for label in self._classifier.classes_)

    def classify(self, ticket: str | TicketInput) -> ClassificationResult:
        request = ticket if isinstance(ticket, TicketInput) else TicketInput(text=ticket)
        probabilities = self._pipeline.predict_proba([request.text])[0]
        predicted_index = int(np.argmax(probabilities))
        predicted_class = self.classes[predicted_index]
        evidence = self._extract_evidence(request.text, predicted_index)
        return ClassificationResult(
            **{
                "class": predicted_class,
                "confidence": float(probabilities[predicted_index]),
                "evidence": evidence,
            }
        )

    @property
    def _vectorizer(self) -> TfidfVectorizer:
        return self._pipeline.named_steps["tfidf"]

    @property
    def _classifier(self) -> LogisticRegression:
        return self._pipeline.named_steps["classifier"]

    def _validate_pipeline(self) -> None:
        required_steps = {"tfidf", "classifier"}
        missing = required_steps - set(self._pipeline.named_steps)
        if missing:
            raise ValueError(f"Pipeline is missing required steps: {sorted(missing)}")
        if not isinstance(self._pipeline.named_steps["tfidf"], TfidfVectorizer):
            raise TypeError("Pipeline step 'tfidf' must be a TfidfVectorizer.")
        if not isinstance(self._pipeline.named_steps["classifier"], LogisticRegression):
            raise TypeError("Pipeline step 'classifier' must be a LogisticRegression.")
        try:
            check_is_fitted(self._vectorizer)
            check_is_fitted(self._classifier)
        except NotFittedError as error:
            raise ValueError("Inference requires a fitted pipeline.") from error
        if len(self._classifier.classes_) != self._classifier.coef_.shape[0]:
            raise ValueError("Classifier classes and coefficient rows are inconsistent.")

    def _extract_evidence(
        self,
        text: str,
        predicted_index: int,
    ) -> tuple[Evidence, ...]:
        vector = self._vectorizer.transform([text])
        present_indices = vector.indices
        tfidf_values = vector.data
        coefficients = self._classifier.coef_[predicted_index, present_indices]
        contributions = tfidf_values * coefficients
        feature_names = self._vectorizer.get_feature_names_out()

        evidence: list[Evidence] = []
        for position in np.argsort(contributions)[::-1]:
            contribution = float(contributions[position])
            if contribution <= 0.0:
                continue
            evidence.append(
                Evidence(
                    feature=str(feature_names[int(present_indices[position])]),
                    tfidf=float(tfidf_values[position]),
                    coefficient=float(coefficients[position]),
                    contribution=contribution,
                )
            )
            if len(evidence) == self._top_k_evidence:
                break
        return tuple(evidence)
