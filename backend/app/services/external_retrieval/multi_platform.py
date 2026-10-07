"""Stage-2 multi-platform orchestration; adapters are injected and never live by default."""
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Protocol

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
        self._cache: dict[str, MultiPlatformRetrievalResult] = {}

    def retrieve(self, query: str, *, refresh: bool = False, max_age_days: int = 30) -> MultiPlatformRetrievalResult:
        safe_query = " ".join((query or "").split())
        if not safe_query:
            return MultiPlatformRetrievalResult((), ())
        if not refresh and safe_query in self._cache:
            cached = self._cache[safe_query]
            return replace(cached, from_cache=True)

        statuses: list[PlatformCollectionStatus] = []
        records: list[Evidence] = []
        normalizer, validator = EvidenceNormalizer(), EvidenceValidator()
        for collector in self.collectors:
            platform = str(getattr(collector, "platform", collector.__class__.__name__)).strip() or "unknown"
            try:
                response = collector.collect(safe_query)
            except Exception:
                response = SearchProviderResult(SearchProviderStatus.NETWORK_ERROR, message="Nguồn thu thập dữ liệu gặp sự cố; không có dữ liệu mới được sử dụng.")
            statuses.append(PlatformCollectionStatus(platform, response.status, response.message))
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
        self._cache[safe_query] = result
        return result

    @staticmethod
    def _mark_explicit_conflicts(records: list[Evidence]) -> list[Evidence]:
        ids = {record.evidence_id for record in records}
        conflicted = {record.evidence_id for record in records if set(record.metadata.get("conflicts_with", [])) & ids}
        return [replace(record, verification_status=EvidenceVerificationStatus.CONFLICTING) if record.evidence_id in conflicted else record for record in records]

    @staticmethod
    def _deduplicate(records: list[Evidence]) -> tuple[list[Evidence], dict[str, str]]:
        aliases: dict[str, str] = {}
        remove: set[str] = set()
        for group in EvidenceDeduplicator.duplicate_groups(records):
            canonical = group[0].evidence_id
            for duplicate in group[1:]:
                aliases[duplicate.evidence_id] = canonical
                remove.add(duplicate.evidence_id)
        return [record for record in records if record.evidence_id not in remove], aliases
