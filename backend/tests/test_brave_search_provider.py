"""CP-2 tests for the isolated Brave Web Search adapter."""

import unittest
from datetime import datetime, timezone

import httpx

from app.services.external_retrieval.brave_search import BraveSearchProvider
from app.services.external_retrieval.provider import SearchProviderResult, SearchProviderStatus
from app.services.external_retrieval.retrieval_service import ExternalRetrievalService


class RecordingProvider:
    def __init__(self, result=None):
        self.calls = []
        self.result = result or SearchProviderResult(status=SearchProviderStatus.EMPTY)

    def search(self, query, *, limit=None):
        self.calls.append((query, limit))
        return self.result


class BraveSearchProviderTests(unittest.TestCase):
    fixed_now = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)

    def provider(self, handler, **overrides):
        options = {
            "api_key": "brave-test-secret",
            "transport": httpx.MockTransport(handler),
            "clock": lambda: self.fixed_now,
            "timeout_seconds": 1,
            "max_results": 3,
            "max_excerpt_chars": 80,
            "max_retries": 0,
        }
        options.update(overrides)
        return BraveSearchProvider(**options)

    @staticmethod
    def result(title="Trend report", url="https://example.com/report", description="Demand is increasing."):
        return {"title": title, "url": url, "description": description}

    def test_valid_response_becomes_unverified_evidence(self):
        provider = self.provider(
            lambda request: httpx.Response(
                200,
                json={"web": {"results": [self.result()]}},
                request=request,
            )
        )

        response = provider.search("skincare trend Vietnam")

        self.assertEqual(response.status, SearchProviderStatus.SUCCESS)
        self.assertEqual(len(response.evidences), 1)
        evidence = response.evidences[0]
        self.assertEqual(evidence.source_url, "https://example.com/report")
        self.assertEqual(evidence.retrieved_at, self.fixed_now)
        self.assertEqual(evidence.verification_status.value, "unverified")
        self.assertIsNone(evidence.confidence)
        self.assertEqual(evidence.metadata["provider"], "brave_search")

    def test_duplicate_results_are_removed(self):
        provider = self.provider(
            lambda request: httpx.Response(
                200,
                json={
                    "web": {
                        "results": [
                            self.result(),
                            self.result(
                                title="Duplicate article",
                                url="https://another.example/duplicate",
                            ),
                        ]
                    }
                },
                request=request,
            )
        )

        response = provider.search("skincare trend Vietnam")

        self.assertEqual(response.status, SearchProviderStatus.SUCCESS)
        self.assertEqual(len(response.evidences), 1)
        self.assertEqual(response.metadata["duplicates_removed"], 1)

    def test_empty_results_are_not_provider_errors(self):
        provider = self.provider(
            lambda request: httpx.Response(
                200,
                json={"web": {"results": []}},
                request=request,
            )
        )

        response = provider.search("unknown niche")

        self.assertEqual(response.status, SearchProviderStatus.EMPTY)
        self.assertFalse(response.is_error)

    def test_http_quota_timeout_and_malformed_responses_are_classified(self):
        quota_provider = self.provider(
            lambda request: httpx.Response(429, request=request)
        )
        self.assertEqual(
            quota_provider.search("query").status,
            SearchProviderStatus.QUOTA_EXCEEDED,
        )

        timeout_calls = []

        def timeout_handler(request):
            timeout_calls.append(request)
            raise httpx.ReadTimeout("timed out", request=request)

        timeout_provider = self.provider(timeout_handler, max_retries=1)
        self.assertEqual(
            timeout_provider.search("query").status,
            SearchProviderStatus.TIMEOUT,
        )
        self.assertEqual(len(timeout_calls), 2)

        malformed_provider = self.provider(
            lambda request: httpx.Response(
                200,
                json={"web": {"results": "not-a-list"}},
                request=request,
            )
        )
        self.assertEqual(
            malformed_provider.search("query").status,
            SearchProviderStatus.INVALID_RESPONSE,
        )

    def test_http_error_does_not_expose_api_key(self):
        provider = self.provider(
            lambda request: httpx.Response(500, request=request)
        )

        response = provider.search("query")

        self.assertEqual(response.status, SearchProviderStatus.HTTP_ERROR)
        self.assertNotIn("brave-test-secret", repr(response))
        self.assertNotIn("brave-test-secret", response.message or "")

    def test_requested_limit_is_clamped_and_applied_to_http_request(self):
        captured = {}

        def handler(request):
            captured["count"] = request.url.params.get("count")
            return httpx.Response(
                200,
                json={"web": {"results": [self.result()] * 5}},
                request=request,
            )

        provider = self.provider(handler)
        response = provider.search("query", limit=99)

        self.assertEqual(captured["count"], "3")
        self.assertLessEqual(len(response.evidences), 3)

    def test_missing_api_key_does_not_attempt_http_call(self):
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(200, json={"web": {"results": []}}, request=request)

        provider = BraveSearchProvider(
            api_key="",
            transport=httpx.MockTransport(handler),
        )
        response = provider.search("query")

        self.assertEqual(response.status, SearchProviderStatus.NOT_CONFIGURED)
        self.assertEqual(calls, [])

    def test_intent_gate_prevents_provider_call_for_normal_ads(self):
        fake_provider = RecordingProvider()
        service = ExternalRetrievalService(fake_provider)

        result = service.retrieve("Write five TikTok ad headlines for this product")

        self.assertFalse(result.was_requested)
        self.assertIsNone(result.provider_result)
        self.assertEqual(fake_provider.calls, [])

    def test_gate_allows_explicit_market_research(self):
        fake_provider = RecordingProvider(
            SearchProviderResult(status=SearchProviderStatus.EMPTY)
        )
        service = ExternalRetrievalService(fake_provider)

        result = service.retrieve(
            "Research the latest skincare market trends in Vietnam",
            limit=2,
        )

        self.assertTrue(result.was_requested)
        self.assertEqual(result.status, SearchProviderStatus.EMPTY)
        self.assertEqual(len(fake_provider.calls), 1)
        self.assertEqual(fake_provider.calls[0][1], 2)


if __name__ == "__main__":
    unittest.main()
