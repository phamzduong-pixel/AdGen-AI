import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.database.database import Base
from app.models.conversation import Conversation
from app.models.user import User
from app.schemas.message import MessageCreate
from app.services.external_retrieval.intent_gate import (
    ExternalRetrievalDecision,
    external_retrieval_intent_gate,
)
from app.services.message_service import stream_message_service
from app.services.prompt_service import (
    build_reference_context,
    build_system_prompt,
)


class ExternalRetrievalIntentGateTest(unittest.TestCase):
    def test_required_and_not_required_examples(self):
        cases = [
            ("Viết quảng cáo Facebook cho sản phẩm này", False),
            ("Tạo 5 tiêu đề quảng cáo TikTok", False),
            ("Đổi nội dung hiện tại sang TikTok", False),
            ("Tạo quảng cáo viral trên TikTok", False),
            ("Viết nội dung hướng đến người tiêu dùng", False),
            ("Phân tích xu hướng mỹ phẩm Việt Nam tháng này", True),
            ("Tìm xu hướng mới nhất để viết quảng cáo và dẫn nguồn", True),
            ("Kiểm chứng công dụng sản phẩm bằng nguồn đáng tin cậy", True),
            ("Viết quảng cáo thông thường, không yêu cầu dữ liệu mới", False),
        ]

        for user_text, expected in cases:
            with self.subTest(user_text=user_text):
                result = external_retrieval_intent_gate.decide(user_text)
                self.assertEqual(result.should_retrieve, expected)
                self.assertEqual(
                    result.decision,
                    (
                        ExternalRetrievalDecision.REQUIRED
                        if expected
                        else ExternalRetrievalDecision.NOT_REQUIRED
                    ),
                )

    def test_platform_name_alone_is_not_a_retrieval_signal(self):
        for user_text in (
            "Viết cho Facebook",
            "Đổi sang TikTok",
            "Tạo nội dung YouTube Shorts",
            "Viết bài Shopee",
        ):
            with self.subTest(user_text=user_text):
                self.assertFalse(
                    external_retrieval_intent_gate.decide(user_text).should_retrieve
                )

    def test_empty_or_unrelated_request_is_not_retrieval(self):
        self.assertFalse(external_retrieval_intent_gate.decide("").should_retrieve)
        self.assertFalse(external_retrieval_intent_gate.decide(None).should_retrieve)
        self.assertFalse(
            external_retrieval_intent_gate.decide("Viết lại đoạn mở đầu cho hấp dẫn hơn").should_retrieve
        )


class RetrievalPromptContractTest(unittest.TestCase):
    def test_platform_intelligence_is_independent_from_external_retrieval(self):
        prompt = build_system_prompt(prompt_type="tiktok")

        self.assertIn("PLATFORM INTELLIGENCE: TIKTOK", prompt)
        self.assertNotIn("TRẠNG THÁI TRA CỨU BÊN NGOÀI", prompt)

    def test_unsupported_retrieval_is_explicitly_grounded(self):
        reference = build_reference_context(
            prompt_type="tiktok",
            external_retrieval_requested=True,
        )

        self.assertIn("External Retrieval chưa được kết nối", reference)
        self.assertIn("Không được nói hoặc ngụ ý rằng hệ thống đã tìm kiếm", reference)
        self.assertNotIn("THÔNG TIN XU HƯỚNG ĐÃ XÁC THỰC", reference)


class MessageServiceRetrievalGateIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.Session = sessionmaker(bind=cls.engine)

    def setUp(self):
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.Session()
        self.user = User(
            username="gate-owner",
            email="gate-owner@example.com",
            hashed_password="not-used",
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

    def tearDown(self):
        self.db.close()

    def _create_conversation(self) -> int:
        conversation = Conversation(user_id=self.user.id, title="CP-0")
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation.id

    def _stream_request(self, content: str) -> dict:
        captured = {}

        def fake_stream_ai(*args, **kwargs):
            captured.update(kwargs)
            yield "Nội dung quảng cáo thử nghiệm"

        with patch(
            "app.services.message_service.stream_ai",
            side_effect=fake_stream_ai,
        ):
            list(
                stream_message_service(
                    message=MessageCreate(
                        conversation_id=self._create_conversation(),
                        content=content,
                        prompt_type="facebook",
                    ),
                    db=self.db,
                    current_user=self.user,
                )
            )

        return captured

    def test_normal_ad_request_passes_retrieval_false(self):
        captured = self._stream_request("Viết quảng cáo Facebook cho sản phẩm này")

        self.assertIn("external_retrieval_requested", captured)
        self.assertFalse(captured["external_retrieval_requested"])

    def test_current_trend_request_passes_retrieval_true(self):
        captured = self._stream_request(
            "Tìm xu hướng mới nhất để viết quảng cáo và dẫn nguồn"
        )

        self.assertIn("external_retrieval_requested", captured)
        self.assertTrue(captured["external_retrieval_requested"])


if __name__ == "__main__":
    unittest.main()
