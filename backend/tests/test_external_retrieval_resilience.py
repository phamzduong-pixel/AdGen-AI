"""CP-3 resilience tests for provider failures before generation."""

import types
import unittest
from unittest.mock import patch

from app.services import ai_service
from app.services.external_retrieval.evidence_context import build_retrieval_fallback_response
from app.services.external_retrieval.evidence import Evidence, EvidenceSourceType, EvidenceVerificationStatus
from app.services.external_retrieval.provider import SearchProviderResult, SearchProviderStatus
from app.services.external_retrieval.retrieval_service import ExternalRetrievalService
from app.services.output_validator.models import ValidationResult


class RaisingProvider:
    def search(self, query, *, limit=None):
        raise RuntimeError("provider implementation failure")


class FakeModels:
    def generate_content_stream(self, **kwargs):
        return [types.SimpleNamespace(text="Generation still streams.")]


class ExternalRetrievalResilienceTests(unittest.TestCase):
    def test_unexpected_provider_failure_becomes_safe_status(self):
        outcome = ExternalRetrievalService(RaisingProvider()).retrieve(
            "Research the latest skincare market trends"
        )

        self.assertTrue(outcome.was_requested)
        self.assertEqual(outcome.status, SearchProviderStatus.NETWORK_ERROR)

    def test_failure_status_does_not_break_ai_streaming(self):
        outcome = ExternalRetrievalService(RaisingProvider()).retrieve(
            "Research the latest skincare market trends"
        )
        valid = ValidationResult(
            is_valid=True,
            sanitized_content="Generation still streams.",
            issues=[],
        )
        with patch.object(
            ai_service,
            "client",
            types.SimpleNamespace(models=FakeModels()),
        ), patch.object(
            ai_service.output_validation_service,
            "validate_and_sanitize",
            return_value=valid,
        ):
            output = "".join(
                ai_service.stream_ai(
                    [{"role": "user", "content": "Research the latest skincare market trends"}],
                    external_retrieval_requested=True,
                    external_retrieval_result=outcome.provider_result,
                )
            )

        self.assertIn("status: network_error", output)
        self.assertIn("source-backed conclusions", output)

    def test_all_unusable_statuses_have_deterministic_no_evidence_fallback(self):
        statuses = (
            SearchProviderStatus.SUCCESS,
            SearchProviderStatus.EMPTY,
            SearchProviderStatus.NOT_CONFIGURED,
            SearchProviderStatus.QUOTA_EXCEEDED,
            SearchProviderStatus.TIMEOUT,
            SearchProviderStatus.NETWORK_ERROR,
            SearchProviderStatus.HTTP_ERROR,
            SearchProviderStatus.INVALID_RESPONSE,
        )
        for provider_status in statuses:
            with self.subTest(status=provider_status):
                fallback = build_retrieval_fallback_response(
                    SearchProviderResult(status=provider_status)
                )
                self.assertIsNotNone(fallback)
                self.assertNotIn("[S", fallback)
                self.assertIn("source-backed", fallback)

    def test_stale_or_conflicting_only_evidence_uses_current_data_fallback(self):
        for evidence_status in (
            EvidenceVerificationStatus.STALE,
            EvidenceVerificationStatus.CONFLICTING,
        ):
            with self.subTest(status=evidence_status):
                result = SearchProviderResult(
                    status=SearchProviderStatus.SUCCESS,
                    evidences=(
                        Evidence(
                            evidence_id=f"{evidence_status.value}-evidence",
                            title="Historical source",
                            source_url="https://example.com/historical",
                            publisher="Example",
                            retrieved_at="2026-10-05T12:00:00Z",
                            excerpt="Historical evidence.",
                            source_type=EvidenceSourceType.SEARCH_RESULT,
                            verification_status=evidence_status,
                        ),
                    ),
                )
                fallback = build_retrieval_fallback_response(result)
                self.assertIsNotNone(fallback)
                self.assertIn("cannot be presented as current data", fallback)

if __name__ == "__main__":
    unittest.main()
