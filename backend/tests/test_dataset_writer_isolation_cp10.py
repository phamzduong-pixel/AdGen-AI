"""CP-10 coverage for direct temporary LearningDatasetService use."""

import hashlib
import unittest
from pathlib import Path

from app.services.learning_dataset.models import LearningDatasetRecord
from tests.dataset_writer_isolation import temporary_learning_dataset_service


DATASET = Path(__file__).resolve().parents[1] / "app" / "data" / "learning_dataset.jsonl"


def fingerprint():
    content = DATASET.read_bytes()
    return hashlib.sha256(content).hexdigest(), len(content)


class TemporaryLearningDatasetServiceCp10Tests(unittest.TestCase):
    def test_direct_persistence_is_redirected_and_cleaned_up(self):
        before = fingerprint()

        with temporary_learning_dataset_service() as (service, target):
            service.log_generation(
                LearningDatasetRecord(
                    interaction_id="cp10-temporary-record",
                    generated_content="temporary only",
                )
            )
            self.assertTrue(target.is_file())
            self.assertIsNotNone(service.get_record("cp10-temporary-record"))

        self.assertFalse(target.exists())
        self.assertFalse(target.parent.exists())
        self.assertEqual(fingerprint(), before)


if __name__ == "__main__":
    unittest.main()
