"""Stage-2 multi-platform orchestration; adapters are injected and never live by default."""
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Protocol

from app.services.external_retrieval.evidence import (
    Evidence, EvidenceDeduplicator, EvidenceNormalizer, EvidenceValidator,
    EvidenceVerificationStatus,
)
from app.services.external_retrieval.provider import SearchProviderResult, SearchProviderStatus


class PlatformCollector(Protocol):
    platform: str
    def collect(self, query: str) -> SearchProviderResult: ...


@dataclass(frozen=True)
class PlatformCollectionStatus:
    platform: str
    status: SearchProviderStatus
    message: str | None = None
    collected_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MultiPlatformRetrievalResult:
    evidences: tuple[Evidence, ...]
    sources: tuple[PlatformCollectionStatus, ...]
    duplicate_ids: dict[str, str] = field(default_factory=dict)
    from_cache: bool = False

    @property
    def has_usable_evidence(self) -> bool:
        return bool(self.evidences)


class MultiPlatformRetrievalService:
    """Normalize, retain stale/conflicting evidence, and expose every source outcome.

    Conflict is explicit provider metadata (``conflicts_with``), never keyword or
    semantic inference. Cache entries are only reused on an explicit non-refresh
    request, so callers cannot represent cached evidence as a new retrieval.
    """
    def __init__(self, collectors: list[PlatformCollector], *, clock=None):
        self.collectors = list(collectors)
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self._cache: dict[tuple[str, int], MultiPlatformRetrievalResult] = {}

    def retrieve(self, query: str, *, refresh: bool = False, max_age_days: int = 30) -> MultiPlatformRetrievalResult:
        safe_query = " ".join((query or "").split())
        if not safe_query:
            return MultiPlatformRetrievalResult((), ())
        cache_key = (safe_query, max_age_days)
        if not refresh and cache_key in self._cache:
            cached = self._cache[cache_key]
            now = self.clock()
            if now.tzinfo is None or now.utcoffset() is None:
                now = now.replace(tzinfo=timezone.utc)
            validator = EvidenceValidator()
            refreshed_evidences = []
            for evidence in cached.evidences:
                validation = validator.validate(
                    evidence,
                    now=now,
                    max_age_days=max_age_days,
                )
                existing_status = str(
                    getattr(evidence.verification_status, "value", evidence.verification_status)
                ).lower()
                status = (
                    EvidenceVerificationStatus.CONFLICTING
                    if existing_status == EvidenceVerificationStatus.CONFLICTING.value
                    else validation.status
                )
                refreshed_evidences.append(replace(evidence, verification_status=status))
            return replace(cached, evidences=tuple(refreshed_evidences), from_cache=True)

        statuses: list[PlatformCollectionStatus] = []
        records: list[Evidence] = []
        normalizer, validator = EvidenceNormalizer(), EvidenceValidator()
        for collector in self.collectors:
            platform = str(getattr(collector, "platform", collector.__class__.__name__)).strip() or "unknown"
            try:
                response = collector.collect(safe_query)
            except Exception:
                response = SearchProviderResult(SearchProviderStatus.NETWORK_ERROR, message="Nguồn thu thập dữ liệu gặp sự cố; không có dữ liệu mới được sử dụng.")
            collected_at = self.clock()
            if collected_at.tzinfo is None or collected_at.utcoffset() is None:
                collected_at = collected_at.replace(tzinfo=timezone.utc)
            statuses.append(
                PlatformCollectionStatus(
                    platform, response.status, response.message, collected_at,
                    dict(response.metadata) if isinstance(response.metadata, dict) else {},
                )
            )
            if response.status is not SearchProviderStatus.SUCCESS:
                continue
            for raw in response.evidences:
                normalized = normalizer.normalize(raw)
                if not normalized.is_valid or normalized.evidence is None:
                    continue
                validation = validator.validate(normalized.evidence, now=self.clock(), max_age_days=max_age_days)
                if not validation.is_valid:
                    continue
                metadata = dict(normalized.evidence.metadata)
                metadata.setdefault("platform", platform)
                records.append(replace(normalized.evidence, verification_status=validation.status, metadata=metadata))

        records = self._mark_explicit_conflicts(records)
        kept, aliases = self._deduplicate(records)
        result = MultiPlatformRetrievalResult(tuple(kept), tuple(statuses), aliases)
        self._cache[cache_key] = result
        return result

    @staticmethod
    def _mark_explicit_conflicts(records: list[Evidence]) -> list[Evidence]:
        ids = {record.evidence_id for record in records}
        conflicted: set[str] = set()
        for record in records:
            metadata = record.metadata if isinstance(record.metadata, dict) else {}
            references = metadata.get("conflicts_with", [])
            if not isinstance(references, (list, tuple, set)):
                continue
            related = set(references) & ids
            if related:
                conflicted.add(record.evidence_id)
                conflicted.update(related)
        return [replace(record, verification_status=EvidenceVerificationStatus.CONFLICTING) if record.evidence_id in conflicted else record for record in records]

    @staticmethod
    def _deduplicate(records: list[Evidence]) -> tuple[list[Evidence], dict[str, str]]:
        aliases: dict[str, str] = {}
        canonical_by_object: dict[int, Evidence] = {}
        remove: set[int] = set()
        for group in EvidenceDeduplicator.duplicate_groups(records):
            canonical_source = group[0]
            canonical_item = canonical_source
            canonical = canonical_item.evidence_id
            publisher_names: set[str] = set()
            statuses: set[str] = set()
            for duplicate in group[1:]:
                aliases[duplicate.evidence_id] = canonical
                remove.add(id(duplicate))
            for item in group:
                metadata = item.metadata if isinstance(item.metadata, dict) else {}
                stored_publishers = metadata.get("source_publishers", [])
                if isinstance(stored_publishers, (list, tuple, set)):
                    publisher_names.update(
                        " ".join(name.split())
                        for name in stored_publishers
                        if isinstance(name, str) and name.strip()
                    )
                publisher = metadata.get("publisher_name")
                if not isinstance(publisher, str) or not publisher.strip():
                    publisher = item.publisher
                if isinstance(publisher, str) and publisher.strip():
                    publisher_names.add(" ".join(publisher.split()))
                statuses.add(str(getattr(item.verification_status, "value", item.verification_status)).lower())
            metadata = dict(canonical_item.metadata or {})
            metadata["source_publishers"] = sorted(publisher_names, key=lambda name: (name.casefold(), name))
            metadata["duplicate_evidence_ids"] = sorted(
                item.evidence_id for item in group[1:]
            )
            if "conflicting" in statuses:
                canonical_item = replace(canonical_item, verification_status=EvidenceVerificationStatus.CONFLICTING)
            elif "stale" in statuses:
                canonical_item = replace(canonical_item, verification_status=EvidenceVerificationStatus.STALE)
            canonical_by_object[id(canonical_source)] = replace(canonical_item, metadata=metadata)
        return [
            canonical_by_object.get(id(record), record)
            for record in records
            if id(record) not in remove
        ], aliases
