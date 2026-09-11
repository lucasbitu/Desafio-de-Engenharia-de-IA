"""Frozen low-confidence policy selected only from E04 validation results."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

LOW_CONFIDENCE_THRESHOLD = 0.60
MINIMUM_ERROR_CAPTURE_RATE = 0.70
MAXIMUM_FLAGGED_RATE = 0.30
THRESHOLD_CANDIDATES = (0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70)


@dataclass(frozen=True)
class ThresholdMetrics:
    threshold: float
    total: int
    total_errors: int
    flagged: int
    errors_captured: int
    flagged_rate: float
    error_capture_rate: float
    accuracy_below: float | None
    accuracy_at_or_above: float | None


def is_low_confidence(
    confidence: float,
    *,
    threshold: float = LOW_CONFIDENCE_THRESHOLD,
) -> bool:
    """Return true only below the frozen threshold; equality is not flagged."""

    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0 and 1.")
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0 and 1.")
    return confidence < threshold


def evaluate_threshold(
    confidences: Iterable[float],
    correctness: Iterable[bool],
    threshold: float,
) -> ThresholdMetrics:
    """Evaluate one policy candidate without training or accessing model inputs."""

    confidence_values = [float(value) for value in confidences]
    correct_values = [bool(value) for value in correctness]
    if len(confidence_values) != len(correct_values):
        raise ValueError("confidences and correctness must have the same length.")
    if not confidence_values:
        raise ValueError("At least one prediction is required.")
    if any(not 0.0 <= value <= 1.0 for value in confidence_values):
        raise ValueError("All confidence values must be between 0 and 1.")
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0 and 1.")

    low = [value < threshold for value in confidence_values]
    total = len(low)
    errors = [not value for value in correct_values]
    total_errors = sum(errors)
    flagged = sum(low)
    errors_captured = sum(flag and error for flag, error in zip(low, errors))
    retained = total - flagged
    correct_below = sum(flag and correct for flag, correct in zip(low, correct_values))
    correct_at_or_above = sum(
        (not flag) and correct for flag, correct in zip(low, correct_values)
    )
    return ThresholdMetrics(
        threshold=threshold,
        total=total,
        total_errors=total_errors,
        flagged=flagged,
        errors_captured=errors_captured,
        flagged_rate=flagged / total,
        error_capture_rate=errors_captured / total_errors if total_errors else 0.0,
        accuracy_below=correct_below / flagged if flagged else None,
        accuracy_at_or_above=correct_at_or_above / retained if retained else None,
    )


def select_lowest_eligible_threshold(
    confidences: Iterable[float],
    correctness: Iterable[bool],
    *,
    candidates: Iterable[float] = THRESHOLD_CANDIDATES,
    minimum_error_capture_rate: float = MINIMUM_ERROR_CAPTURE_RATE,
    maximum_flagged_rate: float = MAXIMUM_FLAGGED_RATE,
) -> ThresholdMetrics:
    """Select the lowest candidate satisfying the frozen operational criterion."""

    confidence_values = list(confidences)
    correct_values = list(correctness)
    evaluated = [
        evaluate_threshold(confidence_values, correct_values, threshold)
        for threshold in sorted(set(candidates))
    ]
    eligible = [
        item
        for item in evaluated
        if item.error_capture_rate >= minimum_error_capture_rate
        and item.flagged_rate <= maximum_flagged_rate
    ]
    if not eligible:
        raise ValueError("No threshold satisfies the operational criterion.")
    return eligible[0]
