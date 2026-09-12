"""Static delivery-safety checks for the container configuration."""

from __future__ import annotations

import unittest

from ticket_classifier.config import PROJECT_ROOT


class ContainerContractTest(unittest.TestCase):
    def test_final_test_is_excluded_from_docker_context(self) -> None:
        dockerignore = (PROJECT_ROOT / ".dockerignore").read_text(encoding="utf-8")
        self.assertIn("data/splits/test.csv", dockerignore.splitlines())

    def test_image_trains_only_from_development_partitions(self) -> None:
        dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8").casefold()
        self.assertIn("train.csv", dockerfile)
        self.assertIn("validation.csv", dockerfile)
        self.assertNotIn("test.csv", dockerfile)
        self.assertNotIn("ticket-final-evaluate", dockerfile)

    def test_production_container_has_no_llm_integration(self) -> None:
        compose = (PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8")
        dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
        app = (PROJECT_ROOT / "interface" / "app.py").read_text(encoding="utf-8")
        for source in (compose, dockerfile, app):
            self.assertNotIn("OPENAI_API_KEY", source)
            self.assertNotIn("GEMINI_API_KEY", source)
            self.assertNotIn("LLM_PROVIDER", source)
        self.assertIn(".[interface]", dockerfile)
        self.assertNotIn(".[delivery]", dockerfile)

    def test_dockerfile_sets_explicit_project_root(self) -> None:
        dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("TICKET_CLASSIFIER_PROJECT_ROOT=/app", dockerfile)


if __name__ == "__main__":
    unittest.main()
