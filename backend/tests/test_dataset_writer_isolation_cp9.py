"""CP-9 tests for safe isolation of learning-dataset writes."""

import hashlib
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.services import ai_service
from app.services.output_validator.models import ValidationResult
from tests.dataset_writer_isolation import isolated_ai_writer


DATASET = Path(__file__).resolve().parents[1] / "app" / "data" / "learning_dataset.jsonl"


def dataset_fingerprint():
    content = DATASET.read_bytes()
    return hashlib.sha256(content).hexdigest(), len(content)


class DatasetWriterIsolationCp9Tests(unittest.TestCase):
    def test_default_writer_is_blocked_and_real_dataset_is_unchanged(self):
        before = dataset_fingerprint()
        valid = ValidationResult(is_valid=True, sanitized_content="SAFE", issues=[])

        with isolated_ai_writer() as (blocked_writer, target):
            with patch.object(
                ai_service,
                "client",
                SimpleNamespace(
                    models=SimpleNamespace(
                        generate_content=lambda **_kwargs: SimpleNamespace(text="RAW")
                    )
                ),
            ), patch.object(
                ai_service.output_validation_service,
                "validate_and_sanitize",
                return_value=valid,
            ):
                self.assertEqual(
                    ai_service.ask_ai([{"role": "user", "content": "offline"}]),
                    "SAFE",
                )

        blocked_writer.assert_called_once()
        self.assertIsNone(target)
        self.assertEqual(dataset_fingerprint(), before)

    def test_persistence_mode_writes_only_to_temporary_target(self):
        before = dataset_fingerprint()
        valid = ValidationResult(is_valid=True, sanitized_content="SAFE", issues=[])

        with isolated_ai_writer(persist_to_temp=True) as (isolated_service, target):
            with patch.object(
                ai_service,
                "client",
                SimpleNamespace(
                    models=SimpleNamespace(
                        generate_content=lambda **_kwargs: SimpleNamespace(text="RAW")
                    )
                ),
            ), patch.object(
                ai_service.output_validation_service,
                "validate_and_sanitize",
                return_value=valid,
            ):
                self.assertEqual(
                    ai_service.ask_ai([{"role": "user", "content": "offline"}]),
                    "SAFE",
                )

            self.assertIs(isolated_service, ai_service.learning_dataset_service)
            self.assertTrue(target.is_file())
            self.assertIn('"generated_content": "SAFE"', target.read_text(encoding="utf-8"))

        self.assertFalse(target.exists())
        self.assertEqual(dataset_fingerprint(), before)

    def test_exception_restores_writer_and_cleans_temporary_target(self):
        before = dataset_fingerprint()
        captured_target = None

        try:
            with isolated_ai_writer(persist_to_temp=True) as (_service, target):
                captured_target = target
                self.assertTrue(target.parent.is_dir())
                raise RuntimeError("controlled CP-9 failure")
        except RuntimeError as error:
            self.assertEqual(str(error), "controlled CP-9 failure")

        self.assertIsNotNone(captured_target)
        self.assertFalse(captured_target.exists())
        self.assertFalse(captured_target.parent.exists())
        self.assertEqual(dataset_fingerprint(), before)


if __name__ == "__main__":
    unittest.main()
