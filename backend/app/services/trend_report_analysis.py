"""Deterministic, evidence-grounded analysis for Trend Radar reports."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import re
import unicodedata
from urllib.parse import urlsplit

from app.services.external_retrieval.evidence import (
    Evidence,
    EvidenceNormalizer,
    EvidenceValidator,
)
from app.services.external_retrieval.rss_sources import RSS_FEEDS_BY_ID


_STOP_WORDS = {
    "a", "about", "an", "and", "are", "at", "be", "been", "being", "but",
    "by", "for", "from", "had", "has", "have", "he", "her", "here", "how",
    "i", "in", "is", "it", "its", "of", "on", "or", "our", "she", "that",
    "the", "their", "them", "there", "they", "this", "to", "was", "we", "were",
    "what", "when", "where", "which", "who", "why", "with", "you", "your",
    "các", "cho", "chúng", "có", "của", "đã", "đang", "đây", "để", "đến",
    "được", "gì", "hay", "là", "mà", "một", "nay", "như", "ở", "sẽ", "thì",
    "trên", "từ", "và", "với", "xu", "hướng", "trend", "trends", "trending", "tiktok",
}
_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
_MAX_CLUSTERS = 5


@dataclass(frozen=True)
class AnalysisClaim:
    claim_id: str
    claim_text: str
    claim_type: str
    evidence_ids: tuple[str, ...] = ()
    caveat: str | None = None


@dataclass(frozen=True)
class TopicCluster:
    phrase: str
    article_count: int
    publisher_count: int
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class TrendReportAnalysis:
    evidences: tuple[Evidence, ...]
    duplicate_ids: dict[str, str]
    article_count: int
    publisher_count: int
    newest_article_at: datetime | None
    topic_clusters: tuple[TopicCluster, ...]
    summary: str
    claims: tuple[AnalysisClaim, ...]


def _fold(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", unicodedata.normalize("NFKC", value).casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _publisher_labels(evidence: Evidence) -> tuple[str, ...]:
    metadata = evidence.metadata if isinstance(evidence.metadata, dict) else {}
    labels: list[str] = []
    explicit = metadata.get("source_publishers")
    if isinstance(explicit, (list, tuple, set)):
        labels.extend(item for item in explicit if isinstance(item, str) and item.strip())
    publisher = metadata.get("publisher_name")
    if not isinstance(publisher, str) or not publisher.strip():
        feed = RSS_FEEDS_BY_ID.get(str(metadata.get("feed_id", "")))
        publisher = feed.publisher if feed else evidence.publisher
    if isinstance(publisher, str) and publisher.strip():
        labels.append(publisher)
    unique: dict[str, str] = {}
    for label in labels:
        normalized = " ".join(label.split())
        unique.setdefault(_fold(normalized), normalized)
    return tuple(unique[key] for key in sorted(unique))


def _canonical_url(value: str) -> str:
    parts = urlsplit(value)
    return f"{parts.scheme.lower()}://{parts.netloc.lower()}{parts.path or '/'}?{parts.query}"


def _deduplicate(records: list[Evidence]) -> tuple[list[Evidence], dict[str, str]]:
    if not records:
        return [], {}
    parent = list(range(len(records)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[max(left_root, right_root)] = min(left_root, right_root)

    owner_by_key: dict[str, int] = {}
    for index, evidence in enumerate(records):
        keys = {
            f"id:{evidence.evidence_id}",
            f"url:{_canonical_url(evidence.source_url)}",
            f"content:{str(evidence.content_hash or '').lower()}",
        }
        for key in keys:
            previous = owner_by_key.get(key)
            if previous is None:
                owner_by_key[key] = index
            else:
                union(previous, index)

    groups: dict[int, list[Evidence]] = defaultdict(list)
    for index, evidence in enumerate(records):
        groups[find(index)].append(evidence)

    canonical_records: list[Evidence] = []
    aliases: dict[str, str] = {}
    for group in groups.values():
        ordered = sorted(group, key=lambda item: item.evidence_id)
        canonical = ordered[0]
        all_publishers = sorted(
            {label for item in ordered for label in _publisher_labels(item)},
            key=lambda label: (_fold(label), label),
        )
        metadata = dict(canonical.metadata or {})
        metadata["source_publishers"] = all_publishers
        metadata["duplicate_evidence_ids"] = [
            item.evidence_id for item in ordered[1:]
        ]
        statuses = {str(getattr(item.verification_status, "value", item.verification_status)).lower() for item in ordered}
        if "conflicting" in statuses:
            metadata["duplicate_statuses"] = sorted(statuses)
            canonical = replace(canonical, verification_status="conflicting")
        elif "stale" in statuses:
            canonical = replace(canonical, verification_status="stale")
        canonical_records.append(replace(canonical, metadata=metadata))
        aliases.update({item.evidence_id: canonical.evidence_id for item in ordered[1:]})

    canonical_records.sort(key=lambda item: item.evidence_id)
    return canonical_records, aliases


def _extract_clusters(evidences: tuple[Evidence, ...]) -> tuple[TopicCluster, ...]:
    phrase_support: dict[tuple[str, ...], list[Evidence]] = defaultdict(list)
    phrase_display: dict[tuple[str, ...], str] = {}
    for evidence in evidences:
        status = str(getattr(evidence.verification_status, "value", evidence.verification_status)).lower()
        if status in {"stale", "conflicting"}:
            continue
        evidence_phrases: set[tuple[str, ...]] = set()
        for field in (evidence.title, evidence.excerpt):
            tokens = _TOKEN_RE.findall(field.casefold())
            for size in (1, 2, 3):
                for start in range(0, len(tokens) - size + 1):
                    surface = tuple(tokens[start : start + size])
                    folded = tuple(_fold(token) for token in surface)
                    if any(token in _STOP_WORDS for token in surface):
                        continue
                    minimum_length = 3 if size == 1 else 2
                    if any(
                        not any(char.isalpha() for char in token) or len(token) < minimum_length
                        for token in folded
                    ):
                        continue
                    evidence_phrases.add(folded)
                    phrase_display.setdefault(folded, " ".join(surface))
        for phrase in evidence_phrases:
            phrase_support[phrase].append(evidence)

    candidates: list[TopicCluster] = []
    for phrase, supporting in phrase_support.items():
        unique_by_id = {item.evidence_id: item for item in supporting}
        if len(unique_by_id) < 2:
            continue
        publisher_labels = {
            _fold(label)
            for item in unique_by_id.values()
            for label in _publisher_labels(item)
        }
        # Repeated text from one publisher is too narrow to label a topic group.
        if len(publisher_labels) < 2:
            continue
        ids = tuple(sorted(unique_by_id))
        candidates.append(
            TopicCluster(
                phrase=phrase_display[phrase],
                article_count=len(ids),
                publisher_count=len(publisher_labels),
                evidence_ids=ids,
            )
        )

    candidates.sort(
        key=lambda item: (
            -item.article_count,
            -item.publisher_count,
            -len(item.phrase.split()),
            _fold(item.phrase),
            item.evidence_ids,
        )
    )
    return tuple(candidates[:_MAX_CLUSTERS])


def _source_state(source_statuses: list[dict]) -> str:
    if not source_statuses:
        return "no_sources"
    states = [str(item.get("status", "unknown")).lower() for item in source_statuses]
    if all(state not in {"success", "empty"} for state in states):
        return "all_failed"
    if any(state not in {"success", "empty"} for state in states):
        return "partial_failure"
    return "completed"


def _summary(
    evidences: tuple[Evidence, ...],
    publisher_count: int,
    newest: datetime | None,
    clusters: tuple[TopicCluster, ...],
    source_statuses: list[dict],
) -> str:
    state = _source_state(source_statuses)
    if not evidences:
        if state == "no_sources":
            return "Chưa cấu hình nguồn RSS, nên chưa có bài báo để lập báo cáo theo chủ đề."
        if state == "all_failed":
            failed = ", ".join(
                f"{item.get('source', 'nguồn không rõ')}: {item.get('status', 'lỗi')}"
                for item in source_statuses
            )
            return f"Không có bằng chứng hợp lệ để lập báo cáo; tất cả nguồn thu thập đều lỗi ({failed})."
        if state == "partial_failure":
            return "Không có bằng chứng hợp lệ để lập báo cáo; một số nguồn thu thập bị lỗi, các nguồn còn lại không cung cấp bằng chứng phù hợp."
        return "Các nguồn đã hoàn tất nhưng không có bằng chứng phù hợp với truy vấn; chưa thể rút ra chủ đề."

    stale_count = sum(
        str(getattr(item.verification_status, "value", item.verification_status)).lower() == "stale"
        for item in evidences
    )
    conflicting_count = sum(
        str(getattr(item.verification_status, "value", item.verification_status)).lower() == "conflicting"
        for item in evidences
    )
    parts = [
        f"Bằng chứng gồm {len(evidences)} bài sau khi loại trùng, từ {publisher_count} đơn vị xuất bản độc lập."
    ]
    if newest:
        parts.append(f"Bài có thời điểm xuất bản mới nhất ghi nhận lúc {newest.astimezone(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}.")
    if clusters:
        phrases = "; ".join(
            f"“{item.phrase}” ({item.article_count} bài, {item.publisher_count} publisher)"
            for item in clusters
        )
        parts.append(f"Các cụm từ lặp lại trong tiêu đề hoặc trích đoạn: {phrases}.")
    else:
        parts.append("Chưa đủ evidence từ ít nhất hai publisher độc lập để tạo nhóm chủ đề đáng tin cậy.")
    if stale_count:
        parts.append(f"{stale_count} bài có trạng thái dữ liệu cũ.")
    if conflicting_count:
        parts.append(f"{conflicting_count} bài có bằng chứng mâu thuẫn và không dùng để tạo nhóm chủ đề.")
    if state == "partial_failure":
        parts.append("Một số nguồn thu thập bị lỗi; kết quả chỉ phản ánh evidence đã nhận được.")
    parts.append("Đây là số bài RSS và cụm từ quan sát được, không phải lượt xem, doanh số, độ viral hay thứ hạng nền tảng.")
    return " ".join(parts)


def analyze_trend_report(
    evidences: tuple[Evidence, ...] | list[Evidence],
    source_statuses: list[dict] | tuple[dict, ...],
) -> TrendReportAnalysis:
    """Normalize, validate, deduplicate and summarize evidence without I/O."""
    normalized: list[Evidence] = []
    normalizer, validator = EvidenceNormalizer(), EvidenceValidator()
    for raw in evidences:
        if not isinstance(raw, Evidence):
            continue
        try:
            metadata = raw.metadata if isinstance(raw.metadata, dict) else {}
            result = normalizer.normalize(replace(raw, metadata=dict(metadata)))
        except (TypeError, ValueError, AttributeError):
            continue
        if not result.is_valid or result.evidence is None:
            continue
        normalized.append(result.evidence)

    reference_now = max(
        (item.retrieved_at for item in normalized),
        default=datetime(1970, 1, 1, tzinfo=timezone.utc),
    )
    valid: list[Evidence] = []
    for item in normalized:
        validation = validator.validate(item, now=reference_now, max_age_days=3650)
        if not validation.is_valid:
            continue
        # The collector already applied the caller's freshness threshold. Keep
        # its persisted status stable instead of re-aging data during GET.
        valid.append(item)

    canonical, duplicate_ids = _deduplicate(valid)
    canonical_tuple = tuple(canonical)
    publishers = {
        _fold(label)
        for item in canonical_tuple
        for label in _publisher_labels(item)
    }
    published = [item.published_at for item in canonical_tuple if item.published_at is not None]
    newest = max(published, key=lambda item: item.astimezone(timezone.utc)) if published else None
    clusters = _extract_clusters(canonical_tuple)

    claim_list: list[AnalysisClaim] = []
    evidence_ids = tuple(item.evidence_id for item in canonical_tuple)
    if canonical_tuple:
        claim_list.append(
            AnalysisClaim(
                claim_id="analysis:corpus:v1",
                claim_text=f"Bằng chứng gồm {len(canonical_tuple)} bài sau khi loại trùng, từ {len(publishers)} đơn vị xuất bản độc lập.",
                claim_type="report_statistic",
                evidence_ids=evidence_ids,
            )
        )
    if newest is not None:
        newest_ids = tuple(sorted(
            item.evidence_id
            for item in canonical_tuple
            if item.published_at is not None
            and item.published_at.astimezone(timezone.utc) == newest.astimezone(timezone.utc)
        ))
        claim_list.append(
            AnalysisClaim(
                claim_id="analysis:newest:v1",
                claim_text=f"Thời điểm xuất bản mới nhất ghi nhận trong evidence là {newest.astimezone(timezone.utc).isoformat()}.",
                claim_type="report_statistic",
                evidence_ids=newest_ids,
            )
        )
    for index, cluster in enumerate(clusters, start=1):
        claim_list.append(
            AnalysisClaim(
                claim_id=f"analysis:topic:{index}:v1",
                claim_text=(
                    f"Cụm từ “{cluster.phrase}” xuất hiện trong tiêu đề hoặc trích đoạn "
                    f"của {cluster.article_count} bài thuộc {cluster.publisher_count} publisher."
                ),
                claim_type="topic_observation",
                evidence_ids=cluster.evidence_ids,
                caveat="Đây là quan sát lặp lại trong RSS, không xác nhận độ phổ biến hay thứ hạng trên nền tảng.",
            )
        )
    if not clusters:
        claim_list.append(
            AnalysisClaim(
                claim_id="analysis:insufficient-topics:v1",
                claim_text="Chưa đủ evidence từ ít nhất hai publisher độc lập để tạo nhóm chủ đề đáng tin cậy.",
                claim_type="analysis_status",
                caveat="Không suy diễn chủ đề khi corpus quá nhỏ hoặc chỉ có một publisher.",
            )
        )

    state_statuses = [dict(item) for item in source_statuses if isinstance(item, dict)]
    summary = _summary(canonical_tuple, len(publishers), newest, clusters, state_statuses)
    cached_sources = [item for item in state_statuses if item.get("from_cache") is True]
    if cached_sources:
        original_times = sorted(
            {
                str(item.get("original_collected_at") or item.get("collected_at"))
                for item in cached_sources
                if item.get("original_collected_at") or item.get("collected_at")
            }
        )
        source_names = sorted(
            {str(item.get("source", "nguồn không rõ")) for item in cached_sources}
        )
        time_label = ", ".join(original_times) if original_times else "không có thời điểm nguồn"
        summary += (
            " Kết quả được dùng lại từ bộ nhớ đệm, không phải lần thu thập mới; "
            f"nguồn: {', '.join(source_names)}; thời điểm thu thập ban đầu: {time_label}."
        )
    return TrendReportAnalysis(
        evidences=canonical_tuple,
        duplicate_ids=duplicate_ids,
        article_count=len(canonical_tuple),
        publisher_count=len(publishers),
        newest_article_at=newest,
        topic_clusters=clusters,
        summary=summary,
        claims=tuple(claim_list),
    )
