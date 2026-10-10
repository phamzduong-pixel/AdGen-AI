"""Expected-failure characterization of the CP-2 sanitized-stream contract."""

import types
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.schemas.message import MessageCreate
from app.services import ai_service, message_service
from app.services.message_service import get_messages_service
from app.services.message_service import stream_message_service
from app.services.output_validator.models import ValidationResult

from test_stream_lifecycle_cp1 import FakeGeminiModels, NoRetrieval


class ExpectedSanitizedStreamContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.Session = sessionmaker(bind=cls.engine)
        Base.metadata.create_all(bind=cls.engine)

    def setUp(self):
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.Session()
        self.user = User(
            username="cp1-expected-user",
            email="cp1-expected@example.com",
            hashed_password="not-used",
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)
        self.conversation = Conversation(title="CP-1 expected", user_id=self.user.id)
        self.db.add(self.conversation)
        self.db.commit()
        self.db.refresh(self.conversation)

    def tearDown(self):
        self.db.close()

    def test_frontend_reload_and_database_receive_final_sanitized_content(self):
        fake_models = FakeGeminiModels(["RAW CONTENT"])
        validation = ValidationResult(
            is_valid=True,
            sanitized_content="FINAL CONTENT",
            issues=[],
        )

        with patch.object(
            message_service.external_retrieval_service,
            "retrieve",
            return_value=NoRetrieval(),
        ), patch.object(
            ai_service,
            "client",
            types.SimpleNamespace(models=fake_models),
        ), patch.object(
            ai_service.output_validation_service,
            "validate_and_sanitize",
            return_value=validation,
        ), patch.object(ai_service.learning_dataset_service, "log_generation"):
            streamed_content = "".join(
                stream_message_service(
                    message=MessageCreate(
                        conversation_id=self.conversation.id,
                        content="Viết nội dung quảng cáo",
                    ),
                    db=self.db,
                    current_user=self.user,
                )
            )

        self.assertEqual(streamed_content, "RAW CONTENT")

        messages_after_reload = get_messages_service(
            conversation_id=self.conversation.id,
            db=self.db,
            current_user=self.user,
        )
        assistant = messages_after_reload[-1]
        self.assertEqual(assistant["role"], "assistant")
        self.assertEqual(assistant["content"], "FINAL CONTENT")


if __name__ == "__main__":
    unittest.main()
