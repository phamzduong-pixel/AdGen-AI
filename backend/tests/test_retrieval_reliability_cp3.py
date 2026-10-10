"""Offline CP-3 tests for retrieval failure isolation and evidence safety."""

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.database.database import Base
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.trend_report import TrendReport
from app.models.user import User
from app.schemas.message import MessageCreate
from app.services import ai_service, message_service
from app.services.external_retrieval.evidence import (
    Evidence,
    EvidenceSourceType,
)
from app.services.external_retrieval.evidence_context import (
    build_evidence_prompt_context,
    build_retrieval_fallback_response,
)
from app.services.external_retrieval.provider import (
    SearchProviderResult,
    SearchProviderStatus,
)
from app.services.external_retrieval.retrieval_service import ExternalRetrievalService
from app.services.message_service import create_message_service, stream_message_service


class ResultProvider:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def search(self, query, *, limit=None):
        self.calls.append((query, limit))
        return self.result


class RaisingProvider:
    def __init__(self, error):
        self.error = error
        self.calls = 0

    def search(self, query, *, limit=None):
        self.calls += 1
        raise self.error


def valid_evidence(evidence_id="cp3-source"):
    return Evidence(
        evidence_id=evidence_id,
        title="Current market report",
        source_url="https://example.com/report",
        publisher="Example",
        retrieved_at=datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc),
        excerpt="Demand is increasing.",
        source_type=EvidenceSourceType.SEARCH_RESULT,
    )


def malformed_evidence():
    return Evidence(
        evidence_id="malformed-source",
        title="Malformed source",
        source_url="not-a-url",
        publisher="Example",
        retrieved_at=datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc),
        excerpt="This record must not become a citation.",
        source_type=EvidenceSourceType.SEARCH_RESULT,
    )


class RetrievalBoundaryCp3Tests(unittest.TestCase):
    def test_success_keeps_only_normalized_valid_evidence(self):
        provider = ResultProvider(
            SearchProviderResult(
                status=SearchProviderStatus.SUCCESS,
                evidences=(malformed_evidence(), valid_evidence()),
            )
        )

        outcome = ExternalRetrievalService(provider).retrieve(
            "Research the latest skincare market trends"
        )

        self.assertTrue(outcome.was_requested)
        self.assertEqual(outcome.status, SearchProviderStatus.SUCCESS)
        self.assertEqual(len(outcome.provider_result.evidences), 1)
        self.assertEqual(outcome.provider_result.evidences[0].evidence_id, "cp3-source")
        self.assertEqual(outcome.provider_result.metadata["malformed_evidence"], 1)
        self.assertEqual(len(provider.calls), 1)

    def test_timeout_and_provider_exception_are_safe_statuses(self):
        timeout_provider = ResultProvider(
            SearchProviderResult(status=SearchProviderStatus.TIMEOUT)
        )
        timeout = ExternalRetrievalService(timeout_provider).retrieve(
            "Research the latest skincare market trends"
        )
        self.assertEqual(timeout.status, SearchProviderStatus.TIMEOUT)
        self.assertEqual(timeout.provider_result.evidences, ())

        raising_provider = RaisingProvider(RuntimeError("offline fake failure"))
        failed = ExternalRetrievalService(raising_provider).retrieve(
            "Research the latest skincare market trends"
        )
        self.assertEqual(failed.status, SearchProviderStatus.NETWORK_ERROR)
        self.assertEqual(failed.provider_result.evidences, ())
        self.assertEqual(raising_provider.calls, 1)

    def test_empty_and_all_malformed_evidence_have_no_citation(self):
        successful_empty = ExternalRetrievalService(
            ResultProvider(
                SearchProviderResult(
                    status=SearchProviderStatus.SUCCESS,
                    evidences=(),
                )
            )
        ).retrieve("Research the latest skincare market trends")
        self.assertEqual(successful_empty.status, SearchProviderStatus.SUCCESS)
        self.assertEqual(successful_empty.provider_result.evidences, ())

        empty = ExternalRetrievalService(
            ResultProvider(SearchProviderResult(status=SearchProviderStatus.EMPTY))
        ).retrieve("Research the latest skincare market trends")
        self.assertEqual(empty.status, SearchProviderStatus.EMPTY)
        self.assertEqual(empty.provider_result.evidences, ())

        malformed = ExternalRetrievalService(
            ResultProvider(
                SearchProviderResult(
                    status=SearchProviderStatus.SUCCESS,
                    evidences=(malformed_evidence(),),
                )
            )
        ).retrieve("Research the latest skincare market trends")
        self.assertEqual(malformed.status, SearchProviderStatus.INVALID_RESPONSE)
        self.assertEqual(malformed.provider_result.evidences, ())

        context = build_evidence_prompt_context(malformed.provider_result)
        fallback = build_retrieval_fallback_response(malformed.provider_result)
        self.assertEqual(context.citation_ids, frozenset())
        self.assertNotIn("[S1]", context.text)
        self.assertNotIn("[S1]", fallback)

    def test_intent_gate_does_not_call_provider(self):
        provider = ResultProvider(SearchProviderResult(status=SearchProviderStatus.SUCCESS))

        outcome = ExternalRetrievalService(provider).retrieve(
            "Write five TikTok ad headlines for this product"
        )

        self.assertFalse(outcome.was_requested)
        self.assertIsNone(outcome.provider_result)
        self.assertEqual(provider.calls, [])


class MessageRetrievalReliabilityCp3Tests(unittest.TestCase):
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
            username="cp3-user",
            email="cp3@example.com",
            hashed_password="not-used",
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)
        self.conversation = Conversation(user_id=self.user.id, title="CP-3")
        self.db.add(self.conversation)
        self.db.commit()
        self.db.refresh(self.conversation)

    def tearDown(self):
        self.db.close()

    def _request(self, content="Research the latest skincare market trends"):
        return MessageCreate(
            conversation_id=self.conversation.id,
            content=content,
            prompt_type="facebook",
        )

    def _assert_user_durable(self, content):
        durable_db = self.Session()
        try:
            stored = (
                durable_db.query(Message)
                .filter(
                    Message.conversation_id == self.conversation.id,
                    Message.role == "user",
                )
                .one()
            )
            self.assertEqual(stored.content, content)
        finally:
            durable_db.close()

    def test_stream_timeout_commits_user_before_fallback_and_never_calls_gemini(self):
        provider = ResultProvider(SearchProviderResult(status=SearchProviderStatus.TIMEOUT))
        retrieval = ExternalRetrievalService(provider)

        with patch.object(message_service, "external_retrieval_service", retrieval), patch.object(
            ai_service, "_gemini_client", side_effect=AssertionError("Gemini must not run")
        ):
            output = list(stream_message_service(self._request(), self.db, self.user))

        self.assertEqual(provider.calls[0][0], "Research the latest skincare market trends")
        self.assertEqual(len(output), 1)
        self.assertIn("status: timeout", output[0])
        self._assert_user_durable("Research the latest skincare market trends")
        assistant = (
            self.db.query(Message)
            .filter(
                Message.conversation_id == self.conversation.id,
                Message.role == "assistant",
            )
            .one()
        )
        self.assertEqual(assistant.content, output[0])
        user_message = (
            self.db.query(Message)
            .filter(
                Message.conversation_id == self.conversation.id,
                Message.role == "user",
            )
            .one()
        )
        report = (
            self.db.query(TrendReport)
            .filter(TrendReport.source_message_id == user_message.id)
            .one_or_none()
        )
        self.assertIsNotNone(report)
        self.assertEqual(report.provider_status, "timeout")

    def test_stream_provider_exception_commits_user_and_returns_network_fallback(self):
        provider = RaisingProvider(RuntimeError("offline fake failure"))
        retrieval = ExternalRetrievalService(provider)

        with patch.object(message_service, "external_retrieval_service", retrieval), patch.object(
            ai_service, "_gemini_client", side_effect=AssertionError("Gemini must not run")
        ):
            output = list(stream_message_service(self._request(), self.db, self.user))

        self.assertEqual(provider.calls, 1)
        self.assertIn("status: network_error", output[0])
        self._assert_user_durable("Research the latest skincare market trends")

    def test_non_stream_success_keeps_evidence_and_cp2_assistant_contract(self):
        provider = ResultProvider(
            SearchProviderResult(
                status=SearchProviderStatus.SUCCESS,
                evidences=(valid_evidence("non-stream-source"),),
            )
        )
        retrieval = ExternalRetrievalService(provider)
        captured = {}

        def fake_ask_ai(*args, **kwargs):
            captured.update(kwargs)
            return "canonical non-stream response"

        with patch.object(message_service, "external_retrieval_service", retrieval), patch.object(
            message_service, "ask_ai", side_effect=fake_ask_ai
        ):
            result = create_message_service(self._request(), self.db, self.user)

        self.assertEqual(provider.calls, [("Research the latest skincare market trends", None)])
        self.assertEqual(
            captured["external_retrieval_result"].evidences[0].evidence_id,
            "non-stream-source",
        )
        self.assertEqual(result["assistant_message"].content, "canonical non-stream response")
        self._assert_user_durable("Research the latest skincare market trends")


if __name__ == "__main__":
    unittest.main()
