import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.trend_report import router as trend_report_router
from app.core.security import get_current_user
from app.database.database import Base, get_db
from app.models.conversation import Conversation
from app.models.advertising_angle import AdvertisingAngle
from app.models.advertising_brief import AdvertisingBrief, CampaignMetricSnapshot
from app.models.campaign import Campaign
from app.models.message import Message
from app.models.trend_report import TrendReport, TrendReportEvidence
from app.models.user import User
from app.services.external_retrieval.evidence import Evidence
from app.services.external_retrieval.provider import SearchProviderResult, SearchProviderStatus
from app.schemas.campaign import CampaignCreate
from app.schemas.content_document import ContentDocumentCreate
from app.schemas.saved_content import SavedContentCreate
from app.schemas.trend_report import (
    TrendReportClaimCreate,
    TrendReportCreate,
    TrendReportEvidenceCreate,
)
from app.services.campaign_service import create_campaign_service
from app.services.content_document_service import create_document
from app.services.saved_content_service import save_content_service
from app.services.trend_report_service import (
    create_trend_report_service,
    delete_trend_report_service,
    get_trend_report_service,
    list_trend_reports_service,
)
from app.services.message_service import _persist_requested_retrieval_report


class TrendReportPersistenceTests(unittest.TestCase):
    fixed_now = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)

    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.Session = sessionmaker(bind=cls.engine)
        Base.metadata.create_all(cls.engine)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def setUp(self):
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        self.db = self.Session()
        self.owner = User(
            username="trend-owner",
            email="trend-owner@example.com",
            hashed_password="unused",
        )
        self.other = User(
            username="trend-other",
            email="trend-other@example.com",
            hashed_password="unused",
        )
        self.db.add_all([self.owner, self.other])
        self.db.commit()
        self.conversation = Conversation(user_id=self.owner.id, title="Trend research")
        self.db.add(self.conversation)
        self.db.commit()
        self.message = Message(
            conversation_id=self.conversation.id,
            role="user",
            content="Tìm trend mới nhất cho sản phẩm",
        )
        self.db.add(self.message)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def evidence(self, **overrides):
        values = {
            "evidence_id": "evidence-1",
            "title": "Official trend report",
            "source_url": "https://example.com/trend-report",
            "publisher": "Example Research",
            "retrieved_at": self.fixed_now,
            "published_at": datetime(2026, 10, 1, tzinfo=timezone.utc),
            "excerpt": "Demand increased in the monitored period.",
            "source_type": "official_report",
            "status": "unverified",
            "metadata": {"supports_claim_ids": ["trend-demand"]},
        }
        values.update(overrides)
        return TrendReportEvidenceCreate(**values)

    def report(self, **overrides):
        values = {
            "request_id": "request-1",
            "query": "latest demand trend",
            "summary": "Use this evidence-backed insight as a research brief.",
            "conversation_id": self.conversation.id,
            "source_message_id": self.message.id,
            "retrieved_at": self.fixed_now,
            "provider_status": "success",
            "evidences": [self.evidence()],
            "claims": [
                TrendReportClaimCreate(
                    claim_id="trend-demand",
                    claim_text="Demand increased in the monitored period.",
                    claim_type="evidence_backed",
                    evidence_ids=["evidence-1"],
                )
            ],
        }
        values.update(overrides)
        if values.get("summary") and not values.get("claims"):
            values["summary"] = None
        values["summary_claim_ids"] = [
            claim.claim_id for claim in values.get("claims", [])
        ] if values.get("summary") else []
        return TrendReportCreate(**values)

    def test_report_persists_loads_and_keeps_claim_source_mapping(self):
        response = create_trend_report_service(self.report(), self.db, self.owner)

        self.assertEqual(response.source_message_id, self.message.id)
        self.assertEqual(response.conversation_id, self.conversation.id)
        self.assertEqual(response.evidences[0].source_url, "https://example.com/trend-report")
        self.assertEqual(response.evidences[0].publisher, "Example Research")
        self.assertEqual(response.evidences[0].retrieved_at, self.fixed_now.replace(tzinfo=None))
        self.assertEqual(response.evidences[0].status, "unverified")
        self.assertEqual(response.claims[0].evidence[0].citation_id, "S1")

        stored = self.db.query(TrendReport).one()
        self.assertEqual(self.db.query(TrendReportEvidence).count(), 1)
        loaded = get_trend_report_service(stored.report_key, self.db, self.owner)
        self.assertEqual(loaded.claims[0].evidence[0].source_url, response.evidences[0].source_url)

    def test_missing_evidence_cannot_be_declared_source_backed(self):
        data = self.report(
            evidences=[],
            claims=[
                TrendReportClaimCreate(
                    claim_id="unsupported-stat",
                    claim_text="42% of users prefer this product.",
                    claim_type="evidence_backed",
                    evidence_ids=["missing"],
                )
            ],
        )
        with self.assertRaisesRegex(Exception, "evidence không thuộc report"):
            create_trend_report_service(data, self.db, self.owner)

    def test_provider_failure_report_is_explicit_and_has_no_fake_evidence(self):
        response = create_trend_report_service(
            TrendReportCreate(
                query="latest demand trend",
                conversation_id=self.conversation.id,
                source_message_id=self.message.id,
                retrieved_at=self.fixed_now,
                provider_status="timeout",
            ),
            self.db,
            self.owner,
        )

        self.assertEqual(response.provider_status, "timeout")
        self.assertIn("Không thể sử dụng nguồn dữ liệu xu hướng", response.caveat)
        self.assertIn("không dùng dữ liệu đã cũ như dữ liệu hiện tại", response.caveat)
        self.assertEqual(response.evidences, [])
        self.assertEqual(response.claims, [])

    def test_stale_evidence_is_stored_as_stale_not_current(self):
        response = create_trend_report_service(
            self.report(
                claims=[],
                evidences=[
                    self.evidence(
                        published_at=datetime(2020, 1, 1, tzinfo=timezone.utc)
                    )
                ],
            ),
            self.db,
            self.owner,
        )
        self.assertEqual(response.evidences[0].status, "stale")
        self.assertIn("stale", response.caveat)

    def test_requested_retrieval_is_snapshotted_with_message_link(self):
        provider_result = SearchProviderResult(
            status=SearchProviderStatus.SUCCESS,
            evidences=(
                Evidence(
                    evidence_id="retrieval-evidence",
                    title="Retrieved source",
                    source_url="https://example.com/retrieved",
                    publisher="Example",
                    retrieved_at=self.fixed_now,
                    excerpt="Retrieved excerpt.",
                    source_type="search_result",
                ),
            ),
        )
        report = _persist_requested_retrieval_report(
            retrieval_outcome=SimpleNamespace(
                was_requested=True,
                provider_result=provider_result,
            ),
            query="tìm trend mới nhất",
            db=self.db,
            current_user=self.owner,
            conversation_id=self.conversation.id,
            source_message_id=self.message.id,
        )
        self.assertEqual(report.source_message_id, self.message.id)
        self.assertEqual(report.evidences[0].source_url, "https://example.com/retrieved")

    def test_report_reference_survives_saved_content_document_and_campaign_handoff(self):
        response = create_trend_report_service(self.report(), self.db, self.owner)
        report_id = self.db.query(TrendReport).filter_by(report_key=response.report_id).one().id

        saved = save_content_service(
            SavedContentCreate(trend_report_id=report_id), self.db, self.owner
        )
        self.assertEqual(saved.trend_report_id, report_id)

        document = create_document(
            ContentDocumentCreate(source_trend_report_id=report_id),
            self.db,
            self.owner,
        )
        self.assertEqual(document["source_trend_report_id"], report_id)

        campaign = create_campaign_service(
            CampaignCreate(name="Trend campaign", trend_report_id=report_id),
            self.db,
            self.owner,
        )
        self.assertEqual(campaign.trend_report_id, report_id)

    def test_owner_soft_delete_hides_every_provider_outcome_and_preserves_references(self):
        success = create_trend_report_service(self.report(), self.db, self.owner)
        empty = create_trend_report_service(
            TrendReportCreate(query="empty trend", provider_status="empty"), self.db, self.owner
        )
        error = create_trend_report_service(
            TrendReportCreate(query="error trend", provider_status="error"), self.db, self.owner
        )
        success_record = self.db.query(TrendReport).filter_by(report_key=success.report_id).one()

        saved = save_content_service(
            SavedContentCreate(trend_report_id=success_record.id), self.db, self.owner
        )
        document = create_document(
            ContentDocumentCreate(source_trend_report_id=success_record.id), self.db, self.owner
        )
        campaign = create_campaign_service(
            CampaignCreate(name="Preserved campaign", trend_report_id=success_record.id),
            self.db,
            self.owner,
        )
        angle = AdvertisingAngle(
            owner_user_id=self.owner.id,
            trend_report_id=success_record.id,
            source_claim_key="trend-demand",
            trust_status="verified",
            trust_risk_level="low",
            trust_action="allow",
            title="Preserved angle",
            rationale="Evidence-backed.",
            wording="Use bounded wording.",
            source_key="preserved-angle",
        )
        self.db.add(angle)
        self.db.flush()
        brief = AdvertisingBrief(
            owner_user_id=self.owner.id,
            advertising_angle_id=angle.id,
            title="Preserved brief",
            core_message="Core message",
            copy_direction="Bounded copy",
            rationale="Evidence-backed.",
        )
        self.db.add(brief)
        self.db.flush()
        artifact_campaign = Campaign(
            user_id=self.owner.id,
            trend_report_id=success_record.id,
            advertising_brief_id=brief.id,
            name="Preserved artifact campaign",
        )
        self.db.add(artifact_campaign)
        self.db.flush()
        metric = CampaignMetricSnapshot(
            owner_user_id=self.owner.id,
            campaign_id=artifact_campaign.id,
            advertising_brief_id=brief.id,
            payload_json="{}",
        )
        self.db.add(metric)
        self.db.commit()

        for report_key in (success.report_id, empty.report_id, error.report_id):
            delete_trend_report_service(report_key, self.db, self.owner)

        self.assertEqual(list_trend_reports_service(self.db, self.owner), [])
        self.assertEqual(self.db.query(TrendReport).count(), 3)
        self.assertTrue(all(item.deleted_at is not None for item in self.db.query(TrendReport).all()))
        self.assertEqual(saved.trend_report_id, success_record.id)
        self.assertEqual(document["source_trend_report_id"], success_record.id)
        self.assertEqual(campaign.trend_report_id, success_record.id)
        self.assertEqual(self.db.query(AdvertisingAngle).filter_by(id=angle.id).one().trend_report_id, success_record.id)
        self.assertEqual(self.db.query(AdvertisingBrief).filter_by(id=brief.id).one().advertising_angle_id, angle.id)
        self.assertEqual(self.db.query(Campaign).filter_by(id=artifact_campaign.id).one().advertising_brief_id, brief.id)
        self.assertEqual(self.db.query(CampaignMetricSnapshot).filter_by(id=metric.id).one().campaign_id, artifact_campaign.id)

    def test_soft_delete_is_owner_scoped(self):
        response = create_trend_report_service(self.report(), self.db, self.owner)

        with self.assertRaises(HTTPException) as error:
            delete_trend_report_service(response.report_id, self.db, self.other)

        self.assertEqual(error.exception.status_code, 404)
        self.assertIsNone(
            self.db.query(TrendReport).filter_by(report_key=response.report_id).one().deleted_at
        )

    def test_summary_requires_explicit_structured_claim_contract(self):
        with self.assertRaisesRegex(ValueError, "summary_claim_ids"):
            TrendReportCreate(
                query="latest trend",
                summary="42% of users prefer this product.",
                evidences=[self.evidence()],
                claims=[
                    TrendReportClaimCreate(
                        claim_id="supported-stat",
                        claim_text="42% of users prefer this product.",
                        claim_type="evidence_backed",
                        evidence_ids=["evidence-1"],
                    )
                ],
            )

    def test_duplicate_evidence_is_collapsed_and_claim_maps_to_canonical_source(self):
        duplicate = self.evidence(
            evidence_id="evidence-duplicate",
            source_url="https://duplicate.example/trend-report",
        )
        response = create_trend_report_service(
            self.report(
                evidences=[self.evidence(), duplicate],
                claims=[
                    TrendReportClaimCreate(
                        claim_id="trend-demand",
                        claim_text="Demand increased in the monitored period.",
                        claim_type="evidence_backed",
                        evidence_ids=["evidence-duplicate"],
                    )
                ],
            ),
            self.db,
            self.owner,
        )

        self.assertEqual(len(response.evidences), 1)
        self.assertEqual(response.claims[0].evidence[0].evidence_id, "evidence-1")
        self.assertEqual(
            response.evidences[0].metadata["deduplicated_evidence_ids"],
            ["evidence-duplicate"],
        )
        self.assertIn("Đã loại", response.caveat)

    def test_conflicting_evidence_status_is_persisted_with_caveat(self):
        response = create_trend_report_service(
            self.report(
                summary=None,
                claims=[],
                evidences=[self.evidence(status="conflicting")],
            ),
            self.db,
            self.owner,
        )

        self.assertEqual(response.evidences[0].status, "conflicting")
        self.assertIn("conflicting", response.caveat)
    def test_provider_duplicate_evidence_is_collapsed_before_report_persistence(self):
        provider_result = SearchProviderResult(
            status=SearchProviderStatus.SUCCESS,
            evidences=(
                Evidence(
                    evidence_id="provider-primary",
                    title="Retrieved source",
                    source_url="https://example.com/retrieved",
                    publisher="Example",
                    retrieved_at=self.fixed_now,
                    excerpt="Same retrieved excerpt.",
                    source_type="search_result",
                ),
                Evidence(
                    evidence_id="provider-duplicate",
                    title="Mirror source",
                    source_url="https://mirror.example/retrieved",
                    publisher="Mirror",
                    retrieved_at=self.fixed_now,
                    excerpt="Same retrieved excerpt.",
                    source_type="search_result",
                ),
            ),
        )
        report = _persist_requested_retrieval_report(
            retrieval_outcome=SimpleNamespace(
                was_requested=True,
                provider_result=provider_result,
            ),
            query="latest trend",
            db=self.db,
            current_user=self.owner,
            conversation_id=self.conversation.id,
            source_message_id=self.message.id,
        )

        self.assertEqual(len(report.evidences), 1)
        self.assertEqual(
            report.evidences[0].metadata["deduplicated_evidence_ids"],
            ["provider-duplicate"],
        )


class TrendReportApiTests(unittest.TestCase):
    def test_report_endpoint_returns_source_fields(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Session = sessionmaker(bind=engine)
        Base.metadata.create_all(engine)
        db = Session()
        owner = User(username="api-owner", email="api-owner@example.com", hashed_password="unused")
        db.add(owner)
        db.commit()

        app = FastAPI()
        app.include_router(trend_report_router)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: owner
        client = TestClient(app)
        payload = {
            "query": "latest trend",
            "summary": "A source-backed report summary.",
            "summary_claim_ids": ["api-claim"],
            "provider_status": "success",
            "claims": [
                {
                    "claim_id": "api-claim",
                    "claim_text": "A bounded claim.",
                    "claim_type": "evidence_backed",
                    "evidence_ids": ["api-evidence"],
                }
            ],
            "evidences": [
                {
                    "evidence_id": "api-evidence",
                    "title": "Report",
                    "source_url": "https://example.com/api-report",
                    "publisher": "Example",
                    "retrieved_at": "2026-10-05T12:00:00Z",
                    "excerpt": "A bounded excerpt.",
                    "source_type": "search_result",
                    "status": "unverified",
                }
            ],
        }
        response = client.post("/trend-reports", json=payload)
        client.close()
        db.close()
        engine.dispose()

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["evidences"][0]["source_url"], "https://example.com/api-report")
        self.assertEqual(body["evidences"][0]["publisher"], "Example")
        self.assertEqual(body["evidences"][0]["status"], "unverified")
        self.assertIn("retrieved_at", body["evidences"][0])
