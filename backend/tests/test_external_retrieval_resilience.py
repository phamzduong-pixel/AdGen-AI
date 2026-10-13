"""CP-3 resilience tests for provider failures before generation."""

import types
import unittest
from unittest.mock import patch

from app.services import ai_service
from app.services.external_retrieval.evidence_context import (
    build_evidence_prompt_context,
    build_retrieval_fallback_response,
)
from app.services.external_retrieval.evidence import Evidence, EvidenceSourceType, EvidenceVerificationStatus
from app.services.external_retrieval.provider import SearchProviderResult, SearchProviderStatus
from app.services.external_retrieval.retrieval_service import ExternalRetrievalService
from app.services.output_validator.models import ValidationResult


class RaisingProvider:
    def search(self, query, *, limit=None):
        raise RuntimeError("provider implementation failure")


class UnconfiguredProvider:
    def search(self, query, *, limit=None):
        return SearchProviderResult(status=SearchProviderStatus.NOT_CONFIGURED)


class ReturningProvider:
    def __init__(self, result):
        self.result = result

    def search(self, query, *, limit=None):
        return self.result


class FakeModels:
    def generate_content_stream(self, **kwargs):
        return [types.SimpleNamespace(text="Generation still streams.")]


class FakeModelsWithAnswer:
    def __init__(self, answer):
        self.answer = answer

    def generate_content(self, **kwargs):
        return types.SimpleNamespace(text=self.answer)

    def generate_content_stream(self, **kwargs):
        return [types.SimpleNamespace(text=self.answer)]


class ExternalRetrievalResilienceTests(unittest.TestCase):
    def _model_answer(self, answer, user_content, provider_result, *, streaming):
        valid = ValidationResult(is_valid=True, sanitized_content=answer, issues=[])
        with patch.object(
            ai_service, "client", types.SimpleNamespace(models=FakeModelsWithAnswer(answer))
        ), patch.object(
            ai_service.output_validation_service,
            "validate_and_sanitize",
            return_value=valid,
        ), patch.object(ai_service, "_log_generation"):
            kwargs = {
                "external_retrieval_requested": True,
                "external_retrieval_result": provider_result,
            }
            history = [{"role": "user", "content": user_content}]
            if streaming:
                return "".join(ai_service.stream_ai(history, **kwargs))
            return ai_service.ask_ai(history, **kwargs)

    def test_entity_question_without_provider_can_use_cautious_model_answer(self):
        outcome = ExternalRetrievalService(UnconfiguredProvider()).retrieve(
            "Bạn có biết website của Bà Tuyết không?"
        )
        self.assertTrue(outcome.was_requested)
        self.assertEqual(outcome.status, SearchProviderStatus.NOT_CONFIGURED)
        self.assertTrue(outcome.provider_result.metadata["prior_knowledge_fallback"])
        self.assertIsNone(build_retrieval_fallback_response(outcome.provider_result))
        context = build_evidence_prompt_context(outcome.provider_result).text
        self.assertIn("do not provide or claim an official URL", context)
        self.assertIn("Do not redirect to marketing features", context)

        valid = ValidationResult(is_valid=True, sanitized_content="Tôi chưa rõ website chính thức.", issues=[])
        with patch.object(ai_service, "client", types.SimpleNamespace(models=FakeModels())), patch.object(
            ai_service.output_validation_service,
            "validate_and_sanitize",
            return_value=valid,
        ), patch.object(ai_service, "_log_generation"):
            output = "".join(ai_service.stream_ai(
                [{"role": "user", "content": "Bạn có biết website của Bà Tuyết không?"}],
                external_retrieval_requested=True,
                external_retrieval_result=outcome.provider_result,
            ))
        self.assertEqual(output, "Tôi chưa rõ website chính thức.")

    def test_unsourced_website_url_is_blocked_before_streaming(self):
        outcome = ExternalRetrievalService(UnconfiguredProvider()).retrieve(
            "Trang web của thương hiệu X là gì?"
        )
        output = self._model_answer(
            "Trang web là https://invented.example; thương hiệu bán hàng trực tuyến.",
            "Trang web của thương hiệu X là gì?",
            outcome.provider_result,
            streaming=True,
        )
        self.assertNotIn("invented.example", output)
        self.assertIn("đường dẫn không có nguồn", output)
        self.assertIn("thương hiệu bán hàng trực tuyến", output)

    def test_entity_question_provider_error_still_allows_cautious_answer(self):
        outcome = ExternalRetrievalService(RaisingProvider()).retrieve(
            "Bạn có biết sản phẩm X được bán ở đâu không?"
        )
        self.assertEqual(outcome.status, SearchProviderStatus.NETWORK_ERROR)
        self.assertTrue(outcome.provider_result.metadata["prior_knowledge_fallback"])
        self.assertIsNone(build_retrieval_fallback_response(outcome.provider_result))

    def test_unsourced_website_url_is_blocked_in_non_stream_response(self):
        outcome = ExternalRetrievalService(UnconfiguredProvider()).retrieve(
            "Trang web của thương hiệu X là gì?"
        )
        output = self._model_answer(
            "Trang web là https://invented.example; thương hiệu bán hàng trực tuyến.",
            "Trang web của thương hiệu X là gì?",
            outcome.provider_result,
            streaming=False,
        )
        self.assertNotIn("invented.example", output)
        self.assertIn("đường dẫn không có nguồn", output)
        self.assertIn("thương hiệu bán hàng trực tuyến", output)

    def test_user_url_email_and_plain_domain_are_preserved_in_both_paths(self):
        user_content = "Website của X là https://provided.example/path; bạn biết gì thêm?"
        outcome = ExternalRetrievalService(UnconfiguredProvider()).retrieve(user_content)
        answer = (
            "Bạn đã cung cấp https://provided.example/path. "
            "Email là support@example.com; tên miền example.org chỉ được nhắc trong văn bản."
        )
        for streaming in (False, True):
            with self.subTest(streaming=streaming):
                output = self._model_answer(
                    answer, user_content, outcome.provider_result, streaming=streaming
                )
                self.assertEqual(output, answer)

    def test_retrieved_evidence_url_is_preserved_in_both_paths(self):
        evidence = Evidence(
            evidence_id="website-source",
            title="Website source",
            source_url="https://source.example/official",
            publisher="Example",
            retrieved_at="2026-10-05T12:00:00Z",
            excerpt="Search result for a website.",
            source_type=EvidenceSourceType.SEARCH_RESULT,
        )
        result = SearchProviderResult(
            status=SearchProviderStatus.SUCCESS,
            evidences=(evidence,),
        )
        outcome = ExternalRetrievalService(ReturningProvider(result)).retrieve(
            "Website của X là gì?"
        )
        self.assertTrue(outcome.provider_result.metadata["entity_lookup"])
        self.assertNotIn("prior_knowledge_fallback", outcome.provider_result.metadata)
        answer = "Nguồn tìm thấy: https://source.example/official"
        for streaming in (False, True):
            with self.subTest(streaming=streaming):
                output = self._model_answer(
                    answer, "Website của X là gì?", outcome.provider_result,
                    streaming=streaming,
                )
                self.assertEqual(output, answer)
                invented = self._model_answer(
                    "Nguồn tìm thấy: https://invented.example/official",
                    "Website của X là gì?", outcome.provider_result,
                    streaming=streaming,
                )
                self.assertNotIn("invented.example", invented)
                self.assertIn("đường dẫn chưa được xác minh", invented)

    def test_unsourced_markdown_link_keeps_label_without_broken_link(self):
        outcome = ExternalRetrievalService(UnconfiguredProvider()).retrieve(
            "Website của X là gì?"
        )
        answer = "Tham khảo [trang chủ](https://invented.example) để xem sản phẩm."
        for streaming in (False, True):
            with self.subTest(streaming=streaming):
                output = self._model_answer(
                    answer, "Website của X là gì?", outcome.provider_result,
                    streaming=streaming,
                )
                self.assertIn("trang chủ [đường dẫn chưa được xác minh]", output)
                self.assertIn("để xem sản phẩm", output)
                self.assertNotIn("invented.example", output)

    def test_normal_marketing_request_keeps_provider_and_fallback_off(self):
        for request in (
            "Viết quảng cáo cho website của X",
            "Cho tôi một caption về website của X.",
            "Mô tả sản phẩm X được bán ở đâu.",
            "Viết email marketing cho website của X",
            "Làm nội dung SEO cho website của X",
            "Kịch bản video giới thiệu website của X",
        ):
            with self.subTest(request=request):
                outcome = ExternalRetrievalService(RaisingProvider()).retrieve(request)
                self.assertFalse(outcome.was_requested)
                self.assertIsNone(outcome.provider_result)

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
