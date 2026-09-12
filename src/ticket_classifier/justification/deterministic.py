"""Faithful deterministic justification for ticket classifications."""

from __future__ import annotations

from ..schemas import ClassificationResult

MAX_JUSTIFICATION_EVIDENCE = 3
WEAK_EVIDENCE_TERMS = frozenset(
    {
        "about", "and", "by", "care", "dear", "el", "for", "hello", "hi", "in",
        "done", "la", "of", "on", "out", "please", "re", "regards", "related", "se", "si", "thank",
        "thanks", "the", "to", "user", "va", "which", "with",
    }
)


def is_informative_evidence(feature: str) -> bool:
    """Return whether a model feature is useful in a human-facing explanation."""

    return feature.casefold().strip() not in WEAK_EVIDENCE_TERMS


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
        if not is_informative_evidence(item.feature):
            continue
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

