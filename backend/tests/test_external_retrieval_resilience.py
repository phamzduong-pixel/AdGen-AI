"""CP-3 resilience tests for provider failures before generation."""

import types
import unittest
from unittest.mock import patch

from app.services import ai_service
from app.services.external_retrieval.provider import SearchProviderStatus
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

        self.assertEqual(output, "Generation still streams.")


if __name__ == "__main__":
    unittest.main()
