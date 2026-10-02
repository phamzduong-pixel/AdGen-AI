import json
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.saved_content import SavedContent  # noqa: F401
from app.models.uploaded_file import UploadedFile  # noqa: F401
from app.models.user import User
from app.schemas.content_tools import ContentEvaluationRequest
from app.schemas.content_tools import ContentVariantRequest
from app.schemas.saved_content import SavedContentCreate
from app.services.content_evaluation_service import evaluate_content_service
from app.services.content_variant_service import generate_variants_service
from app.services.saved_content_service import save_content_service


CRITERION_NAMES = [
    "Mức độ thu hút",
    "Độ rõ ràng",
    "Phù hợp khách hàng mục tiêu",
    "Phù hợp nền tảng quảng cáo",
    "Chất lượng CTA",
    "Tính thuyết phục",
    "Độ dài",
    "Khả năng chuyển đổi",
    "Chính tả và cách trình bày",
]


class ContentToolsTestCase(unittest.TestCase):
    def setUp(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()
        self.user = User(
            username="owner",
            email="owner@example.com",
            hashed_password="test",
        )
        self.other_user = User(
            username="other",
            email="other@example.com",
            hashed_password="test",
        )
        self.db.add_all([self.user, self.other_user])
        self.db.flush()
        self.conversation = Conversation(title="Campaign", user_id=self.user.id)
        other_conversation = Conversation(
            title="Other",
            user_id=self.other_user.id,
        )
        self.db.add_all([self.conversation, other_conversation])
        self.db.flush()
        self.message = Message(
            conversation_id=self.conversation.id,
            role="assistant",
            content="Quảng cáo mẫu",
        )
        self.other_message = Message(
            conversation_id=other_conversation.id,
            role="assistant",
            content="Nội dung riêng tư",
        )
        self.db.add_all([self.message, self.other_message])
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_request_rejects_empty_or_ambiguous_source(self):
        with self.assertRaises(ValidationError):
            ContentEvaluationRequest()
        with self.assertRaises(ValidationError):
            ContentEvaluationRequest(message_id=1, content="Nội dung")

    def test_evaluation_is_structured_and_checks_ownership(self):
        response = {
            "overall_score": 84,
            "criteria": [
                {"name": name, "score": 84, "comment": "Nhận xét"}
                for name in CRITERION_NAMES
            ],
            "strengths": ["CTA rõ ràng"],
            "improvements": ["Rút gọn tiêu đề"],
            "suggested_revision": "Bản chỉnh sửa",
        }
        with patch(
            "app.services.content_tool_utils.generate_structured_content",
            return_value=json.dumps(response, ensure_ascii=False),
        ):
            result = evaluate_content_service(
                ContentEvaluationRequest(message_id=self.message.id),
                self.db,
                self.user,
            )
        self.assertEqual(result.overall_score, 84)
        self.assertEqual(len(result.criteria), 9)

        with self.assertRaises(HTTPException) as context:
            evaluate_content_service(
                ContentEvaluationRequest(message_id=self.other_message.id),
                self.db,
                self.user,
            )
        self.assertEqual(context.exception.status_code, 404)

    def test_variant_response_and_explicit_library_save(self):
        response = {
            "variants": [
                {
                    "label": label,
                    "strategy": strategy,
                    "title": f"Tiêu đề {label}",
                    "content": f"Nội dung {label}",
                    "cta": f"CTA {label}",
                }
                for label, strategy in (
                    ("A", "Nhấn mạnh lợi ích"),
                    ("B", "Nhấn mạnh giá hoặc ưu đãi"),
                    ("C", "Nhấn mạnh cảm xúc hoặc nỗi đau khách hàng"),
                )
            ]
        }
        with patch(
            "app.services.content_tool_utils.generate_structured_content",
            return_value=json.dumps(response, ensure_ascii=False),
        ):
            result = generate_variants_service(
                ContentVariantRequest(message_id=self.message.id),
                self.db,
                self.user,
            )
        self.assertEqual([item.label for item in result.variants], ["A", "B", "C"])

        data = SavedContentCreate(
            conversation_id=self.conversation.id,
            title="Phiên bản A",
            content="Nội dung A\n\nCTA: CTA A",
            platform="facebook",
        )
        first = save_content_service(data, self.db, self.user)
        second = save_content_service(data, self.db, self.user)
        self.assertIsNone(first.message_id)
        self.assertEqual(first.id, second.id)


if __name__ == "__main__":
    unittest.main()
