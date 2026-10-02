import unittest

from app.services.context_engine.models import FollowUpIntentType
from app.services.context_engine.service import conversation_context_service
from app.services.output_validator.models import ValidationErrorType
from app.services.output_validator.service import output_validation_service
from app.services.product_aware.models import (
    AudienceProfile,
    CampaignObjectiveType,
    ProductAwareContext,
    ProductProfile,
)
from app.services.product_aware.service import product_aware_engine
from app.services.prompt_service import build_system_prompt


class FullAiQualityPipelineTest(unittest.TestCase):
    def setUp(self):
        self.sample_product = ProductProfile(
            name="Khóa Học Tiếng Anh Giao Tiếp Thực Chiến AdGen Talk",
            category="Giáo dục & Đào tạo",
            description="Khóa học online 1-1 giúp người đi làm tự tin giao tiếp tiếng Anh công sở trong 3 tháng",
            key_features=["Học 1 kèm 1 linh hoạt", "Giảng viên bản xứ & trợ giảng Việt", "Ứng dụng luyện phát âm AI"],
            key_benefits=["Tự tin thuyết trình và họp với sếp nước ngoài", "Tăng cơ hội thăng tiến và mức lương"],
            usp="Lộ trình cá nhân hóa 100% theo ngành nghề của học viên",
            price="4.500.000 VNĐ / Khóa",
            offer="Tặng bộ tài liệu 1000 mẫu câu tiếng Anh thương mại",
            forbidden_claims=["Cam kết 100% đạt IELTS 8.0 sau 1 tháng"],
        )
        self.audience = AudienceProfile(
            persona_name="Người đi làm 24-35 tuổi",
            pain_points=["Sợ nói sai, ngại giao tiếp", "Không có thời gian đến trung tâm cố định"],
            desires=["Nói trôi chảy, phản xạ tự nhiên"],
        )

    def test_four_platforms_distinct_characteristics(self):
        platforms = ["facebook", "tiktok", "google_ads", "instagram"]
        outputs = {}

        for p in platforms:
            ctx = ProductAwareContext(
                product=self.sample_product,
                platform=p,
                audience=self.audience,
                objective=CampaignObjectiveType.LEAD_GENERATION,
            )
            out = product_aware_engine.build_full_context(ctx)
            outputs[p] = out

            # Basic validations
            self.assertIn("Khóa Học Tiếng Anh Giao Tiếp Thực Chiến AdGen Talk", out)
            self.assertIn("4.500.000 VNĐ / Khóa", out)
            self.assertIn("STRICT GROUNDING", out)

        # Platform specific checks
        self.assertIn("PAS", outputs["facebook"])
        self.assertIn("Timeline", outputs["tiktok"])
        self.assertIn("Headlines: <= 30", outputs["google_ads"])
        self.assertIn("Visual Hook", outputs["instagram"])

    def test_pipeline_follow_up_transformations(self):
        history = [
            {
                "role": "user",
                "content": "Viết quảng cáo Facebook",
                "ad_brief": {
                    "product_name": "Khóa Học AdGen Talk",
                    "description": "Tiếng Anh giao tiếp",
                    "platform": "facebook",
                },
            },
            {
                "role": "assistant",
                "content": "Đây là bài viết dài trên Facebook...",
            },
        ]

        # 1. Shorten
        res_shorten = conversation_context_service.resolve_conversation_context(
            user_message="Viết ngắn hơn giúp mình",
            history=history,
        )
        self.assertEqual(res_shorten.intent, FollowUpIntentType.SHORTEN)

        # 2. Change Tone
        res_tone = conversation_context_service.resolve_conversation_context(
            user_message="Đổi giọng văn hài hước hơn",
            history=history,
        )
        self.assertEqual(res_tone.intent, FollowUpIntentType.CHANGE_TONE)
        self.assertEqual(res_tone.target_tone, "hài hước")

        # 3. Add CTA
        res_cta = conversation_context_service.resolve_conversation_context(
            user_message="Thêm lời kêu gọi hành động đăng ký dùng thử",
            history=history,
        )
        self.assertEqual(res_cta.intent, FollowUpIntentType.ADD_CTA)

        # 4. Change Platform
        res_platform = conversation_context_service.resolve_conversation_context(
            user_message="Đổi sang TikTok",
            history=history,
        )
        self.assertEqual(res_platform.intent, FollowUpIntentType.SWITCH_PLATFORM)
        self.assertEqual(res_platform.target_platform, "tiktok")

    def test_pipeline_missing_product_info_handling(self):
        empty_product = ProductProfile(name="", description="")
        ctx = ProductAwareContext(
            product=empty_product,
            platform="facebook",
        )
        out = product_aware_engine.build_full_context(ctx)
        self.assertIn("STRICT GROUNDING", out)
        self.assertIn("Nếu thiếu thông tin cần thiết", out)

    def test_pipeline_invalid_response_and_api_error_resilience(self):
        # 1. Empty AI response
        val_empty = output_validation_service.validate_and_sanitize("", platform="facebook")
        self.assertFalse(val_empty.is_valid)
        self.assertTrue(val_empty.auto_repaired)
        self.assertIn("NỘI DUNG CHƯA ĐỦ", val_empty.sanitized_content)

        # 2. API error fallback
        val_fallback = output_validation_service.generate_fallback_response(
            error_type=ValidationErrorType.API_ERROR,
            platform="tiktok",
        )
        self.assertIn("THÔNG BÁO HỆ THỐNG", val_fallback)
        self.assertIn("TIKTOK", val_fallback)


if __name__ == "__main__":
    unittest.main()
