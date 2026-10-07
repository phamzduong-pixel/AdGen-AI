import json
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.trend_report import (
    get_multi_platform_retrieval_service,
    router as trend_report_router,
)
from app.core.security import get_current_user
from app.database.database import Base, get_db
from app.models.trend_report import TrendReport, TrendReportEvidence
from app.models.user import User
from app.services.external_retrieval.evidence import Evidence, EvidenceSourceType
from app.services.external_retrieval.multi_platform import MultiPlatformRetrievalService
from app.services.external_retrieval.provider import SearchProviderResult, SearchProviderStatus


NOW = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)


class FakeCollector:
    def __init__(self, platform, result):
        self.platform = platform
        self.result = result
        self.calls = []

    def collect(self, query):
        self.calls.append(query)
        return self.result


def make_evidence(
    evidence_id,
    source_url,
    excerpt,
    *,
    published_at=NOW,
    metadata=None,
):
    return Evidence(
        evidence_id=evidence_id,
        title=evidence_id,
        source_url=source_url,
        publisher="Fake Publisher",
        retrieved_at=NOW,
        published_at=published_at,
        excerpt=excerpt,
        source_type=EvidenceSourceType.PLATFORM_ANALYTICS,
        metadata=metadata or {},
    )


def make_app(db, owner, retrieval_service=None):
    app = FastAPI()
    app.include_router(trend_report_router)
    app.dependency_overrides[get_db] = lambda: db
    if owner is not None:
        app.dependency_overrides[get_current_user] = lambda: owner
    if retrieval_service is not None:
        app.dependency_overrides[get_multi_platform_retrieval_service] = (
            lambda: retrieval_service
        )
    return app


def test_multi_platform_retrieval_api_is_authenticated_and_end_to_end():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = Session()
    owner = User(
        username="stage2-api-owner",
        email="stage2-api-owner@example.com",
        hashed_password="unused",
        email_verified=True,
    )
    db.add(owner)
    db.commit()

    fresh = make_evidence(
        "youtube-fresh",
        "https://youtube.example/fresh",
        "same signal",
        metadata={"provider": "fake-youtube"},
    )
    duplicate = make_evidence(
        "youtube-duplicate",
        "https://youtube.example/duplicate",
        "same signal",
        metadata={"provider": "fake-youtube"},
    )
    conflict_left = make_evidence(
        "conflict-left",
        "https://youtube.example/conflict",
        "left signal",
        metadata={"conflicts_with": ["conflict-right"]},
    )
    conflict_right = make_evidence(
        "conflict-right",
        "https://instagram.example/conflict",
        "right signal",
    )
    stale = make_evidence(
        "instagram-stale",
        "https://instagram.example/stale",
        "old signal",
        published_at=NOW - timedelta(days=31),
    )
    youtube = FakeCollector(
        "youtube",
        SearchProviderResult(
            SearchProviderStatus.SUCCESS,
            evidences=(fresh, duplicate, conflict_left),
        ),
    )
    instagram = FakeCollector(
        "instagram",
        SearchProviderResult(
            SearchProviderStatus.SUCCESS,
            evidences=(conflict_right, stale),
        ),
    )
    meta = FakeCollector(
        "meta",
        SearchProviderResult(
            SearchProviderStatus.TIMEOUT,
            message="fake timeout",
        ),
    )
    retrieval_service = MultiPlatformRetrievalService(
        [youtube, instagram, meta],
        clock=lambda: NOW,
    )
    app = make_app(db, owner, retrieval_service)
    client = TestClient(app)

    try:
        unauthenticated = app
        unauthenticated.dependency_overrides.pop(get_current_user)
        response = client.post("/trend-reports/retrieve", json={"query": "running shoes"})
        assert response.status_code == 401
        app.dependency_overrides[get_current_user] = lambda: owner

        response = client.post(
            "/trend-reports/retrieve",
            json={"query": "running shoes", "request_id": "stage2-api-request"},
        )
        assert response.status_code == 201, response.text
        body = response.json()

        assert youtube.calls == ["running shoes"]
        assert instagram.calls == ["running shoes"]
        assert meta.calls == ["running shoes"]
        assert body["provider_status"] == "partial"
        assert body["summary"] is None
        assert body["claims"] == []

        statuses = {item["source"]: item for item in body["source_statuses"]}
        assert statuses["youtube"]["status"] == "success"
        assert statuses["instagram"]["status"] == "success"
        assert statuses["meta"]["status"] == "timeout"
        assert statuses["meta"]["message"] == "fake timeout"
        assert statuses["youtube"]["deduplicated_evidence_ids"] == [
            "youtube-duplicate"
        ]

        evidence = {item["evidence_id"]: item for item in body["evidences"]}
        assert "youtube-duplicate" not in evidence
        assert evidence["instagram-stale"]["status"] == "stale"
        assert evidence["conflict-left"]["status"] == "conflicting"
        assert evidence["conflict-left"]["metadata"]["conflicts_with"] == [
            "conflict-right"
        ]
        assert evidence["conflict-left"]["source_url"].startswith("https://")
        assert evidence["conflict-left"]["publisher"] == "Fake Publisher"
        assert evidence["conflict-left"]["retrieved_at"]
        assert evidence["conflict-left"]["excerpt"] == "left signal"

        stored = db.query(TrendReport).one()
        assert json.loads(stored.source_statuses_json) == body["source_statuses"]
        assert db.query(TrendReportEvidence).count() == 4

        loaded = client.get(f"/trend-reports/{body['report_id']}")
        assert loaded.status_code == 200
        assert loaded.json()["source_statuses"] == body["source_statuses"]
        assert loaded.json()["evidences"][0]["source_url"].startswith("https://")
    finally:
        client.close()
        db.close()
        engine.dispose()
