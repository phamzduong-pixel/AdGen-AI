import json
import unittest

from app.services.learning_dataset.models import (
    FeedbackScore,
    LearningDatasetRecord,
    UserEditDelta,
)
from app.services.learning_dataset.service import (
    LearningDatasetService,
    learning_dataset_service,
)
from tests.dataset_writer_isolation import temporary_learning_dataset_service


class LearningDatasetTest(unittest.TestCase):
    def setUp(self):
        self._temporary_service = temporary_learning_dataset_service()
        self.service, self.storage_path = self._temporary_service.__enter__()

    def tearDown(self):
        self._temporary_service.__exit__(None, None, None)

    def test_log_generation_and_retrieve(self):
        record = LearningDatasetRecord(
            interaction_id="test-int-001",
            prompt_knowledge={"prompt_type": "facebook", "rules": ["Hook 1-3 lines"]},
            input_context={"product": "Tai nghe AdGen", "platform": "facebook"},
            generated_content="Nội dung quảng cáo Facebook được sinh tự động...",
            tags=["headphones", "facebook_ads"],
        )
        self.service.log_generation(record)

        fetched = self.service.get_record("test-int-001")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.interaction_id, "test-int-001")
        self.assertEqual(fetched.generated_content, "Nội dung quảng cáo Facebook được sinh tự động...")

    def test_record_user_edit_and_feedback(self):
        record = LearningDatasetRecord(
            interaction_id="test-int-002",
            input_context={"platform": "tiktok"},
            generated_content="Bản nháp TikTok 1",
        )
        self.service.log_generation(record)

        # 1. Record User Edit
        delta = UserEditDelta(
            original_text="Bản nháp TikTok 1",
            edited_text="Bản chỉnh sửa TikTok hoàn hảo của người dùng",
            change_ratio=0.35,
        )
        self.service.record_user_edit("test-int-002", delta)

        # 2. Record Positive Feedback
        feedback = FeedbackScore(
            rating=5,
            is_positive=True,
            review_comments="Chuyển đổi rất tốt!",
        )
        self.service.record_feedback("test-int-002", feedback)

        rec = self.service.get_record("test-int-002")
        self.assertIsNotNone(rec.user_edits)
        self.assertEqual(rec.user_edits.edited_text, "Bản chỉnh sửa TikTok hoàn hảo của người dùng")
        self.assertTrue(rec.is_high_quality_example)

    def test_export_to_jsonl(self):
        record = LearningDatasetRecord(
            interaction_id="test-int-003",
            input_context={"platform": "shopee"},
            generated_content="Tiêu đề Shopee tối ưu",
            is_high_quality_example=True,
        )
        self.service.log_generation(record)

        jsonl_output = self.service.export_to_jsonl([record])
        self.assertTrue(len(jsonl_output) > 0)
        parsed = json.loads(jsonl_output)
        self.assertEqual(parsed["interaction_id"], "test-int-003")
        self.assertTrue(parsed["is_high_quality_example"])


if __name__ == "__main__":
    unittest.main()
