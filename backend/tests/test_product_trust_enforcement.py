import types
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from app.services import ai_service
from app.services.product_trust.enforcement import (
    ASK_USER_RESPONSE,
    SAFE_SOFTENED_TEXT,
    ProductTrustPolicyError,
    enforce_product_trust,
)
from app.services.product_trust.models import (
    ClaimAssessment,
    ClaimAssessmentStatus,
    ClaimOrigin,
    ClaimRiskLevel,
    ProductClaim,
    ProductClaimType,
    RecommendedAction,
)


ASSESSMENT_TIME = datetime(2026, 10, 5, tzinfo=timezone.utc)


def pair(text, action):
    claim = ProductClaim(
        claim_id="product:description:0",
        claim_text=text,
        claim_type=ProductClaimType.DESCRIPTION,
        origin=ClaimOrigin.USER_PROVIDED,
        product_field="description",
    )
    return claim, ClaimAssessment(
        claim_id=claim.claim_id,
        status=ClaimAssessmentStatus.UNVERIFIED,
        risk_level=ClaimRiskLevel.HIGH if action != RecommendedAction.ALLOW else ClaimRiskLevel.NORMAL,
        recommended_action=action,
        assessed_at=ASSESSMENT_TIME,
    )


class FakeModels:
    def __init__(self, chunks):
        self.chunks = chunks

    def generate_content(self, **kwargs):
        return types.SimpleNamespace(text="".join(self.chunks))

    def generate_content_stream(self, **kwargs):
        return [types.SimpleNamespace(text=chunk) for chunk in self.chunks]


class ProductTrustEnforcementTests(unittest.TestCase):
    def test_priority_block_overrides_allow_and_soften(self):
        allowed = pair("Thiết kế nhỏ gọn", RecommendedAction.ALLOW)
        softened = pair("Pin dùng 60 ngày", RecommendedAction.SOFTEN)
        blocked = pair("Chữa khỏi bệnh đau cổ tay", RecommendedAction.BLOCK)

        with self.assertRaises(ProductTrustPolicyError):
            enforce_product_trust(
                "Thiết kế nhỏ gọn. Pin dùng 60 ngày. Chữa khỏi bệnh đau cổ tay.",
                (allowed, softened, blocked),
            )

    def test_soften_only_replaces_exact_assessed_claim(self):
        result = enforce_product_trust(
            "Thiết kế đẹp. Pin dùng 60 ngày cho nhu cầu hằng ngày.",
            (pair("Pin dùng 60 ngày", RecommendedAction.SOFTEN),),
        )

        self.assertIn("Thiết kế đẹp", result.content)
        self.assertIn(SAFE_SOFTENED_TEXT, result.content)
        self.assertNotIn("Pin dùng 60 ngày", result.content)

    def test_ask_user_replaces_risky_output_without_repeating_claim(self):
        claim_text = "Chữa khỏi bệnh đau cổ tay"
        result = enforce_product_trust(
            f"Sản phẩm {claim_text}.",
            (pair(claim_text, RecommendedAction.ASK_USER),),
        )

        self.assertEqual(result.content, ASK_USER_RESPONSE)
        self.assertNotIn(claim_text, result.content)

    def test_non_matching_claim_is_not_guessed_or_rewritten(self):
        content = "Sản phẩm hỗ trợ trải nghiệm thoải mái hơn."
        result = enforce_product_trust(
            content, (pair("Chữa khỏi bệnh đau cổ tay", RecommendedAction.BLOCK),)
        )

        self.assertEqual(result.content, content)

    def test_stream_buffers_and_blocks_before_any_chunk_is_emitted(self):
        claim_text = "Chữa khỏi bệnh đau cổ tay"
        models = FakeModels(["Mở đầu an toàn. ", claim_text])
        with patch.object(ai_service, "client", types.SimpleNamespace(models=models)), patch.object(
            ai_service.learning_dataset_service, "log_generation"
        ):
            generator = ai_service.stream_ai(
                [{"role": "user", "content": "Viết quảng cáo"}],
                product_claim_assessments=(pair(claim_text, RecommendedAction.BLOCK),),
            )
            with self.assertRaisesRegex(RuntimeError, "Product Trust blocked"):
                next(generator)

    def test_stream_keeps_valid_citation_after_softening(self):
        models = FakeModels(["Pin dùng 60 ngày [S1]."])
        with patch.object(ai_service, "client", types.SimpleNamespace(models=models)), patch.object(
            ai_service.learning_dataset_service, "log_generation"
        ):
            output = "".join(
                ai_service.stream_ai(
                    [{"role": "user", "content": "Viết quảng cáo"}],
                    product_claim_assessments=(pair("Pin dùng 60 ngày", RecommendedAction.SOFTEN),),
                )
            )

        self.assertIn(SAFE_SOFTENED_TEXT, output)
        self.assertIn("[S1]", output)


if __name__ == "__main__":
    unittest.main()
