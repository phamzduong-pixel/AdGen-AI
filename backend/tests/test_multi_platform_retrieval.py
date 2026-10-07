from datetime import datetime, timedelta, timezone

from app.services.external_retrieval.evidence import Evidence, EvidenceSourceType
from app.services.external_retrieval.multi_platform import MultiPlatformRetrievalService
from app.services.external_retrieval.provider import SearchProviderResult, SearchProviderStatus

NOW = datetime(2026, 10, 5, tzinfo=timezone.utc)

class FakeCollector:
    def __init__(self, platform, result): self.platform, self.result, self.calls = platform, result, 0
    def collect(self, query): self.calls += 1; return self.result

def evidence(identifier, url='https://example.com/a', excerpt='signal', **metadata):
    return Evidence(identifier, identifier, url, 'Publisher', NOW, excerpt, EvidenceSourceType.PLATFORM_ANALYTICS, published_at=NOW, metadata=metadata)

def test_preserves_source_status_and_does_not_fake_evidence_on_failure():
    service = MultiPlatformRetrievalService([FakeCollector('youtube', SearchProviderResult(SearchProviderStatus.QUOTA_EXCEEDED, message='quota'))], clock=lambda: NOW)
    result = service.retrieve('running shoes')
    assert result.evidences == ()
    assert result.sources[0].status is SearchProviderStatus.QUOTA_EXCEEDED

def test_normalizes_platform_provenance_stale_dedup_and_refresh():
    fresh = evidence('a', excerpt='same')
    duplicate = evidence('b', url='https://mirror.example/b', excerpt='same')
    stale = Evidence('old', 'old', 'https://example.com/old', 'Publisher', NOW, 'old', EvidenceSourceType.PLATFORM_ANALYTICS, published_at=NOW-timedelta(days=31))
    collector = FakeCollector('youtube', SearchProviderResult(SearchProviderStatus.SUCCESS, evidences=(fresh, duplicate, stale)))
    service = MultiPlatformRetrievalService([collector], clock=lambda: NOW)
    result = service.retrieve('running shoes')
    assert [item.evidence_id for item in result.evidences] == ['a', 'old']
    assert result.duplicate_ids == {'b': 'a'}
    assert result.evidences[0].metadata['platform'] == 'youtube'
    assert result.evidences[1].verification_status.value == 'stale'
    assert service.retrieve('running shoes').from_cache is True
    assert collector.calls == 1
    assert service.retrieve('running shoes', refresh=True).from_cache is False
    assert collector.calls == 2

def test_marks_only_explicit_conflicts_not_semantic_guessing():
    left = evidence('left', excerpt='growth', conflicts_with=['right'])
    right = evidence('right', url='https://example.com/right', excerpt='decline')
    collector = FakeCollector('meta', SearchProviderResult(SearchProviderStatus.SUCCESS, evidences=(left, right)))
    result = MultiPlatformRetrievalService([collector], clock=lambda: NOW).retrieve('topic')
    assert result.evidences[0].verification_status.value == 'conflicting'
    assert result.evidences[1].verification_status.value == 'unverified'