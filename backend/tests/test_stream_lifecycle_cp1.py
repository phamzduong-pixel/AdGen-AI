"""Offline CP-2 regression tests for the streaming lifecycle.

These tests deliberately use fake Gemini/retrieval components.  They verify
the raw streaming boundary and canonical final persistence without external IO.
"""

import types
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.schemas.message import MessageCreate
from app.services import ai_service
from app.services import message_service
from app.services.external_retrieval.evidence import Evidence, EvidenceSourceType
from app.services.external_retrieval.provider import (
    SearchProviderResult,
    SearchProviderStatus,
)
from app.services.output_validator.models import (
    ValidationErrorType,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)
from app.services.message_service import stream_message_service


class FakeGeminiModels:
    def __init__(self, chunks):
        self.chunks = chunks
        self.stream_calls = 0

    def generate_content_stream(self, **kwargs):
        self.stream_calls += 1
        return [types.SimpleNamespace(text=chunk) for chunk in self.chunks]


class NoRetrieval:
    was_requested = False
    provider_result = None


def citation_evidence_result():
    evidence = Evidence(
        evidence_id="stream-source",
        title="Source",
        source_url="https://example.com/source",
        publisher="Example",
        retrieved_at=datetime(2026, 10, 5, tzinfo=timezone.utc),
        excerpt="Reference excerpt.",
        source_type=EvidenceSourceType.SEARCH_RESULT,
    )
    return SearchProviderResult(
        status=SearchProviderStatus.SUCCESS,
        evidences=(evidence,),
    )


class StreamLifecycleCp1Tests(unittest.TestCase):
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
            username="cp1-user",
            email="cp1@example.com",
            hashed_password="not-used",
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)
        self.conversation = Conversation(title="CP-1", user_id=self.user.id)
        self.db.add(self.conversation)
        self.db.commit()
        self.db.refresh(self.conversation)

    def tearDown(self):
        self.db.close()

    def stream_message(self, content="Viết nội dung quảng cáo"):
        return stream_message_service(
            message=MessageCreate(
                conversation_id=self.conversation.id,
                content=content,
            ),
            db=self.db,
            current_user=self.user,
        )

    def test_successful_fake_gemini_stream_reaches_frontend_and_persists_canonical_final(self):
        fake_models = FakeGeminiModels(["RAW ", "CONTENT"])
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
        ), patch.object(
            ai_service.learning_dataset_service,
            "log_generation",
        ) as log_generation:
            frontend_chunks = list(self.stream_message())

        self.assertEqual(frontend_chunks, ["RAW ", "CONTENT"])
        self.assertEqual("".join(frontend_chunks), "RAW CONTENT")
        self.assertEqual(fake_models.stream_calls, 1)
        log_generation.assert_called_once()
        self.assertEqual(
            log_generation.call_args.args[0].generated_content,
            "FINAL CONTENT",
        )

        assistant = (
            self.db.query(Message)
            .filter(
                Message.conversation_id == self.conversation.id,
                Message.role == "assistant",
            )
            .one()
        )
        self.assertEqual(assistant.content, "FINAL CONTENT")

    def test_provider_error_after_partial_output_emits_marker_without_assistant_record(self):
        def failing_stream(**kwargs):
            yield "PARTIAL"
            raise RuntimeError("fake provider exploded")

        with patch.object(
            message_service.external_retrieval_service,
            "retrieve",
            return_value=NoRetrieval(),
        ), patch.object(
            message_service,
            "stream_ai",
            side_effect=failing_stream,
        ):
            output = list(self.stream_message())

        self.assertEqual(output, ["PARTIAL", "\n[ADGEN_STREAM_ERROR]\n"])
        self.assertEqual(
            self.db.query(Message)
            .filter(
                Message.conversation_id == self.conversation.id,
                Message.role == "assistant",
            )
            .count(),
            0,
        )
        self.assertEqual(
            self.db.query(Message)
            .filter(
                Message.conversation_id == self.conversation.id,
                Message.role == "user",
            )
            .count(),
            1,
        )

    def test_valid_citation_does_not_bypass_final_output_validation_failure(self):
        fake_models = FakeGeminiModels(["Claim supported [S1]"])
        invalid = ValidationResult(
            is_valid=False,
            sanitized_content="fallback",
            issues=[
                ValidationIssue(
                    error_type=ValidationErrorType.FORBIDDEN_CLAIM,
                    severity=ValidationSeverity.ERROR,
                    message="fake validator rejection",
                )
            ],
        )

        with patch.object(
            ai_service,
            "client",
            types.SimpleNamespace(models=fake_models),
        ), patch.object(
            ai_service.output_validation_service,
            "validate_and_sanitize",
            return_value=invalid,
        ), patch.object(
            ai_service.learning_dataset_service,
            "log_generation",
        ) as log_generation:
            stream = ai_service.stream_ai(
                [{"role": "user", "content": "Research current trend"}],
                external_retrieval_requested=True,
                external_retrieval_result=citation_evidence_result(),
            )
            yielded = []
            with self.assertRaisesRegex(RuntimeError, "validation rejected"):
                while True:
                    yielded.append(next(stream))

        self.assertEqual(yielded, ["Claim supported [S1]"])
        log_generation.assert_not_called()


if __name__ == "__main__":
    unittest.main()
