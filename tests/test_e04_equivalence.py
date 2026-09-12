"""Characterization tests for the migration of E04 into the reusable package.

This suite intentionally loads only the frozen train and validation splits. The
200-ticket final test split is outside the scope of development verification.
"""

from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ticket_classifier.config import (
    DEFAULT_TRAIN_PATH,
    DEFAULT_VALIDATION_PATH,
    EXPECTED_TRAIN_ROWS,
    EXPECTED_TRAIN_SHA256,
    EXPECTED_VALIDATION_ROWS,
    EXPECTED_VALIDATION_SHA256,
    LABEL_COLUMN,
    DEFAULT_DEVELOPMENT_MODEL_PATH,
    TEXT_COLUMN,
)
from ticket_classifier.model import build_e04_pipeline, moderate_class_weights


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


class E04EquivalenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if sha256_file(DEFAULT_TRAIN_PATH) != EXPECTED_TRAIN_SHA256:
            raise AssertionError("The frozen training split has an unexpected hash.")
        if sha256_file(DEFAULT_VALIDATION_PATH) != EXPECTED_VALIDATION_SHA256:
            raise AssertionError("The frozen validation split has an unexpected hash.")

        cls.train = pd.read_csv(DEFAULT_TRAIN_PATH, encoding="utf-8")
        cls.validation = pd.read_csv(DEFAULT_VALIDATION_PATH, encoding="utf-8")
        if len(cls.train) != EXPECTED_TRAIN_ROWS:
            raise AssertionError("The frozen training split has an unexpected row count.")
        if len(cls.validation) != EXPECTED_VALIDATION_ROWS:
            raise AssertionError("The frozen validation split has an unexpected row count.")

        cls.legacy = joblib.load(DEFAULT_DEVELOPMENT_MODEL_PATH)
        cls.canonical = build_e04_pipeline(cls.train[LABEL_COLUMN])
        cls.canonical.fit(cls.train[TEXT_COLUMN], cls.train[LABEL_COLUMN])

    def test_configuration_matches_frozen_e04(self) -> None:
        legacy_tfidf = self.legacy.named_steps["tfidf"]
        canonical_tfidf = self.canonical.named_steps["tfidf"]
        self.assertEqual(legacy_tfidf.get_params(), canonical_tfidf.get_params())

        legacy_classifier = self.legacy.named_steps["classifier"]
        canonical_classifier = self.canonical.named_steps["classifier"]
        self.assertEqual(
            legacy_classifier.get_params(deep=False),
            canonical_classifier.get_params(deep=False),
        )

    def test_moderate_weights_match_frozen_e04(self) -> None:
        expected = self.legacy.named_steps["classifier"].class_weight
        actual = moderate_class_weights(self.train[LABEL_COLUMN])
        self.assertEqual(set(expected), set(actual))
        for label in expected:
            self.assertAlmostEqual(expected[label], actual[label], places=15)

    def test_vocabulary_and_classes_are_identical(self) -> None:
        legacy_tfidf = self.legacy.named_steps["tfidf"]
        canonical_tfidf = self.canonical.named_steps["tfidf"]
        np.testing.assert_array_equal(
            legacy_tfidf.get_feature_names_out(),
            canonical_tfidf.get_feature_names_out(),
        )
        np.testing.assert_array_equal(
            self.legacy.named_steps["classifier"].classes_,
            self.canonical.named_steps["classifier"].classes_,
        )

    def test_all_validation_predictions_are_identical(self) -> None:
        texts = self.validation[TEXT_COLUMN]
        np.testing.assert_array_equal(
            self.legacy.predict(texts),
            self.canonical.predict(texts),
        )

    def test_all_validation_probabilities_are_numerically_equivalent(self) -> None:
        texts = self.validation[TEXT_COLUMN]
        np.testing.assert_allclose(
            self.legacy.predict_proba(texts),
            self.canonical.predict_proba(texts),
            rtol=1e-12,
            atol=1e-12,
        )


if __name__ == "__main__":
    unittest.main()
