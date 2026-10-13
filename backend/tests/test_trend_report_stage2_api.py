import json
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
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
from app.services.external_retrieval.rss_feed import RSSFeedCollector
from app.services.external_retrieval.rss_sources import TREND_RADAR_RSS_FEEDS


NOW = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)


def parse_api_datetime(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


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
    publisher="Fake Publisher",
):
    return Evidence(
        evidence_id=evidence_id,
        title=evidence_id,
        source_url=source_url,
        publisher=publisher,
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


def make_test_context(retrieval_service, username):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = Session()
    owner = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password="unused",
        email_verified=True,
    )
    db.add(owner)
    db.commit()
    client = TestClient(make_app(db, owner, retrieval_service))
    return engine, db, client


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
        publisher="Second Publisher",
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
        assert body["summary"]
        assert body["article_count"] == 4
        assert body["publisher_count"] == 2
        assert body["topic_clusters"] == []
        assert {claim["claim_type"] for claim in body["claims"]} == {
            "report_statistic",
            "analysis_status",
        }
        assert set(body["summary_claim_ids"]) == {
            claim["claim_id"] for claim in body["claims"]
        }
        assert "không đo lượt xem" in body["caveat"]

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
        assert evidence["conflict-right"]["status"] == "conflicting"
        assert evidence["conflict-left"]["metadata"]["conflicts_with"] == [
            "conflict-right"
        ]
        assert evidence["conflict-left"]["source_url"].startswith("https://")
        assert evidence["conflict-left"]["publisher"] == "Fake Publisher"
        assert evidence["conflict-left"]["retrieved_at"]
        assert evidence["conflict-left"]["excerpt"] == "left signal"
        assert evidence["youtube-fresh"]["metadata"]["source_publishers"] == [
            "Fake Publisher",
            "Second Publisher",
        ]

        stored = db.query(TrendReport).one()
        assert json.loads(stored.source_statuses_json) == body["source_statuses"]
        assert db.query(TrendReportEvidence).count() == 4

        loaded = client.get(f"/trend-reports/{body['report_id']}")
        assert loaded.status_code == 200
        assert loaded.json()["source_statuses"] == body["source_statuses"]
        assert loaded.json()["evidences"][0]["source_url"].startswith("https://")
        assert loaded.json()["summary"] == body["summary"]
        assert loaded.json()["article_count"] == body["article_count"]
        assert loaded.json()["publisher_count"] == body["publisher_count"]
        assert loaded.json()["topic_clusters"] == body["topic_clusters"]
        assert loaded.json()["claims"] == body["claims"]
        trust = client.get(f"/trend-reports/{body['report_id']}/trust")
        assert trust.status_code == 200
        assert trust.json()["claims"] == []
    finally:
        client.close()
        db.close()
        engine.dispose()


def test_default_trend_report_collector_uses_allowlisted_rss_without_live_request():
    retrieval_service = get_multi_platform_retrieval_service()

    assert [collector.feed.feed_id for collector in retrieval_service.collectors] == [
        "thanhnien-consumer-smart",
        "thanhnien-food",
    ]
    assert all(collector.__class__.__name__ == "RSSFeedCollector" for collector in retrieval_service.collectors)


def test_allowlisted_rss_fixture_is_persisted_through_trend_report_api():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    db = Session()
    owner = User(
        username="rss-stage1-owner",
        email="rss-stage1-owner@example.com",
        hashed_password="unused",
        email_verified=True,
    )
    db.add(owner)
    db.commit()
    feed = TREND_RADAR_RSS_FEEDS[0]
    rss_fixture = """<?xml version='1.0' encoding='utf-8'?>
    <rss version='2.0'><channel><item>
      <title>Đồ ăn vặt được người tiêu dùng quan tâm</title>
      <link>https://thanhnien.vn/doi-song/do-an-vat.html</link>
      <description>Thị trường đồ ăn vặt và sản phẩm mới.</description>
      <pubDate>Sun, 04 Oct 2026 10:30:00 +0700</pubDate>
    </item></channel></rss>""".encode("utf-8")
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, content=rss_fixture)

    collector = RSSFeedCollector(
        feed,
        transport=httpx.MockTransport(handler),
        resolver=lambda host, port: ["8.8.8.8"],
        clock=lambda: NOW,
    )
    service = MultiPlatformRetrievalService([collector], clock=lambda: NOW)
    app = make_app(db, owner, service)
    client = TestClient(app)

    try:
        response = client.post(
            "/trend-reports/retrieve",
            json={"query": "đồ ăn vặt", "max_age_days": 0},
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert len(requests) == 1
        assert str(requests[0].url) == feed.url
        assert body["provider_status"] == "success"
        report_collected_at = parse_api_datetime(body["retrieved_at"])
        assert report_collected_at == NOW
        assert parse_api_datetime(body["generated_at"]) >= report_collected_at
        assert body["summary"]
        assert body["article_count"] == 1
        assert body["publisher_count"] == 1
        assert body["newest_article_at"] == "2026-10-04T03:30:00Z"
        assert body["topic_clusters"] == []
        assert "không đo lượt xem" in body["caveat"]
        assert body["source_statuses"][0]["evidence_count"] == 1
        assert body["source_statuses"][0]["result_state"] == "success"
        assert body["source_statuses"][0]["entries_checked"] == 1
        assert body["source_statuses"][0]["valid_entries"] == 1
        assert body["source_statuses"][0]["matched_entries"] == 1
        assert body["evidences"][0]["source_type"] == "rss_feed"
        evidence = body["evidences"][0]
        assert evidence["status"] == "stale"
        assert parse_api_datetime(evidence["retrieved_at"]) == NOW
        assert parse_api_datetime(evidence["published_at"]) < NOW
        assert body["source_statuses"][0]["collected_at"] == NOW.isoformat()
        assert body["source_statuses"][0]["from_cache"] is False
        corpus_claim = next(
            claim for claim in body["claims"] if claim["claim_id"] == "analysis:corpus:v1"
        )
        assert corpus_claim["evidence"][0]["evidence_id"] == body["evidences"][0]["evidence_id"]
        assert body["evidences"][0]["publisher"] == "Báo Thanh Niên"
        assert db.query(TrendReportEvidence).count() == 1
        assert json.loads(db.query(TrendReport).one().source_statuses_json)[0]["status"] == "success"
    finally:
        client.close()
        db.close()
        engine.dispose()


def test_empty_source_is_reported_as_empty_without_fabricated_evidence():
    collector = FakeCollector(
        "public-rss",
        SearchProviderResult(SearchProviderStatus.EMPTY),
    )
    service = MultiPlatformRetrievalService([collector], clock=lambda: NOW)
    engine, db, client = make_test_context(service, "empty-trend-owner")

    try:
        response = client.post("/trend-reports/retrieve", json={"query": "empty topic"})
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["provider_status"] == "empty"
        assert body["article_count"] == 0
        assert body["evidences"] == []
        assert body["source_statuses"][0]["status"] == "empty"
        assert body["source_statuses"][0]["result_state"] == "unknown"
        assert "entries_checked" not in body["source_statuses"][0]
        assert body["source_statuses"][0]["evidence_count"] == 0
        assert body["source_statuses"][0]["collected_at"] == NOW.isoformat()
        assert body["summary"]
        assert "feed RSS" in body["caveat"]
        assert collector.calls == ["empty topic"]
    finally:
        client.close()
        db.close()
        engine.dispose()


def test_cache_is_marked_and_fresh_failure_does_not_replace_history():
    clock_value = [NOW]
    evidence = make_evidence(
        "history-evidence",
        "https://publisher.example/history",
        "a real prior article",
        published_at=NOW - timedelta(days=1),
    )
    collector = FakeCollector(
        "public-rss",
        SearchProviderResult(SearchProviderStatus.SUCCESS, (evidence,)),
    )
    second_collector = FakeCollector(
        "second-rss",
        SearchProviderResult(SearchProviderStatus.EMPTY),
    )
    service = MultiPlatformRetrievalService(
        [collector, second_collector],
        clock=lambda: clock_value[0],
    )
    engine, db, client = make_test_context(service, "history-trend-owner")

    try:
        first = client.post(
            "/trend-reports/retrieve",
            json={"query": "history topic", "refresh": True},
        )
        assert first.status_code == 201, first.text
        first_body = first.json()
        assert first_body["provider_status"] == "success"
        assert first_body["article_count"] == 1
        assert first_body["article_count"] == len(first_body["evidences"])
        assert first_body["summary_claim_ids"] == [
            claim["claim_id"] for claim in first_body["claims"]
        ]
        corpus_claim = next(
            claim for claim in first_body["claims"]
            if claim["claim_id"] == "analysis:corpus:v1"
        )
        assert [item["evidence_id"] for item in corpus_claim["evidence"]] == [
            "history-evidence"
        ]
        assert first_body["source_statuses"][0]["evidence_count"] == 1
        assert first_body["source_statuses"][1]["evidence_count"] == 0
        assert parse_api_datetime(first_body["evidences"][0]["published_at"]) < parse_api_datetime(
            first_body["evidences"][0]["retrieved_at"]
        )
        first_retrieved_at = parse_api_datetime(first_body["retrieved_at"])
        assert first_retrieved_at == NOW

        clock_value[0] = NOW + timedelta(hours=1)
        cached = client.post(
            "/trend-reports/retrieve",
            json={"query": "history topic"},
        )
        assert cached.status_code == 201, cached.text
        cached_body = cached.json()
        assert cached_body["provider_status"] == "success"
        assert parse_api_datetime(cached_body["retrieved_at"]) == first_retrieved_at
        assert cached_body["source_statuses"][0]["from_cache"] is True
        assert cached_body["source_statuses"][0]["original_collected_at"] == NOW.isoformat()
        assert cached_body["source_statuses"][1]["from_cache"] is True
        assert "không phải lần thu thập mới" in cached_body["summary"]
        assert collector.calls == ["history topic"]
        assert second_collector.calls == ["history topic"]

        collector.result = SearchProviderResult(
            SearchProviderStatus.TIMEOUT,
            message="fixture timeout",
        )
        second_collector.result = SearchProviderResult(
            SearchProviderStatus.NETWORK_ERROR,
            message="fixture network error",
        )
        clock_value[0] = NOW + timedelta(hours=2)
        failed = client.post(
            "/trend-reports/retrieve",
            json={"query": "history topic", "refresh": True},
        )
        assert failed.status_code == 201, failed.text
        failed_body = failed.json()
        assert failed_body["provider_status"] == "failed"
        assert failed_body["article_count"] == 0
        assert failed_body["evidences"] == []
        assert [item["status"] for item in failed_body["source_statuses"]] == [
            "timeout",
            "network_error",
        ]
        assert parse_api_datetime(failed_body["retrieved_at"]) == clock_value[0]
        assert "timeout" in failed_body["summary"]
        assert "network_error" in failed_body["summary"]
        assert collector.calls == ["history topic", "history topic"]
        assert second_collector.calls == ["history topic", "history topic"]

        loaded_first = client.get(f"/trend-reports/{first_body['report_id']}")
        loaded_cached = client.get(f"/trend-reports/{cached_body['report_id']}")
        loaded_failed = client.get(f"/trend-reports/{failed_body['report_id']}")
        assert loaded_first.status_code == 200
        assert loaded_cached.status_code == 200
        assert loaded_failed.status_code == 200
        assert loaded_first.json()["article_count"] == 1
        assert loaded_first.json()["evidences"][0]["evidence_id"] == "history-evidence"
        assert loaded_first.json()["retrieved_at"] == first_body["retrieved_at"]
        assert loaded_cached.json()["provider_status"] == "success"
        assert loaded_cached.json()["retrieved_at"] == cached_body["retrieved_at"]
        assert loaded_failed.json()["article_count"] == 0
        assert loaded_failed.json()["evidences"] == []
        assert loaded_failed.json()["retrieved_at"] == failed_body["retrieved_at"]
        history = client.get("/trend-reports")
        assert history.status_code == 200
        assert {item["report_id"] for item in history.json()} == {
            first_body["report_id"],
            cached_body["report_id"],
            failed_body["report_id"],
        }
    finally:
        client.close()
        db.close()
        engine.dispose()


def test_cached_article_is_rechecked_against_current_freshness_threshold():
    clock_value = [NOW]
    evidence = make_evidence(
        "aging-evidence",
        "https://publisher.example/aging",
        "an article that will age past the threshold",
        published_at=NOW - timedelta(days=29),
    )
    collector = FakeCollector(
        "public-rss",
        SearchProviderResult(SearchProviderStatus.SUCCESS, (evidence,)),
    )
    service = MultiPlatformRetrievalService([collector], clock=lambda: clock_value[0])

    first = service.retrieve("aging topic", max_age_days=30)
    assert first.evidences[0].verification_status.value == "unverified"
    assert first.sources[0].collected_at == NOW

    clock_value[0] = NOW + timedelta(days=2)
    cached = service.retrieve("aging topic", max_age_days=30)

    assert cached.from_cache is True
    assert cached.evidences[0].verification_status.value == "stale"
    assert cached.sources[0].collected_at == NOW
    assert collector.calls == ["aging topic"]


def test_rss_empty_reasons_are_persisted_and_read_back():
    documents = (
        (b"<rss><channel /></rss>", "no_valid_entries", 0),
        (
            b"<rss><channel><item><title>Unrelated article</title>"
            b"<link>https://thanhnien.vn/unrelated.html</link></item></channel></rss>",
            "no_topic_matches", 1,
        ),
    )
    for index, (document, state, valid_count) in enumerate(documents):
        collector = RSSFeedCollector(
            TREND_RADAR_RSS_FEEDS[0],
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, content=document)
            ),
            resolver=lambda host, port: ["8.8.8.8"],
            clock=lambda: NOW,
        )
        service = MultiPlatformRetrievalService([collector], clock=lambda: NOW)
        engine, db, client = make_test_context(service, f"rss-empty-{index}")
        try:
            response = client.post("/trend-reports/retrieve", json={"query": "snack"})
            assert response.status_code == 201, response.text
            body = response.json()
            source = body["source_statuses"][0]
            assert body["provider_status"] == "empty"
            assert body["evidences"] == []
            assert source["status"] == "empty"
            assert source["result_state"] == state
            assert source["valid_entries"] == valid_count
            assert source["matched_entries"] == 0
            assert source["evidence_count"] == 0
            saved = db.query(TrendReport).one()
            assert json.loads(saved.source_statuses_json) == body["source_statuses"]
            read_back = client.get(f"/trend-reports/{body['report_id']}")
            assert read_back.status_code == 200
            assert read_back.json()["source_statuses"] == body["source_statuses"]
        finally:
            client.close()
            db.close()
            engine.dispose()


def test_partial_result_retains_evidence_and_source_specific_error():
    evidence = make_evidence(
        "existing-id", "https://publisher.example/snack", "snack product article",
    )
    service = MultiPlatformRetrievalService(
        [
            FakeCollector(
                "working-rss",
                SearchProviderResult(
                    SearchProviderStatus.SUCCESS, (evidence,),
                    metadata={"entries_checked": 2, "valid_entries": 2, "matched_entries": 1},
                ),
            ),
            FakeCollector(
                "failed-rss",
                SearchProviderResult(SearchProviderStatus.TIMEOUT, message="fixture timeout"),
            ),
        ],
        clock=lambda: NOW,
    )
    engine, db, client = make_test_context(service, "rss-partial-owner")
    try:
        response = client.post("/trend-reports/retrieve", json={"query": "snack"})
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["provider_status"] == "partial"
        assert body["article_count"] == 1
        assert body["evidences"][0]["evidence_id"] == "existing-id"
        assert {"report_id", "summary", "claims", "evidences", "source_statuses", "retrieved_at"} <= body.keys()
        statuses = {item["platform"]: item for item in body["source_statuses"]}
        assert statuses["working-rss"]["matched_entries"] == 1
        assert statuses["failed-rss"]["status"] == "timeout"
        assert statuses["failed-rss"]["result_state"] == "timeout"
        assert "entries_checked" not in statuses["failed-rss"]
        assert client.get(f"/trend-reports/{body['report_id']}").json()["source_statuses"] == body["source_statuses"]
    finally:
        client.close()
        db.close()
        engine.dispose()


def test_empty_source_and_error_is_partial_without_inventing_articles():
    service = MultiPlatformRetrievalService(
        [
            FakeCollector("empty-rss", SearchProviderResult(SearchProviderStatus.EMPTY)),
            FakeCollector("bad-rss", SearchProviderResult(SearchProviderStatus.INVALID_RESPONSE)),
        ],
        clock=lambda: NOW,
    )
    engine, db, client = make_test_context(service, "rss-empty-partial-owner")
    try:
        response = client.post("/trend-reports/retrieve", json={"query": "snack"})
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["provider_status"] == "partial"
        assert body["evidences"] == []
        assert body["source_statuses"][0]["result_state"] == "unknown"
        assert body["source_statuses"][1]["status"] == "invalid_response"
    finally:
        client.close()
        db.close()
        engine.dispose()


def test_historical_source_status_without_new_metadata_remains_readable():
    service = MultiPlatformRetrievalService(
        [FakeCollector("old-rss", SearchProviderResult(SearchProviderStatus.EMPTY))],
        clock=lambda: NOW,
    )
    engine, db, client = make_test_context(service, "rss-old-report-owner")
    try:
        created = client.post("/trend-reports/retrieve", json={"query": "snack"})
        assert created.status_code == 201, created.text
        report = db.query(TrendReport).one()
        legacy = [{
            "source": "old-rss", "platform": "old-rss", "status": "empty",
            "message": None, "evidence_count": 0, "from_cache": False,
        }]
        report.source_statuses_json = json.dumps(legacy)
        db.commit()
        loaded = client.get(f"/trend-reports/{created.json()['report_id']}")
        assert loaded.status_code == 200
        assert loaded.json()["source_statuses"] == legacy
        assert loaded.json()["provider_status"] == "empty"
    finally:
        client.close()
        db.close()
        engine.dispose()
