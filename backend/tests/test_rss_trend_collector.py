from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256

import httpx
import pytest

from app.services.external_retrieval.evidence import EvidenceSourceType
from app.services.external_retrieval.provider import SearchProviderStatus
from app.services.external_retrieval.rss_feed import (
    MAX_ENTRIES,
    MAX_RESPONSE_BYTES,
    RSSFeedCollector,
)
from app.services.external_retrieval.rss_sources import TREND_RADAR_RSS_FEEDS


NOW = datetime(2026, 10, 14, 8, 0, tzinfo=timezone.utc)
PUBLIC_IP = "8.8.8.8"


def _rss_document(*, count=1):
    items = []
    for index in range(count):
        items.append(
            f"""
            <item>
              <title>Đồ ăn vặt được người tiêu dùng quan tâm {index}</title>
              <link>https://thanhnien.vn/doi-song/do-an-vat-{index}.html</link>
              <description><![CDATA[Thị trường đồ ăn vặt và sản phẩm mới.]]></description>
              <pubDate>Tue, 13 Oct 2026 10:30:00 +0700</pubDate>
            </item>
            """
        )
    return (
        "<?xml version='1.0' encoding='utf-8'?>"
        "<rss version='2.0'><channel><title>fixture</title>"
        + "".join(items)
        + "</channel></rss>"
    ).encode("utf-8")


def _collector(*, transport, resolver=None, feed=None):
    return RSSFeedCollector(
        feed or TREND_RADAR_RSS_FEEDS[0],
        transport=transport,
        resolver=resolver or (lambda host, port: [PUBLIC_IP]),
        clock=lambda: NOW,
    )


def test_allowlisted_rss_fixture_becomes_unverified_article_evidence():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(
            200,
            headers={"Content-Type": "application/rss+xml"},
            content=_rss_document(),
        )

    collector = _collector(transport=httpx.MockTransport(handler))
    result = collector.collect("bạn có biết ở trên TikTok hiện nay đang xu hướng sản phẩm đồ ăn vặt nào không")

    assert result.status is SearchProviderStatus.SUCCESS
    assert len(result.evidences) == 1
    evidence = result.evidences[0]
    assert evidence.source_type is EvidenceSourceType.RSS_FEED
    assert evidence.publisher == "Báo Thanh Niên"
    assert evidence.metadata["publisher_name"] == "Báo Thanh Niên"
    assert evidence.metadata["feed_category"] == "Tiêu dùng thông minh"
    assert evidence.metadata["source_directory_url"] == "https://thanhnien.vn/rss.html"
    assert evidence.source_url == "https://thanhnien.vn/doi-song/do-an-vat-0.html"
    assert evidence.published_at == datetime(2026, 10, 13, 3, 30, tzinfo=timezone.utc)
    assert seen[0].url == TREND_RADAR_RSS_FEEDS[0].url


def test_empty_result_message_does_not_assume_the_feed_had_matching_candidates():
    result = _collector(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=_rss_document())
        )
    ).collect("chân gà rút xương")

    assert result.status is SearchProviderStatus.EMPTY
    assert result.message == "Không có kết quả phù hợp từ feed RSS cho truy vấn này."
    assert result.metadata["entries_checked"] == 1
    assert result.metadata["valid_entries"] == 1
    assert result.metadata["matched_entries"] == 0
    assert result.metadata["result_state"] == "no_topic_matches"


def test_empty_feed_and_invalid_articles_are_not_topic_mismatches():
    documents = (
        b"<rss><channel /></rss>",
        b"<rss><channel><item><title>Snack</title></item></channel></rss>",
    )
    for document, checked in zip(documents, (0, 1)):
        result = _collector(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, content=document)
            )
        ).collect("snack")
        assert result.status is SearchProviderStatus.EMPTY
        assert result.metadata["entries_checked"] == checked
        assert result.metadata["valid_entries"] == 0
        assert result.metadata["matched_entries"] == 0
        assert result.metadata["result_state"] == "no_valid_entries"


def test_matching_article_keeps_its_existing_evidence_id():
    result = _collector(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=_rss_document())
        )
    ).collect("đồ ăn vặt")
    evidence = result.evidences[0]
    fingerprint = f"{TREND_RADAR_RSS_FEEDS[0].feed_id}\n{evidence.source_url}\n{evidence.title}"
    expected = f"rss:{TREND_RADAR_RSS_FEEDS[0].feed_id}:{sha256(fingerprint.encode('utf-8')).hexdigest()[:24]}"
    assert evidence.evidence_id == expected
    assert result.metadata["entries_checked"] == 1
    assert result.metadata["valid_entries"] == 1
    assert result.metadata["matched_entries"] == 1
    assert result.metadata["result_state"] == "success"


def test_feed_constructor_rejects_any_source_not_in_compiled_allowlist():
    unsafe = replace(TREND_RADAR_RSS_FEEDS[0], url="http://127.0.0.1/private")

    with pytest.raises(ValueError, match="allowlist"):
        RSSFeedCollector(unsafe)


def test_private_dns_address_is_rejected_before_http_request():
    requests = []
    collector = _collector(
        transport=httpx.MockTransport(lambda request: requests.append(request)),
        resolver=lambda host, port: ["127.0.0.1"],
    )

    result = collector.collect("đồ ăn vặt")

    assert result.status is SearchProviderStatus.HTTP_ERROR
    assert "không nằm trong phạm vi" in result.message
    assert requests == []


def test_redirect_to_non_allowlisted_target_is_rejected_without_following():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(302, headers={"Location": "http://127.0.0.1/admin"})

    result = _collector(transport=httpx.MockTransport(handler)).collect("đồ ăn vặt")

    assert result.status is SearchProviderStatus.HTTP_ERROR
    assert len(requests) == 1


def test_safe_redirect_to_another_registered_feed_is_resolved_before_request():
    requests = []

    def handler(request):
        requests.append(request.url)
        if len(requests) == 1:
            return httpx.Response(302, headers={"Location": TREND_RADAR_RSS_FEEDS[1].url})
        return httpx.Response(200, content=_rss_document())

    resolved_hosts = []

    def resolver(host, port):
        resolved_hosts.append((host, port))
        return [PUBLIC_IP]

    result = _collector(transport=httpx.MockTransport(handler), resolver=resolver).collect("đồ ăn vặt")

    assert result.status is SearchProviderStatus.SUCCESS
    assert [str(url) for url in requests] == [
        TREND_RADAR_RSS_FEEDS[0].url,
        TREND_RADAR_RSS_FEEDS[1].url,
    ]
    assert resolved_hosts == [("thanhnien.vn", 443), ("thanhnien.vn", 443)]


def test_redirect_to_allowed_feed_with_private_dns_is_blocked_before_following():
    requests = []
    resolve_count = 0

    def handler(request):
        requests.append(request.url)
        return httpx.Response(302, headers={"Location": TREND_RADAR_RSS_FEEDS[1].url})

    def resolver(host, port):
        nonlocal resolve_count
        resolve_count += 1
        return [PUBLIC_IP] if resolve_count == 1 else ["10.0.0.7"]

    result = _collector(transport=httpx.MockTransport(handler), resolver=resolver).collect("đồ ăn vặt")

    assert result.status is SearchProviderStatus.HTTP_ERROR
    assert len(requests) == 1
    assert resolve_count == 2


def test_atom_fixture_is_supported_and_dtd_is_rejected():
    atom = """<?xml version='1.0'?>
    <feed xmlns='http://www.w3.org/2005/Atom'>
      <entry>
        <title>Đồ ăn vặt trong mùa hè</title>
        <link href='https://thanhnien.vn/doi-song/mon-an-vat.html' />
        <summary>Sản phẩm đồ ăn vặt mới.</summary>
        <updated>2026-10-13T10:30:00+07:00</updated>
      </entry>
    </feed>""".encode("utf-8")
    parsed = _collector(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=atom))
    ).collect("đồ ăn vặt")
    assert parsed.status is SearchProviderStatus.SUCCESS
    assert len(parsed.evidences) == 1
    assert parsed.evidences[0].published_at == datetime(2026, 10, 13, 3, 30, tzinfo=timezone.utc)

    dtd = b"<!DOCTYPE rss [<!ENTITY x 'unsafe'>]><rss><channel /></rss>"
    rejected = _collector(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=dtd))
    ).collect("đồ ăn vặt")
    assert rejected.status is SearchProviderStatus.INVALID_RESPONSE


def test_collector_caps_entries_and_response_size():
    def handler(request):
        return httpx.Response(200, content=_rss_document(count=MAX_ENTRIES + 10))

    collector = _collector(transport=httpx.MockTransport(handler))
    result = collector.collect("đồ ăn vặt")
    assert result.status is SearchProviderStatus.SUCCESS
    assert len(result.evidences) == MAX_ENTRIES

    too_large = _collector(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=b"x" * (MAX_RESPONSE_BYTES + 1))
        )
    ).collect("đồ ăn vặt")
    assert too_large.status is SearchProviderStatus.HTTP_ERROR
    assert "kích thước" in too_large.message

    undeclared_large_body = _collector(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                headers={"Content-Length": "1"},
                content=b"x" * (MAX_RESPONSE_BYTES + 1),
            )
        )
    ).collect("đồ ăn vặt")
    assert undeclared_large_body.status is SearchProviderStatus.HTTP_ERROR
    assert "kích thước" in undeclared_large_body.message


def test_collector_reports_timeout_and_invalid_xml_without_retry():
    calls = []

    def timeout_handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("fixture timeout", request=request)

    timeout = _collector(transport=httpx.MockTransport(timeout_handler)).collect("đồ ăn vặt")
    assert timeout.status is SearchProviderStatus.TIMEOUT
    assert len(calls) == 1
    assert "entries_checked" not in timeout.metadata

    invalid = _collector(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"not xml"))
    ).collect("đồ ăn vặt")
    assert invalid.status is SearchProviderStatus.INVALID_RESPONSE
    assert "entries_checked" not in invalid.metadata


def test_generic_topic_without_search_terms_does_not_fetch_feed():
    calls = []
    result = _collector(
        transport=httpx.MockTransport(lambda request: calls.append(request))
    ).collect("xu hướng TikTok")

    assert result.status is SearchProviderStatus.EMPTY
    assert calls == []
