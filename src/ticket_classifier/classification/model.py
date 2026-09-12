"""Canonical construction of the model selected in ADR-002."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from ..config import (
    LOGISTIC_REGRESSION_C,
    LOGISTIC_REGRESSION_MAX_ITER,
    LOGISTIC_REGRESSION_SOLVER,
    RANDOM_SEED,
    TFIDF_MIN_DF,
    TFIDF_NGRAM_RANGE,
    TFIDF_NORM,
    TFIDF_SUBLINEAR_TF,
)


def moderate_class_weights(labels: Iterable[str]) -> dict[str, float]:
    """Return the normalized square root of scikit-learn balanced weights.

    The weighted mean across samples is normalized to one. This preserves the
    average regularization scale used by the unweighted E01 configuration.
    """

    counts = Counter(str(label) for label in labels)
    if not counts:
        raise ValueError("At least one label is required to calculate class weights.")

    ordered_counts = sorted(counts.items())
    sample_count = sum(count for _, count in ordered_counts)
    class_count = len(ordered_counts)
    raw = {
        label: math.sqrt(sample_count / (class_count * count))
        for label, count in ordered_counts
    }
    weighted_sum = sum(count * raw[label] for label, count in ordered_counts)
    normalization = sample_count / weighted_sum
    weights = {label: raw[label] * normalization for label, _ in ordered_counts}

    weighted_mean = (
        sum(count * weights[label] for label, count in ordered_counts) / sample_count
    )
    if not math.isclose(weighted_mean, 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError(
            f"Class weights do not have unit sample-weight mean: {weighted_mean}"
        )
    return weights


def build_e04_pipeline(labels: Iterable[str]) -> Pipeline:
    """Build the exact TF-IDF and Logistic Regression pipeline frozen as E04."""

    class_weights = moderate_class_weights(labels)
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    analyzer="word",
                    ngram_range=TFIDF_NGRAM_RANGE,
                    min_df=TFIDF_MIN_DF,
                    norm=TFIDF_NORM,
                    sublinear_tf=TFIDF_SUBLINEAR_TF,
                    dtype=np.float64,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    C=LOGISTIC_REGRESSION_C,
                    solver=LOGISTIC_REGRESSION_SOLVER,
                    max_iter=LOGISTIC_REGRESSION_MAX_ITER,
                    class_weight=class_weights,
                    random_state=RANDOM_SEED,
                ),
            ),
        ]
    )

