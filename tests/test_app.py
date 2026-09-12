"""Integration tests for the thin Streamlit presentation layer."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from ticket_classifier.config import DEFAULT_DEVELOPMENT_MODEL_PATH, PROJECT_ROOT
from ticket_classifier.flow.delivery import DeliveryPredictionService


APP_PATH = PROJECT_ROOT / "interface" / "app.py"
MODEL_PATH = DEFAULT_DEVELOPMENT_MODEL_PATH


class StreamlitInterfaceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not MODEL_PATH.is_file():
            raise AssertionError("Run ticket-train before the interface test suite.")
        cls.service = DeliveryPredictionService.from_model_path(MODEL_PATH)

    @staticmethod
    def run_app() -> AppTest:
        return AppTest.from_file(str(APP_PATH)).run(timeout=30)

    def test_valid_ticket_matches_delivery_service_public_contract(self) -> None:
        text = "reset password for account access"
        expected = self.service.predict(text).model_dump(by_alias=True)
        app = self.run_app()
        app.text_area[0].input(text)
        app.button[0].click()
        app.run(timeout=30)

        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, expected["class"])
        self.assertEqual(json.loads(app.json[0].value), expected)
        self.assertEqual(set(expected), {"class", "justification"})

    def test_blank_ticket_is_handled_without_backend_output(self) -> None:
        app = self.run_app()
        app.button[0].click()
        app.run(timeout=30)

        self.assertFalse(app.exception)
        self.assertTrue(
            any("Enter a ticket" in warning.value for warning in app.warning)
        )
        self.assertFalse(app.json)

    def test_missing_model_stops_with_actionable_message(self) -> None:
        with patch.object(Path, "is_file", return_value=False):
            app = self.run_app()

        self.assertFalse(app.exception)
        self.assertTrue(
            any("Run `ticket-train`" in error.value for error in app.error)
        )
        self.assertFalse(app.text_area)

    def test_optional_diagnostics_flags_low_confidence_without_changing_class(self) -> None:
        text = "zzzxxyyqqq"
        expected = self.service.predict(text).model_dump(by_alias=True)
        app = self.run_app()
        app.text_area[0].input(text)
        app.checkbox[0].check()
        app.button[0].click()
        app.run(timeout=30)

        actual = json.loads(app.json[0].value)
        self.assertEqual(actual, expected)
        self.assertEqual(app.metric[0].value, expected["class"])
        self.assertTrue(
            any("Low-confidence prediction" in warning.value for warning in app.warning)
        )

    def test_interface_source_has_no_dataset_or_final_test_access(self) -> None:
        source = APP_PATH.read_text(encoding="utf-8").casefold()
        forbidden = (
            "test.csv",
            "read_csv",
            "data/splits",
            "default_test",
            "llm_justification",
            "llm_provider",
            "api_key",
        )
        for term in forbidden:
            self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
