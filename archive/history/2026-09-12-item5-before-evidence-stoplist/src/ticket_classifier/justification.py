"""Faithful deterministic justification for ticket classifications."""

from __future__ import annotations

from .schemas import ClassificationResult

MAX_JUSTIFICATION_EVIDENCE = 3


def deterministic_justification(
    result: ClassificationResult,
    *,
    max_evidence: int = MAX_JUSTIFICATION_EVIDENCE,
) -> str:
    """Render one sentence grounded only in positive local model evidence."""

    if not 1 <= max_evidence <= MAX_JUSTIFICATION_EVIDENCE:
        raise ValueError(
            f"max_evidence must be between 1 and {MAX_JUSTIFICATION_EVIDENCE}."
        )

    features: list[str] = []
    for item in result.evidence:
        if item.feature not in features:
            features.append(item.feature)
        if len(features) == max_evidence:
            break

    if not features:
        return (
            f"The ticket was classified as {result.class_} because its overall term pattern "
            "most closely matches that category, although no individual positive term-level "
            "evidence was available."
        )

    quoted = [f"'{feature}'" for feature in features]
    if len(quoted) == 1:
        evidence_text = f"the term {quoted[0]}"
    else:
        evidence_text = f"the terms {', '.join(quoted[:-1])} and {quoted[-1]}"

    return (
        f"The ticket was classified as {result.class_} because {evidence_text} provided the "
        "strongest positive model evidence for that category."
    )

