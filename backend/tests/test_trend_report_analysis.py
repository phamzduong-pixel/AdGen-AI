from dataclasses import replace
from datetime import datetime, timedelta, timezone

from app.services.external_retrieval.evidence import Evidence, EvidenceSourceType
from app.services.trend_report_analysis import analyze_trend_report


NOW = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)


def article(
    evidence_id,
    *,
    title="Đồ ăn vặt được quan tâm",
    excerpt="Thị trường đồ ăn vặt có sản phẩm mới.",
    publisher="Báo Thanh Niên",
    published_at=NOW,
    source_url=None,
    feed_id=None,
    status="unverified",
):
    metadata = {"publisher_name": publisher}
    if feed_id:
        metadata["feed_id"] = feed_id
    return Evidence(
        evidence_id=evidence_id,
        title=title,
        source_url=source_url or f"https://{evidence_id}.example/article",
        publisher=publisher,
        retrieved_at=NOW,
        published_at=published_at,
        excerpt=excerpt,
        source_type=EvidenceSourceType.RSS_FEED,
        verification_status=status,
        metadata=metadata,
    )


def test_repeated_topics_are_deterministic_and_supported_by_two_publishers():
    records = [
        article(
            "tn-1",
            feed_id="thanhnien-consumer-smart",
            title="Đồ ăn vặt được quan tâm trong mùa hè",
            excerpt="Thị trường đồ ăn vặt có sản phẩm mới.",
        ),
        article(
            "tn-2",
            feed_id="thanhnien-food",
            title="Đồ ăn vặt tiếp tục được chú ý",
            excerpt="Nhiều sản phẩm đồ ăn vặt xuất hiện.",
            published_at=NOW - timedelta(hours=1),
        ),
        article(
            "publisher-2",
            publisher="Báo Mới",
            title="Đồ ăn vặt được giới thiệu tại hội chợ",
            excerpt="Một số sản phẩm đồ ăn vặt được trưng bày.",
            published_at=NOW - timedelta(hours=2),
        ),
    ]
    statuses = [{"source": "rss", "status": "success"}]

    result = analyze_trend_report(records, statuses)
    repeated = analyze_trend_report(records, statuses)

    assert result.article_count == 3
    assert result.publisher_count == 2
    assert result.newest_article_at == NOW
    assert result.summary == repeated.summary
    assert result.topic_clusters == repeated.topic_clusters
    cluster = next(item for item in result.topic_clusters if "ăn vặt" in item.phrase)
    assert cluster.article_count == 3
    assert cluster.publisher_count == 2
    assert set(cluster.evidence_ids) == {"tn-1", "tn-2", "publisher-2"}


def test_duplicate_url_and_duplicate_content_are_collapsed_and_publishers_preserved():
    records = [
        article("a", title="Sản phẩm đỏ", excerpt="Thông tin sản phẩm đỏ.", source_url="https://site.example/a"),
        article("a-url-copy", title="Tiêu đề được cập nhật", excerpt="Nội dung khác.", publisher="Báo X", source_url="https://site.example/a"),
        article("b", title="Sản phẩm xanh", excerpt="Thông tin sản phẩm xanh.", publisher="Báo Y", source_url="https://site.example/b"),
        article("b-content-copy", title="Sản phẩm xanh", excerpt="Thông tin sản phẩm xanh.", publisher="Báo Z", source_url="https://other.example/b"),
    ]

    result = analyze_trend_report(records, [{"source": "rss", "status": "success"}])

    assert result.article_count == 2
    assert result.publisher_count == 4
    assert result.duplicate_ids == {"a-url-copy": "a", "b-content-copy": "b"}
    assert result.evidences[0].metadata["source_publishers"] == ["Báo Thanh Niên", "Báo X"]
    assert result.evidences[1].metadata["source_publishers"] == ["Báo Y", "Báo Z"]


def test_missing_title_or_publisher_is_discarded_but_missing_publish_time_is_safe():
    records = [
        article("no-published-time", published_at=None),
        article("no-title", title="  "),
        article("no-publisher", publisher=""),
        replace(article("no-retrieved-time"), retrieved_at=None),
    ]

    result = analyze_trend_report(records, [{"source": "rss", "status": "success"}])

    assert result.article_count == 1
    assert result.publisher_count == 1
    assert result.newest_article_at is None
    assert result.topic_clusters == ()
    assert "1 bài" in result.summary


def test_empty_evidence_does_not_claim_success_or_create_statistics():
    result = analyze_trend_report([], [])

    assert result.article_count == 0
    assert result.publisher_count == 0
    assert result.newest_article_at is None
    assert result.topic_clusters == ()
    assert "Chưa cấu hình nguồn" in result.summary
    assert {item.claim_type for item in result.claims} == {"analysis_status"}
    assert all(not item.evidence_ids for item in result.claims)


def test_one_failed_source_and_one_success_are_reflected_in_summary():
    result = analyze_trend_report(
        [article("one", publisher="Báo A")],
        [
            {"source": "ok", "status": "success"},
            {"source": "down", "status": "timeout"},
        ],
    )

    assert result.article_count == 1
    assert "Một số nguồn thu thập bị lỗi" in result.summary
    assert result.topic_clusters == ()


def test_all_failed_sources_are_not_reported_as_success():
    result = analyze_trend_report(
        [],
        [
            {"source": "one", "status": "timeout"},
            {"source": "two", "status": "network_error"},
        ],
    )

    assert "tất cả nguồn thu thập đều lỗi" in result.summary
    assert result.article_count == 0
    assert all(item.claim_type == "analysis_status" for item in result.claims)


def test_stale_and_conflicting_evidence_are_counted_but_not_used_for_topics():
    records = [
        article("stale", title="Đồ ăn vặt", excerpt="Bài viết cũ.", publisher="Báo A", status="stale"),
        article("conflict", title="Đồ ăn vặt", excerpt="Bài viết tranh luận.", publisher="Báo B", status="conflicting"),
    ]

    result = analyze_trend_report(records, [{"source": "rss", "status": "success"}])

    assert result.article_count == 2
    assert result.publisher_count == 2
    assert result.topic_clusters == ()
    assert "1 bài có trạng thái dữ liệu cũ" in result.summary
    assert "1 bài có bằng chứng mâu thuẫn" in result.summary


def test_quantitative_and_topic_claims_link_only_to_evidence_that_supports_them():
    records = [
        article("one", publisher="Báo A", title="Đồ ăn vặt thu hút chú ý", excerpt="Đồ ăn vặt tại hội chợ."),
        article("two", publisher="Báo B", title="Đồ ăn vặt được giới thiệu", excerpt="Sản phẩm mới tại hội chợ."),
        article("three", publisher="Báo C", title="Sách mới được xuất bản", excerpt="Thông tin về sách."),
    ]
    result = analyze_trend_report(records, [{"source": "rss", "status": "success"}])
    evidence_by_id = {item.evidence_id: item for item in result.evidences}

    corpus_claim = next(item for item in result.claims if item.claim_id == "analysis:corpus:v1")
    assert set(corpus_claim.evidence_ids) == set(evidence_by_id)
    for claim in result.claims:
        assert set(claim.evidence_ids).issubset(evidence_by_id)
        assert "tăng trưởng" not in claim.claim_text.casefold()
        if claim.claim_type == "topic_observation":
            cluster = next(item for item in result.topic_clusters if set(item.evidence_ids) == set(claim.evidence_ids))
            for evidence_id in claim.evidence_ids:
                record = evidence_by_id[evidence_id]
                text = f"{record.title} {record.excerpt}".casefold()
                assert cluster.phrase.casefold() in text

