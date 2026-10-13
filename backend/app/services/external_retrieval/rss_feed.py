"""Bounded, allowlisted RSS/Atom retrieval for Trend Radar."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from hashlib import sha256
from html import unescape
import ipaddress
import re
import socket
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlsplit
import unicodedata

import httpx

from app.services.external_retrieval.evidence import Evidence, EvidenceSourceType
from app.services.external_retrieval.provider import SearchProviderResult, SearchProviderStatus
from app.services.external_retrieval.rss_sources import (
    RSSFeedSource,
    RSS_FEEDS_BY_ID,
    RSS_FEEDS_BY_URL,
    TREND_RADAR_RSS_FEEDS,
)


MAX_RESPONSE_BYTES = 512 * 1024
MAX_ENTRIES = 50
MAX_EXCERPT_CHARS = 1200
MAX_REDIRECTS = 2
REQUEST_TIMEOUT_SECONDS = 8.0
_STOP_WORDS = {
    "a", "an", "and", "are", "at", "be", "biet", "ban", "bi", "co", "cua",
    "cho", "dang", "day", "do", "duoc", "gi", "hien", "how", "is", "la", "mot",
    "nay", "nhu", "nao", "on", "o", "san", "se", "the", "thi", "tren",
    "trend", "trends", "trending", "tiktok", "to", "xu", "with", "what", "where",
    "which", "who", "why", "you", "your", "huong", "khong", "pham",
}


class _UnsafeFeedTarget(ValueError):
    pass


class _FeedNetworkFailure(RuntimeError):
    pass


class RSSFeedCollector:
    """Read one publisher feed; callers can only select a compiled-in source."""

    def __init__(
        self,
        feed: RSSFeedSource,
        *,
        transport: httpx.BaseTransport | None = None,
        resolver: Callable[[str, int], Iterable[str]] | None = None,
        clock: Callable[[], datetime] | None = None,
    ):
        registered = RSS_FEEDS_BY_ID.get(feed.feed_id)
        if registered != feed or RSS_FEEDS_BY_URL.get(feed.url) != feed:
            raise ValueError("RSS feed must be selected from the Trend Radar allowlist.")
        self.feed = feed
        self.platform = f"{feed.publisher} · {feed.category}"
        self.transport = transport
        self.resolver = resolver or _system_resolver
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def collect(self, query: str) -> SearchProviderResult:
        safe_query = " ".join((query or "").split())
        if not safe_query or len(safe_query) > 512:
            return SearchProviderResult(
                SearchProviderStatus.INVALID_REQUEST,
                message="Chủ đề cần từ 1 đến 512 ký tự.",
            )

        terms = _query_terms(safe_query)
        if not terms:
            return SearchProviderResult(
                SearchProviderStatus.EMPTY,
                message="Chủ đề cần có từ khóa cụ thể để lọc bài RSS.",
                metadata={"feed_id": self.feed.feed_id},
            )

        try:
            document = self._download()
        except _UnsafeFeedTarget:
            return SearchProviderResult(
                SearchProviderStatus.HTTP_ERROR,
                message="Đích RSS hoặc địa chỉ mạng không nằm trong phạm vi cho phép.",
                metadata={"feed_id": self.feed.feed_id},
            )
        except httpx.TimeoutException:
            return SearchProviderResult(
                SearchProviderStatus.TIMEOUT,
                message="Nguồn RSS hết thời gian chờ.",
                metadata={"feed_id": self.feed.feed_id},
            )
        except _FeedNetworkFailure:
            return SearchProviderResult(
                SearchProviderStatus.NETWORK_ERROR,
                message="Không thể kết nối tới nguồn RSS.",
                metadata={"feed_id": self.feed.feed_id},
            )
        except httpx.TransportError:
            return SearchProviderResult(
                SearchProviderStatus.NETWORK_ERROR,
                message="Không thể kết nối tới nguồn RSS.",
                metadata={"feed_id": self.feed.feed_id},
            )
        except _FeedHTTPFailure as error:
            return SearchProviderResult(
                SearchProviderStatus.HTTP_ERROR,
                message=str(error),
                metadata={"feed_id": self.feed.feed_id},
            )

        try:
            entries = _parse_feed(document)
        except (ET.ParseError, ValueError):
            return SearchProviderResult(
                SearchProviderStatus.INVALID_RESPONSE,
                message="Nguồn RSS trả về XML không hợp lệ hoặc không được hỗ trợ.",
                metadata={"feed_id": self.feed.feed_id},
            )

        retrieved_at = self.clock()
        evidences = []
        valid_entries = 0
        for entry in entries[:MAX_ENTRIES]:
            title = entry["title"]
            excerpt = entry["excerpt"] or title
            if not title or not entry["url"]:
                continue
            article_url = _safe_article_url(entry["url"], self.feed.allowed_article_hosts)
            if article_url is None:
                continue
            valid_entries += 1
            if not _contains_all_terms(f"{title} {excerpt}", terms):
                continue
            fingerprint = f"{self.feed.feed_id}\n{article_url}\n{title}".encode("utf-8")
            evidence_id = f"rss:{self.feed.feed_id}:{sha256(fingerprint).hexdigest()[:24]}"
            evidences.append(
                Evidence(
                    evidence_id=evidence_id,
                    title=title[:300],
                    source_url=article_url,
                    publisher=self.feed.publisher,
                    retrieved_at=retrieved_at,
                    published_at=entry["published_at"],
                    excerpt=excerpt[:MAX_EXCERPT_CHARS],
                    source_type=EvidenceSourceType.RSS_FEED,
                    metadata={
                        "provider": "allowlisted_rss",
                        "feed_id": self.feed.feed_id,
                        "publisher_name": self.feed.publisher,
                        "feed_category": self.feed.category,
                        "feed_url": self.feed.url,
                        "source_directory_url": self.feed.directory_url,
                        "retrieval_query": safe_query,
                        "platform": self.platform,
                    },
                )
            )

        metadata = {
            "feed_id": self.feed.feed_id,
            "entries_checked": min(len(entries), MAX_ENTRIES),
            "valid_entries": valid_entries,
            "matched_entries": len(evidences),
            "result_state": (
                "success" if evidences else
                "no_topic_matches" if valid_entries else "no_valid_entries"
            ),
        }
        if not evidences:
            return SearchProviderResult(
                SearchProviderStatus.EMPTY,
                message="Không có kết quả phù hợp từ feed RSS cho truy vấn này.",
                metadata=metadata,
            )
        return SearchProviderResult(
            SearchProviderStatus.SUCCESS,
            evidences=tuple(evidences),
            metadata=metadata,
        )

    def _download(self) -> bytes:
        url = self.feed.url
        with httpx.Client(
            timeout=httpx.Timeout(REQUEST_TIMEOUT_SECONDS),
            transport=self.transport,
            follow_redirects=False,
            trust_env=False,
            headers={
                "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9",
                "Accept-Encoding": "identity",
                "User-Agent": "AdGenAI Trend Radar RSS reader",
            },
        ) as client:
            for redirect_count in range(MAX_REDIRECTS + 1):
                target = _registered_url(url)
                _assert_public_addresses(target, self.resolver)
                with client.stream("GET", target) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location or redirect_count >= MAX_REDIRECTS:
                            raise _FeedHTTPFailure("Nguồn RSS chuyển hướng vượt giới hạn cho phép.")
                        next_url = urljoin(target, location)
                        _registered_url(next_url)
                        # The next iteration validates the redirect target's DNS before GET.
                        url = next_url
                        continue
                    if response.is_error:
                        raise _FeedHTTPFailure(f"Nguồn RSS trả HTTP {response.status_code}.")
                    content_length = response.headers.get("content-length")
                    if content_length:
                        try:
                            if int(content_length) > MAX_RESPONSE_BYTES:
                                raise _FeedHTTPFailure("Nguồn RSS vượt quá giới hạn kích thước.")
                        except ValueError as error:
                            raise _FeedHTTPFailure("Nguồn RSS có Content-Length không hợp lệ.") from error
                    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                    if content_type and content_type not in {
                        "application/rss+xml", "application/atom+xml", "application/xml", "text/xml",
                    }:
                        raise _FeedHTTPFailure("Nguồn RSS trả về loại nội dung không được hỗ trợ.")
                    chunks = bytearray()
                    for chunk in response.iter_bytes():
                        chunks.extend(chunk)
                        if len(chunks) > MAX_RESPONSE_BYTES:
                            raise _FeedHTTPFailure("Nguồn RSS vượt quá giới hạn kích thước.")
                    return bytes(chunks)
        raise _FeedHTTPFailure("Nguồn RSS không trả về tài liệu hợp lệ.")


class _FeedHTTPFailure(RuntimeError):
    pass


def _system_resolver(host: str, port: int) -> list[str]:
    try:
        return list({record[4][0] for record in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)})
    except OSError as error:
        raise _FeedNetworkFailure from error


def _registered_url(url: str) -> str:
    source = RSS_FEEDS_BY_URL.get(url)
    if source is None:
        raise _UnsafeFeedTarget
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or parsed.hostname not in source.allowed_article_hosts
        or parsed.query
        or parsed.fragment
    ):
        raise _UnsafeFeedTarget
    return url


def _assert_public_addresses(url: str, resolver: Callable[[str, int], Iterable[str]]) -> None:
    parsed = urlsplit(url)
    try:
        addresses = tuple(resolver(parsed.hostname or "", parsed.port or 443))
    except (OSError, _FeedNetworkFailure) as error:
        raise _FeedNetworkFailure from error
    if not addresses:
        raise _FeedNetworkFailure
    for address in addresses:
        try:
            resolved = ipaddress.ip_address(address)
        except ValueError as error:
            raise _UnsafeFeedTarget from error
        if not resolved.is_global:
            raise _UnsafeFeedTarget


def _parse_feed(document: bytes) -> list[dict[str, object]]:
    if re.search(br"<!\s*(DOCTYPE|ENTITY)\b", document, flags=re.IGNORECASE):
        raise ValueError("DTD and entity declarations are not supported")
    root = ET.fromstring(document)
    root_name = _local_name(root.tag)
    if root_name == "rss":
        parents = [child for child in root if _local_name(child.tag) == "channel"]
        if not parents:
            raise ValueError("RSS channel is missing")
        raw_entries = [child for child in parents[0] if _local_name(child.tag) == "item"]
        entries = [_parse_rss_item(item) for item in raw_entries[:MAX_ENTRIES]]
    elif root_name == "feed":
        raw_entries = [child for child in root if _local_name(child.tag) == "entry"]
        entries = [_parse_atom_entry(item) for item in raw_entries[:MAX_ENTRIES]]
    else:
        raise ValueError("Unsupported feed root")
    return entries


def _parse_rss_item(item: ET.Element) -> dict[str, object]:
    return {
        "title": _clean_text(_child_text(item, "title")),
        "url": _child_text(item, "link").strip(),
        "excerpt": _clean_text(_child_text(item, "description") or _child_text(item, "content")),
        "published_at": _parse_datetime(_child_text(item, "pubDate") or _child_text(item, "date")),
    }


def _parse_atom_entry(entry: ET.Element) -> dict[str, object]:
    link = next((child.attrib.get("href", "") for child in entry if _local_name(child.tag) == "link" and child.attrib.get("rel", "alternate") == "alternate"), "")
    return {
        "title": _clean_text(_child_text(entry, "title")),
        "url": link,
        "excerpt": _clean_text(_child_text(entry, "summary") or _child_text(entry, "content")),
        "published_at": _parse_datetime(_child_text(entry, "published") or _child_text(entry, "updated")),
    }


def _child_text(element: ET.Element, name: str) -> str:
    child = next((item for item in element if _local_name(item.tag) == name.lower()), None)
    return "" if child is None else "".join(child.itertext())


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _clean_text(value: str) -> str:
    without_markup = re.sub(r"<[^>]*>", " ", value)
    return re.sub(r"\s+", " ", unescape(without_markup)).strip()


def _parse_datetime(value: str) -> datetime | None:
    if not value.strip():
        return None
    try:
        parsed = parsedate_to_datetime(value.strip())
    except (TypeError, ValueError, OverflowError):
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _normalize_search_text(value: str) -> str:
    folded = value.casefold().replace("đ", "d")
    decomposed = unicodedata.normalize("NFKD", folded)
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", plain))


def _query_terms(query: str) -> frozenset[str]:
    normalized = _normalize_search_text(query)
    return frozenset(word for word in normalized.split() if word not in _STOP_WORDS)


def _contains_all_terms(value: str, terms: frozenset[str]) -> bool:
    haystack = f" {_normalize_search_text(value)} "
    return all(f" {term} " in haystack for term in terms)


def _safe_article_url(value: str, allowed_hosts: tuple[str, ...]) -> str | None:
    try:
        parsed = urlsplit(value.strip())
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.port not in (None, 443)
            or parsed.hostname.lower() not in allowed_hosts
        ):
            return None
    except ValueError:
        return None
    return value.strip()


def build_trend_radar_rss_collectors(
    *,
    transport: httpx.BaseTransport | None = None,
    resolver: Callable[[str, int], Iterable[str]] | None = None,
    clock: Callable[[], datetime] | None = None,
) -> list[RSSFeedCollector]:
    """Create collectors for the reviewed publisher allowlist."""
    return [
        RSSFeedCollector(source, transport=transport, resolver=resolver, clock=clock)
        for source in TREND_RADAR_RSS_FEEDS
    ]
