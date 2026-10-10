"""Gate-aware retrieval orchestration without Chat or prompt integration."""

from dataclasses import dataclass

from app.services.external_retrieval.evidence import EvidenceNormalizer, EvidenceValidator
from app.services.external_retrieval.intent_gate import (
    ExternalRetrievalIntentGate,
    RetrievalIntent,
    external_retrieval_intent_gate,
)
from app.services.external_retrieval.provider import (
    SearchProvider,
    SearchProviderResult,
    SearchProviderStatus,
)


@dataclass(frozen=True)
class ExternalRetrievalResult:
    """The boundary result for CP-2/CP-3; evidence is not persisted here."""

    intent: RetrievalIntent
    provider_result: SearchProviderResult | None

    @property
    def status(self) -> SearchProviderStatus | None:
        return self.provider_result.status if self.provider_result else None

    @property
    def was_requested(self) -> bool:
        return self.intent.should_retrieve


class ExternalRetrievalService:
    """Call a provider only after the CP-0 intent gate explicitly allows it."""

    def __init__(
        self,
        provider: SearchProvider,
        *,
        intent_gate: ExternalRetrievalIntentGate = external_retrieval_intent_gate,
    ):
        self.provider = provider
        self.intent_gate = intent_gate

    def retrieve(
        self,
        user_request: str,
        *,
        query: str | None = None,
        limit: int | None = None,
    ) -> ExternalRetrievalResult:
        intent = self.intent_gate.decide(user_request)
        if not intent.should_retrieve:
            return ExternalRetrievalResult(intent=intent, provider_result=None)

        try:
            provider_result = self.provider.search(query or user_request, limit=limit)
        except Exception:
            provider_result = SearchProviderResult(
                status=SearchProviderStatus.NETWORK_ERROR,
                message="Nguồn tìm kiếm dữ liệu xu hướng đang tạm thời không khả dụng.",
            )
        return ExternalRetrievalResult(
            intent=intent,
            provider_result=self._sanitize_provider_result(provider_result),
        )

    @staticmethod
    def _sanitize_provider_result(
        provider_result: SearchProviderResult,
    ) -> SearchProviderResult:
        """Keep only evidence that satisfies the existing evidence contract."""
        if provider_result.status is not SearchProviderStatus.SUCCESS:
            if provider_result.evidences:
                return SearchProviderResult(
                    status=provider_result.status,
                    message=provider_result.message,
                    metadata=dict(provider_result.metadata or {}),
                )
            return provider_result

        normalizer = EvidenceNormalizer()
        validator = EvidenceValidator()
        if not provider_result.evidences:
            return provider_result
        valid_evidence = []
        malformed_count = 0
        for evidence in provider_result.evidences:
            try:
                normalized = normalizer.normalize(evidence)
                if not normalized.is_valid or normalized.evidence is None:
                    malformed_count += 1
                    continue
                validation = validator.validate(normalized.evidence)
            except Exception:
                malformed_count += 1
                continue
            if not validation.is_valid:
                malformed_count += 1
                continue
            valid_evidence.append(normalized.evidence)

        metadata = dict(provider_result.metadata or {})
        if malformed_count:
            metadata["malformed_evidence"] = malformed_count
        if not valid_evidence:
            return SearchProviderResult(
                status=SearchProviderStatus.INVALID_RESPONSE,
                message="Search provider returned no usable evidence.",
                metadata=metadata,
            )
        return SearchProviderResult(
            status=SearchProviderStatus.SUCCESS,
            evidences=tuple(valid_evidence),
            message=provider_result.message,
            metadata=metadata,
        )
