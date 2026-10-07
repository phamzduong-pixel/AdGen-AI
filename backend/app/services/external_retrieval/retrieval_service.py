"""Gate-aware retrieval orchestration without Chat or prompt integration."""

from dataclasses import dataclass

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
        return ExternalRetrievalResult(intent=intent, provider_result=provider_result)
