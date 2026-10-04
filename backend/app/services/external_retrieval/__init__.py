"""Contracts and adapters for optional external retrieval."""

from app.services.external_retrieval.brave_search import BraveSearchProvider
from app.services.external_retrieval.evidence import (
    Evidence,
    EvidenceDeduplicator,
    EvidenceIssue,
    EvidenceIssueCode,
    EvidenceNormalizationResult,
    EvidenceNormalizer,
    EvidenceSourceType,
    EvidenceValidationResult,
    EvidenceValidator,
    EvidenceVerificationStatus,
)
from app.services.external_retrieval.intent_gate import (
    ExternalRetrievalDecision,
    ExternalRetrievalIntentGate,
    RetrievalIntent,
    external_retrieval_intent_gate,
)
from app.services.external_retrieval.provider import (
    SearchProvider,
    SearchProviderResult,
    SearchProviderStatus,
)
from app.services.external_retrieval.retrieval_service import (
    ExternalRetrievalResult,
    ExternalRetrievalService,
)

__all__ = [
    "BraveSearchProvider",
    "Evidence",
    "EvidenceDeduplicator",
    "EvidenceIssue",
    "EvidenceIssueCode",
    "EvidenceNormalizationResult",
    "EvidenceNormalizer",
    "EvidenceSourceType",
    "EvidenceValidationResult",
    "EvidenceValidator",
    "EvidenceVerificationStatus",
    "ExternalRetrievalDecision",
    "ExternalRetrievalIntentGate",
    "ExternalRetrievalResult",
    "ExternalRetrievalService",
    "RetrievalIntent",
    "SearchProvider",
    "SearchProviderResult",
    "SearchProviderStatus",
    "external_retrieval_intent_gate",
]
