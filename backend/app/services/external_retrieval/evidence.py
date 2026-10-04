"""Evidence contract and pure validation utilities for external retrieval.

The module intentionally has no persistence and performs no network access.
It defines the data shape that future collectors must return before retrieval
results can be passed to an AI prompt or attached to generated content.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
import re
from typing import Any, Iterable
from urllib.parse import urlsplit, urlunsplit


class EvidenceSourceType(str, Enum):
    OFFICIAL_REPORT = "official_report"
    PLATFORM_ANALYTICS = "platform_analytics"
    MARKET_DATA = "market_data"
    NEWS_FEED = "news_feed"
    SEARCH_RESULT = "search_result"
    RSS_FEED = "rss_feed"
    USER_PROVIDED_URL = "user_provided_url"
    MANUAL_VERIFIED = "manual_verified"
    UNKNOWN = "unknown"


class EvidenceVerificationStatus(str, Enum):
    VERIFIED = "verified"
    PARTIAL = "partial"
    UNVERIFIED = "unverified"
    CONFLICTING = "conflicting"
    STALE = "stale"


class EvidenceIssueCode(str, Enum):
    MISSING_REQUIRED_FIELD = "missing_required_field"
    INVALID_URL = "invalid_url"
    UNSUPPORTED_URL_SCHEME = "unsupported_url_scheme"
    INVALID_DATETIME = "invalid_datetime"
    INVALID_SOURCE_TYPE = "invalid_source_type"
    INVALID_VERIFICATION_STATUS = "invalid_verification_status"
    INVALID_CONFIDENCE = "invalid_confidence"
    CONFIDENCE_REQUIRES_BASIS = "confidence_requires_basis"
    VERIFIED_REQUIRES_BASIS = "verified_requires_basis"
    CONTENT_HASH_MISMATCH = "content_hash_mismatch"
    PUBLISHED_AFTER_RETRIEVAL = "published_after_retrieval"
    STALE_EVIDENCE = "stale_evidence"


@dataclass(frozen=True)
class EvidenceIssue:
    code: EvidenceIssueCode
    message: str
    field: str | None = None
    fatal: bool = True


@dataclass(frozen=True)
class Evidence:
    """Normalized evidence record shared by future retrieval providers.

    ``published_at`` may be unknown. ``verification_status`` defaults to the
    safe ``unverified`` value. ``confidence`` is optional and is never inferred
    from a URL, publisher name, or status alone.

    ``metadata`` may contain provider-specific trace fields such as
    ``verification_basis``, ``confidence_basis``, ``retrieval_query``,
    ``region`` and ``platform``.
    """

    evidence_id: str
    title: str
    source_url: str
    publisher: str
    retrieved_at: datetime | str
    excerpt: str
    source_type: EvidenceSourceType | str
    published_at: datetime | str | None = None
    content_hash: str | None = None
    verification_status: EvidenceVerificationStatus | str = EvidenceVerificationStatus.UNVERIFIED
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceNormalizationResult:
    evidence: Evidence | None
    issues: tuple[EvidenceIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        return self.evidence is not None and not any(issue.fatal for issue in self.issues)


@dataclass(frozen=True)
class EvidenceValidationResult:
    evidence: Evidence
    is_valid: bool
    status: EvidenceVerificationStatus
    issues: tuple[EvidenceIssue, ...] = ()
    stale_by_days: float | None = None

    @property
    def is_stale(self) -> bool:
        return self.status is EvidenceVerificationStatus.STALE


def _parse_datetime(value: datetime | str | None, *, field_name: str) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError(f"{field_name} không phải thời gian ISO hợp lệ") from error
    else:
        raise ValueError(f"{field_name} phải là datetime, chuỗi ISO hoặc null")

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _normalize_url(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("source_url không được để trống")

    raw_url = value.strip()
    if any(ord(char) < 32 for char in raw_url):
        raise ValueError("source_url chứa ký tự điều khiển không hợp lệ")

    parsed = urlsplit(raw_url)
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError("source_url chỉ hỗ trợ scheme http hoặc https")
    if not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("source_url phải có host hợp lệ và không chứa thông tin đăng nhập")

    try:
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as error:
        raise ValueError("source_url có host hoặc port không hợp lệ") from error

    if not hostname:
        raise ValueError("source_url thiếu host")

    try:
        hostname = hostname.encode("idna").decode("ascii").lower()
    except UnicodeError as error:
        raise ValueError("source_url có hostname không hợp lệ") from error

    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    netloc = hostname if not port or default_port else f"{hostname}:{port}"
    path = parsed.path or "/"
    return urlunsplit((scheme, netloc, path, parsed.query, ""))


def _normalize_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} phải là chuỗi")
    normalized = re.sub(r"\s+", " ", value).strip()
    if not normalized:
        raise ValueError(f"{field_name} không được để trống")
    return normalized


def _coerce_enum(value: Enum | str, enum_type: type[Enum], *, field_name: str) -> Enum:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(str(value).strip().lower())
    except ValueError as error:
        raise ValueError(f"{field_name} không được hỗ trợ: {value}") from error


def _content_hash(excerpt: str) -> str:
    canonical_excerpt = re.sub(r"\s+", " ", excerpt).strip().encode("utf-8")
    return sha256(canonical_excerpt).hexdigest()


class EvidenceNormalizer:
    """Normalize safe scalar values without assigning trust or confidence."""

    def normalize(self, evidence: Evidence) -> EvidenceNormalizationResult:
        issues: list[EvidenceIssue] = []

        required_values = {
            "evidence_id": evidence.evidence_id,
            "title": evidence.title,
            "source_url": evidence.source_url,
            "publisher": evidence.publisher,
            "excerpt": evidence.excerpt,
            "retrieved_at": evidence.retrieved_at,
            "source_type": evidence.source_type,
        }
        for field_name, value in required_values.items():
            if value is None or (isinstance(value, str) and not value.strip()):
                issues.append(
                    EvidenceIssue(
                        EvidenceIssueCode.MISSING_REQUIRED_FIELD,
                        f"Thiếu trường bắt buộc: {field_name}",
                        field=field_name,
                    )
                )

        if any(issue.fatal for issue in issues):
            return EvidenceNormalizationResult(None, tuple(issues))

        try:
            evidence_id = _normalize_text(str(evidence.evidence_id), field_name="evidence_id")
            title = _normalize_text(evidence.title, field_name="title")
            publisher = _normalize_text(evidence.publisher, field_name="publisher")
            excerpt = _normalize_text(evidence.excerpt, field_name="excerpt")
            source_url = _normalize_url(evidence.source_url)
            retrieved_at = _parse_datetime(evidence.retrieved_at, field_name="retrieved_at")
            published_at = _parse_datetime(evidence.published_at, field_name="published_at")
            source_type = _coerce_enum(
                evidence.source_type,
                EvidenceSourceType,
                field_name="source_type",
            )
            verification_status = _coerce_enum(
                evidence.verification_status,
                EvidenceVerificationStatus,
                field_name="verification_status",
            )
        except ValueError as error:
            message = str(error)
            if "source_url" in message:
                code = (
                    EvidenceIssueCode.UNSUPPORTED_URL_SCHEME
                    if "scheme" in message
                    else EvidenceIssueCode.INVALID_URL
                )
                field_name = "source_url"
            elif "datetime" in message or "thời gian" in message:
                code = EvidenceIssueCode.INVALID_DATETIME
                field_name = "retrieved_at" if "retrieved" in message else "published_at"
            elif "source_type" in message:
                code = EvidenceIssueCode.INVALID_SOURCE_TYPE
                field_name = "source_type"
            elif "verification_status" in message:
                code = EvidenceIssueCode.INVALID_VERIFICATION_STATUS
                field_name = "verification_status"
            else:
                code = EvidenceIssueCode.MISSING_REQUIRED_FIELD
                field_name = None
            issues.append(EvidenceIssue(code, message, field=field_name))
            return EvidenceNormalizationResult(None, tuple(issues))

        computed_hash = _content_hash(excerpt)
        supplied_hash = evidence.content_hash.strip().lower() if evidence.content_hash else None
        if supplied_hash and supplied_hash != computed_hash:
            issues.append(
                EvidenceIssue(
                    EvidenceIssueCode.CONTENT_HASH_MISMATCH,
                    "content_hash không khớp với excerpt đã chuẩn hóa",
                    field="content_hash",
                )
            )

        normalized = Evidence(
            evidence_id=evidence_id,
            title=title,
            source_url=source_url,
            publisher=publisher,
            retrieved_at=retrieved_at,
            excerpt=excerpt,
            source_type=source_type,
            published_at=published_at,
            content_hash=computed_hash,
            verification_status=verification_status,
            confidence=evidence.confidence,
            metadata=dict(evidence.metadata or {}),
        )
        return EvidenceNormalizationResult(normalized, tuple(issues))


class EvidenceValidator:
    """Validate trust metadata and freshness after normalization."""

    def validate(
        self,
        evidence: Evidence,
        *,
        now: datetime | None = None,
        max_age_days: int = 30,
    ) -> EvidenceValidationResult:
        issues: list[EvidenceIssue] = []
        status = _coerce_enum(
            evidence.verification_status,
            EvidenceVerificationStatus,
            field_name="verification_status",
        )
        metadata = evidence.metadata or {}

        if status is EvidenceVerificationStatus.VERIFIED and not str(metadata.get("verification_basis", "")).strip():
            issues.append(
                EvidenceIssue(
                    EvidenceIssueCode.VERIFIED_REQUIRES_BASIS,
                    "verified cần metadata.verification_basis; URL đơn thuần không đủ căn cứ",
                    field="verification_status",
                )
            )

        if evidence.confidence is not None:
            if not isinstance(evidence.confidence, (int, float)) or isinstance(evidence.confidence, bool):
                issues.append(
                    EvidenceIssue(
                        EvidenceIssueCode.INVALID_CONFIDENCE,
                        "confidence phải là số trong khoảng 0 đến 1",
                        field="confidence",
                    )
                )
            elif not 0.0 <= float(evidence.confidence) <= 1.0:
                issues.append(
                    EvidenceIssue(
                        EvidenceIssueCode.INVALID_CONFIDENCE,
                        "confidence phải nằm trong khoảng 0 đến 1",
                        field="confidence",
                    )
                )
            elif not str(metadata.get("confidence_basis", "")).strip():
                issues.append(
                    EvidenceIssue(
                        EvidenceIssueCode.CONFIDENCE_REQUIRES_BASIS,
                        "confidence cần metadata.confidence_basis; không được tự suy diễn",
                        field="confidence",
                    )
                )

        retrieved_at = evidence.retrieved_at
        published_at = evidence.published_at
        if not isinstance(retrieved_at, datetime) or (
            published_at is not None and not isinstance(published_at, datetime)
        ):
            issues.append(
                EvidenceIssue(
                    EvidenceIssueCode.INVALID_DATETIME,
                    "Validator yêu cầu datetime đã được normalizer chuẩn hóa",
                    field="retrieved_at",
                )
            )
            return EvidenceValidationResult(evidence, False, status, tuple(issues))

        if published_at and published_at > retrieved_at:
            issues.append(
                EvidenceIssue(
                    EvidenceIssueCode.PUBLISHED_AFTER_RETRIEVAL,
                    "published_at không được sau retrieved_at",
                    field="published_at",
                )
            )

        reference_now = now or datetime.now(timezone.utc)
        if reference_now.tzinfo is None or reference_now.utcoffset() is None:
            reference_now = reference_now.replace(tzinfo=timezone.utc)
        reference_now = reference_now.astimezone(timezone.utc)

        stale_by_days: float | None = None
        if published_at:
            stale_by_days = (reference_now - published_at.astimezone(timezone.utc)).total_seconds() / 86400
            if stale_by_days > max_age_days:
                status = EvidenceVerificationStatus.STALE
                issues.append(
                    EvidenceIssue(
                        EvidenceIssueCode.STALE_EVIDENCE,
                        f"Evidence cũ {stale_by_days:.1f} ngày, ngưỡng là {max_age_days} ngày",
                        field="published_at",
                        fatal=False,
                    )
                )

        is_valid = not any(issue.fatal for issue in issues)
        return EvidenceValidationResult(
            evidence=evidence,
            is_valid=is_valid,
            status=status,
            issues=tuple(issues),
            stale_by_days=stale_by_days,
        )


class EvidenceDeduplicator:
    """Find duplicate normalized evidence without storing it permanently."""

    @staticmethod
    def duplicate_key(evidence: Evidence) -> str:
        if evidence.content_hash:
            return f"content:{evidence.content_hash.lower()}"
        return f"url:{evidence.source_url}"

    @classmethod
    def duplicate_groups(cls, evidences: Iterable[Evidence]) -> list[tuple[Evidence, ...]]:
        records = list(evidences)
        parent = list(range(len(records)))
        key_owner: dict[str, int] = {}

        def find(index: int) -> int:
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        def union(left: int, right: int) -> None:
            left_root = find(left)
            right_root = find(right)
            if left_root != right_root:
                parent[right_root] = left_root

        for index, evidence in enumerate(records):
            keys = [f"id:{evidence.evidence_id}"]
            if evidence.content_hash:
                keys.append(f"content:{evidence.content_hash.lower()}")
            else:
                keys.append(f"url:{evidence.source_url}")
            for key in keys:
                previous = key_owner.get(key)
                if previous is None:
                    key_owner[key] = index
                else:
                    union(previous, index)

        grouped: dict[int, list[Evidence]] = {}
        for index, evidence in enumerate(records):
            grouped.setdefault(find(index), []).append(evidence)
        return [tuple(group) for group in grouped.values() if len(group) > 1]
