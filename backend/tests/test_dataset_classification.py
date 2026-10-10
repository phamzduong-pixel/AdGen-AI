import json
import unittest

from app.services.learning_dataset.models import (
    DatasetType,
    FeedbackScore,
    LearningDatasetRecord,
    UserEditDelta,
)
from app.services.learning_dataset.service import LearningDatasetService
from tests.dataset_writer_isolation import temporary_learning_dataset_service


class DatasetClassificationTest(unittest.TestCase):
    def setUp(self):
        self._temporary_service = temporary_learning_dataset_service()
        self.service, self.storage_path = self._temporary_service.__enter__()

    def tearDown(self):
        self._temporary_service.__exit__(None, None, None)

    def test_dataset_classification_rules(self):
        # 1. Basic generation -> Evaluation dataset
        rec1 = LearningDatasetRecord(
            interaction_id="eval-001",
            input_context={"platform": "facebook"},
            generated_content="Content 1",
        )
        self.service.log_generation(rec1)
        self.assertIn(DatasetType.EVALUATION, rec1.eligible_dataset_types)

        # 2. Brand-linked generation -> Personalization dataset
        rec2 = LearningDatasetRecord(
            interaction_id="pers-002",
            input_context={"platform": "tiktok", "brand_name": "AdGen Luxe"},
            generated_content="Content 2",
        )
        self.service.log_generation(rec2)
        self.assertIn(DatasetType.PERSONALIZATION, rec2.eligible_dataset_types)

        # 3. Rated 5-star -> Fine-tuning & Recommendation dataset
        rec3 = LearningDatasetRecord(
            interaction_id="fine-003",
            input_context={"platform": "shopee"},
            generated_content="Content 3",
        )
        self.service.log_generation(rec3)
        self.service.record_feedback(
            "fine-003",
            FeedbackScore(rating=5, is_positive=True, review_comments="Rất tốt!"),
        )
        self.assertIn(DatasetType.FINE_TUNING, rec3.eligible_dataset_types)
        self.assertIn(DatasetType.RECOMMENDATION, rec3.eligible_dataset_types)

    def test_query_and_export_fine_tuning_dataset(self):
        rec_good = LearningDatasetRecord(
            interaction_id="good-01",
            input_context={"platform": "google_ads"},
            generated_content="RSA Headlines...",
            is_high_quality_example=True,
            user_feedback=FeedbackScore(rating=5, is_positive=True),
        )
        rec_draft = LearningDatasetRecord(
            interaction_id="draft-02",
            input_context={"platform": "google_ads"},
            generated_content="Draft...",
        )
        self.service.log_generation(rec_good)
        self.service.log_generation(rec_draft)

        fine_tuning_records = self.service.query_dataset(dataset_type=DatasetType.FINE_TUNING)
        self.assertEqual(len(fine_tuning_records), 1)
        self.assertEqual(fine_tuning_records[0].interaction_id, "good-01")

        jsonl_output = self.service.export_to_jsonl(fine_tuning_records, target_dataset_type=DatasetType.FINE_TUNING)
        self.assertTrue(len(jsonl_output) > 0)
        parsed = json.loads(jsonl_output)
        self.assertEqual(parsed["interaction_id"], "good-01")
        self.assertIn("fine_tuning", parsed["eligible_datasets"])


if __name__ == "__main__":
    unittest.main()
