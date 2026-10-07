"""CP-5C: mock E2E tests through MessageService and the real internal pipeline."""

import types
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
from app.models.user import User
from app.schemas.message import AdBrief, MessageCreate, MessageUpdate
from app.services import ai_service
from app.services.external_retrieval.evidence import (
    Evidence,
    EvidenceSourceType,
    EvidenceVerificationStatus,
)
from app.services.external_retrieval.provider import (
    SearchProviderResult,
    SearchProviderStatus,
)
from app.services.external_retrieval.retrieval_service import ExternalRetrievalService
from app.services.message_service import (
    create_message_service,
    edit_message_stream_service,
    stream_message_service,
)


NOW = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)


class FakeProvider:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def search(self, query, *, limit=None):
        self.calls.append((query, limit))
        return self.result


class FakeGeminiModels:
    def __init__(self, chunks):
        self.chunks = tuple(chunks)
        self.requests = []

    def generate_content_stream(self, **kwargs):
        self.requests.append(kwargs)
        return [types.SimpleNamespace(text=chunk) for chunk in self.chunks]

    def generate_content(self, **kwargs):
        self.requests.append(kwargs)
        return types.SimpleNamespace(text="".join(self.chunks))


def evidence_result(*, metadata=None, status=EvidenceVerificationStatus.UNVERIFIED, provider_status=SearchProviderStatus.SUCCESS):
    evidences = ()
    if provider_status is SearchProviderStatus.SUCCESS:
        evidences = (
            Evidence(
                evidence_id="evidence-1",
                title="Synthetic product source",
                source_url="https://example.test/product",
                publisher="Synthetic publisher",
                published_at=None,
                retrieved_at=NOW,
                excerpt="Synthetic source excerpt.",
                source_type=EvidenceSourceType.SEARCH_RESULT,
                verification_status=status,
                metadata=metadata or {},
            ),
        )
    return SearchProviderResult(status=provider_status, evidences=evidences)


class MessageServiceMockE2ETests(unittest.TestCase):
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
            username="cp5c-owner",
            email="cp5c-owner@example.com",
            hashed_password="not-used",
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

    def tearDown(self):
        self.db.close()

    def conversation_id(self):
        conversation = Conversation(user_id=self.user.id, title="CP-5C")
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation.id

    def run_stream(self, content, *, provider_result, chunks, ad_brief=None, conversation_id=None):
        provider = FakeProvider(provider_result)
        models = FakeGeminiModels(chunks)
        conversation_id = conversation_id or self.conversation_id()
        with patch("app.services.message_service.external_retrieval_service", ExternalRetrievalService(provider)), patch.object(
            ai_service, "client", types.SimpleNamespace(models=models)
        ), patch.object(ai_service.learning_dataset_service, "log_generation"):
            output = "".join(
                stream_message_service(
                    message=MessageCreate(
                        conversation_id=conversation_id,
                        content=content,
                        prompt_type="facebook",
                        ad_brief=ad_brief,
                    ),
                    db=self.db,
                    current_user=self.user,
                )
            )
        return output, provider, models, conversation_id

    def test_normal_ad_does_not_call_provider_and_keeps_streaming(self):
        output, provider, models, _ = self.run_stream(
            "Viết quảng cáo Facebook cho sản phẩm này",
            provider_result=evidence_result(),
            chunks=("Bản quảng cáo ", "thông thường."),
        )

        self.assertEqual(provider.calls, [])
        self.assertEqual(output, "Bản quảng cáo thông thường.")
        self.assertEqual(len(models.requests), 1)

    def test_retrieval_evidence_product_trust_and_valid_citation_cross_message_service(self):
        output, provider, models, _ = self.run_stream(
            "Tìm xu hướng mới nhất và dẫn nguồn để viết quảng cáo",
            provider_result=evidence_result(
                metadata={"supports_claim_ids": ["product:description"]}
            ),
            chunks=("Pin dùng 60 ngày [S1].",),
            ad_brief=AdBrief(
                product_name="Demo device",
                description="Pin dùng 60 ngày",
                platform="facebook",
            ),
        )

        self.assertEqual(len(provider.calls), 1)
        self.assertIn("Pin dùng 60 ngày", output)
        self.assertIn("[S1]", output)
        self.assertIn("evidence_supported", "".join(
            getattr(part, "text", "")
            for part in models.requests[0]["contents"][-1].parts
        ))

    def test_unverified_claim_is_not_promoted_and_is_softened(self):
        output, provider, _, _ = self.run_stream(
            "Tìm xu hướng mới nhất của sản phẩm",
            provider_result=evidence_result(metadata={}),
            chunks=("Pin dùng 60 ngày [S1].",),
            ad_brief=AdBrief(
                product_name="Demo device",
                description="Pin dùng 60 ngày",
                platform="facebook",
            ),
        )

        self.assertEqual(len(provider.calls), 1)
        self.assertNotIn("Pin dùng 60 ngày", output)
        self.assertIn("cần được kiểm tra thêm", output)

    def test_contradicted_high_risk_claim_is_blocked_before_stream_yield(self):
        claim = "Chữa khỏi bệnh đau cổ tay"
        output, provider, _, conversation_id = self.run_stream(
            "Kiểm chứng công dụng sản phẩm và dẫn nguồn",
            provider_result=evidence_result(
                metadata={
                    "contradicts_claim_ids": ["product:description"],
                    "verification_basis": "synthetic manual comparison",
                },
                status=EvidenceVerificationStatus.PARTIAL,
            ),
            chunks=("Mở đầu ", f"{claim} [S1]."),
            ad_brief=AdBrief(
                product_name="Demo treatment",
                description=claim,
                platform="facebook",
            ),
        )

        self.assertEqual(len(provider.calls), 1)
        self.assertNotIn(claim, output)
        self.assertIn("[ADGEN_STREAM_ERROR]", output)
        self.assertEqual(
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id, Message.role == "assistant")
            .count(),
            0,
        )

    def test_unknown_citation_is_not_released(self):
        output, provider, _, _ = self.run_stream(
            "Tìm xu hướng mới nhất và dẫn nguồn",
            provider_result=evidence_result(
                metadata={"supports_claim_ids": ["product:description"]}
            ),
            chunks=("Nội dung có nguồn [S9].",),
            ad_brief=AdBrief(
                product_name="Demo device",
                description="Thiết kế nhỏ gọn",
                platform="facebook",
            ),
        )

        self.assertEqual(len(provider.calls), 1)
        self.assertNotIn("[S9]", output)
        self.assertIn("[ADGEN_STREAM_ERROR]", output)

    def test_provider_error_is_distinct_and_does_not_look_verified(self):
        output, provider, models, _ = self.run_stream(
            "Research the latest product trend with sources",
            provider_result=evidence_result(provider_status=SearchProviderStatus.TIMEOUT),
            chunks=("fabricated current trend",),
            ad_brief=AdBrief(
                product_name="Demo device",
                description="Pin dÃ¹ng 60 ngÃ y",
                platform="facebook",
            ),
        )

        self.assertEqual(len(provider.calls), 1)
        self.assertIn("status: timeout", output)
        self.assertIn("source-backed conclusions", output)
        self.assertNotIn("fabricated current trend", output)
        self.assertEqual(models.requests, [])
    def test_edit_regenerate_repeats_retrieval_product_trust_and_enforcement(self):
        provider = FakeProvider(
            evidence_result(metadata={"supports_claim_ids": ["product:description"]})
        )
        models = FakeGeminiModels(("Pin dùng 60 ngày [S1].",))
        conversation_id = self.conversation_id()
        brief = AdBrief(
            product_name="Demo device",
            description="Pin dùng 60 ngày",
            platform="facebook",
        )
        retrieval_service = ExternalRetrievalService(provider)
        with patch("app.services.message_service.external_retrieval_service", retrieval_service), patch.object(
            ai_service, "client", types.SimpleNamespace(models=models)
        ), patch.object(ai_service.learning_dataset_service, "log_generation"):
            first = stream_message_service(
                MessageCreate(
                    conversation_id=conversation_id,
                    content="Tìm xu hướng mới nhất và dẫn nguồn",
                    prompt_type="facebook",
                    ad_brief=brief,
                ),
                self.db,
                self.user,
            )
            self.assertIn("Pin dùng 60 ngày", "".join(first))
            user_message = (
                self.db.query(Message)
                .filter(Message.conversation_id == conversation_id, Message.role == "user")
                .first()
            )
            edited = edit_message_stream_service(
                user_message.id,
                MessageUpdate(content="Tìm xu hướng mới nhất để viết lại quảng cáo"),
                self.db,
                self.user,
            )
            self.assertIn("Pin dùng 60 ngày", "".join(edited))

        self.assertEqual(len(provider.calls), 2)
        self.assertEqual(len(models.requests), 2)


    def test_create_uses_deterministic_fallback_without_model_call(self):
        provider = FakeProvider(
            evidence_result(provider_status=SearchProviderStatus.QUOTA_EXCEEDED)
        )
        models = FakeGeminiModels(("fabricated trend statistic",))
        with patch(
            "app.services.message_service.external_retrieval_service",
            ExternalRetrievalService(provider),
        ), patch.object(
            ai_service, "client", types.SimpleNamespace(models=models)
        ), patch.object(ai_service.learning_dataset_service, "log_generation"):
            result = create_message_service(
                MessageCreate(
                    conversation_id=self.conversation_id(),
                    content="Research the latest market trend with sources",
                    prompt_type="facebook",
                ),
                self.db,
                self.user,
            )

        self.assertEqual(len(provider.calls), 1)
        self.assertIn("status: quota_exceeded", result["assistant_message"].content)
        self.assertNotIn("fabricated trend statistic", result["assistant_message"].content)
        self.assertEqual(models.requests, [])

    def test_edit_regenerate_uses_deterministic_fallback_without_model_call(self):
        conversation_id = self.conversation_id()
        user_message = Message(
            conversation_id=conversation_id,
            role="user",
            content="Initial ad request",
            prompt_type="facebook",
        )
        self.db.add(user_message)
        self.db.commit()
        self.db.refresh(user_message)

        provider = FakeProvider(
            evidence_result(provider_status=SearchProviderStatus.TIMEOUT)
        )
        models = FakeGeminiModels(("fabricated current trend",))
        with patch(
            "app.services.message_service.external_retrieval_service",
            ExternalRetrievalService(provider),
        ), patch.object(
            ai_service, "client", types.SimpleNamespace(models=models)
        ), patch.object(ai_service.learning_dataset_service, "log_generation"):
            output = "".join(
                edit_message_stream_service(
                    user_message.id,
                    MessageUpdate(content="Research current market trend with sources"),
                    self.db,
                    self.user,
                )
            )

        self.assertEqual(len(provider.calls), 1)
        self.assertIn("status: timeout", output)
        self.assertNotIn("fabricated current trend", output)
        self.assertEqual(models.requests, [])
        self.assertEqual(
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id, Message.role == "assistant")
            .count(),
            1,
        )

if __name__ == "__main__":
    unittest.main()
