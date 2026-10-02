import unittest

from app.services.context_engine.intent_resolver import intent_resolver
from app.services.context_engine.context_pruner import context_pruner
from app.services.context_engine.models import FollowUpIntentType
from app.services.context_engine.service import conversation_context_service


class ContextEngineTest(unittest.TestCase):
    def test_intent_resolver_detects_all_follow_up_types(self):
        # 1. Shorten
        intent, _ = intent_resolver.resolve_intent("Hãy viết ngắn gọn lại giúp mình")
        self.assertEqual(intent, FollowUpIntentType.SHORTEN)

        # 2. Expand
        intent, _ = intent_resolver.resolve_intent("Viết chi tiết hơn và sâu hơn về tính năng")
        self.assertEqual(intent, FollowUpIntentType.EXPAND)

        # 3. Change Tone
        intent, meta = intent_resolver.resolve_intent("Đổi giọng văn hài hước và trẻ trung hơn")
        self.assertEqual(intent, FollowUpIntentType.CHANGE_TONE)
        self.assertEqual(meta.get("target_tone"), "hài hước")

        # 4. Add CTA
        intent, _ = intent_resolver.resolve_intent("Thêm 3 CTA kêu gọi mua hàng")
        self.assertEqual(intent, FollowUpIntentType.ADD_CTA)

        # 5. Rewrite
        intent, _ = intent_resolver.resolve_intent("Viết lại bài khác đi bạn")
        self.assertEqual(intent, FollowUpIntentType.REWRITE)

        # 6. Multi Variation
        intent, meta = intent_resolver.resolve_intent("Cho tôi 5 phiên bản khác")
        self.assertEqual(intent, FollowUpIntentType.MULTI_VARIATION)
        self.assertEqual(meta.get("variation_count"), 5)

        # 7. Switch Platform
        intent, meta = intent_resolver.resolve_intent("Đổi sang TikTok giúp mình")
        self.assertEqual(intent, FollowUpIntentType.SWITCH_PLATFORM)
        self.assertEqual(meta.get("target_platform"), "tiktok")

        intent, meta = intent_resolver.resolve_intent("Chuyển qua Shopee nhé")
        self.assertEqual(intent, FollowUpIntentType.SWITCH_PLATFORM)
        self.assertEqual(meta.get("target_platform"), "shopee")

    def test_context_pruner_extracts_product_and_last_message(self):
        history = [
            {
                "role": "user",
                "content": "Tạo quảng cáo",
                "ad_brief": {
                    "product_name": "Kem chống nắng AdGen SunShield",
                    "description": "Chống nắng SPF 50+ PA++++, kiềm dầu 12h",
                    "price": "299.000đ",
                    "platform": "facebook",
                },
            },
            {
                "role": "assistant",
                "content": "Đây là bài quảng cáo Facebook cho Kem chống nắng...",
            },
        ]

        extracted = context_pruner.extract_product_from_history(history)
        self.assertEqual(extracted.product_name, "Kem chống nắng AdGen SunShield")
        self.assertEqual(extracted.price, "299.000đ")
        self.assertEqual(extracted.platform, "facebook")

        last_assistant = context_pruner.get_last_assistant_message(history)
        self.assertIn("Đây là bài quảng cáo Facebook", last_assistant)

    def test_conversation_context_service_flow(self):
        history = [
            {
                "role": "user",
                "content": "Viết quảng cáo Facebook cho son môi dưỡng ẩm",
                "ad_brief": {
                    "product_name": "Son dưỡng AdGen LipGlow",
                    "description": "Dưỡng ẩm hữu cơ, không chì",
                    "platform": "facebook",
                },
            },
            {
                "role": "assistant",
                "content": "Nội dung bài viết Facebook...",
            },
        ]

        # User asks to switch to TikTok
        follow_up = conversation_context_service.resolve_conversation_context(
            user_message="Đổi sang TikTok",
            history=history,
            current_prompt_type="facebook",
        )

        self.assertEqual(follow_up.intent, FollowUpIntentType.SWITCH_PLATFORM)
        self.assertEqual(follow_up.target_platform, "tiktok")
        self.assertEqual(follow_up.extracted_product.product_name, "Son dưỡng AdGen LipGlow")

        prompt_instruction = conversation_context_service.format_follow_up_prompt_instruction(follow_up)
        self.assertIn("SWITCH_PLATFORM", prompt_instruction)
        self.assertIn("TIKTOK", prompt_instruction)


if __name__ == "__main__":
    unittest.main()
