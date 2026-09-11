"""Validated contracts shared by inference and future delivery interfaces."""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TicketInput(BaseModel):
    """Validated input accepted by the inference service."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=50_000)

    @field_validator("text")
    @classmethod
    def normalize_and_reject_blank_text(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Ticket text cannot be blank.")
        return normalized


class Evidence(BaseModel):
    """A positive local feature contribution supporting the predicted class."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    feature: str = Field(min_length=1)
    tfidf: float = Field(gt=0.0)
    coefficient: float = Field(gt=0.0)
    contribution: float = Field(gt=0.0)

    @field_validator("tfidf", "coefficient", "contribution")
    @classmethod
    def require_finite_number(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Evidence values must be finite.")
        return value


class ClassificationResult(BaseModel):
    """Internal deterministic output before justification rendering."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    class_: str = Field(alias="class", min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: tuple[Evidence, ...]


class PredictionOutput(BaseModel):
    """Final public output required by the challenge specification."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    class_: str = Field(alias="class", min_length=1)
    justification: str = Field(min_length=1)
