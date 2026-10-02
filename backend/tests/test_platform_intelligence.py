import unittest

from app.services.platform_intelligence.models import PlatformId
from app.services.platform_intelligence.registry import PLATFORM_SPECIFICATIONS
from app.services.platform_intelligence.service import (
    PlatformIntelligenceService,
    platform_intelligence_service,
)
from app.services.prompt_service import (
    build_system_prompt,
    get_specialized_prompt,
    get_supported_prompt_types,
    is_supported_prompt_type,
    normalize_prompt_type,
)


class PlatformIntelligenceTest(unittest.TestCase):
    def test_all_nine_required_platforms_present_in_specifications(self):
        expected_platforms = [
            PlatformId.FACEBOOK,
            PlatformId.INSTAGRAM,
            PlatformId.TIKTOK,
            PlatformId.GOOGLE_ADS,
            PlatformId.YOUTUBE,
            PlatformId.SHOPEE,
            PlatformId.EMAIL,
            PlatformId.LANDING_PAGE,
            PlatformId.SEO,
        ]
        for pid in expected_platforms:
            self.assertIn(pid, PLATFORM_SPECIFICATIONS)
            spec = PLATFORM_SPECIFICATIONS[pid]
            self.assertEqual(spec.platform_id, pid)
            self.assertTrue(len(spec.display_name) > 0)
            self.assertTrue(len(spec.primary_objective) > 0)
            self.assertTrue(len(spec.recommended_tones) > 0)
            self.assertTrue(len(spec.structure.primary_sections) > 0)
            self.assertTrue(len(spec.hook_guideline.recommended_types) > 0)
            self.assertTrue(len(spec.cta_guideline.primary_actions) > 0)
            self.assertTrue(len(spec.constraints) > 0)
            self.assertTrue(len(spec.best_practices) > 0)

    def test_platform_service_lookup_and_normalization(self):
        self.assertTrue(platform_intelligence_service.is_valid_platform("facebook"))
        self.assertTrue(platform_intelligence_service.is_valid_platform("youtube"))
        self.assertTrue(platform_intelligence_service.is_valid_platform("tiktok"))
        self.assertTrue(platform_intelligence_service.is_valid_platform("google_ads"))
        self.assertFalse(platform_intelligence_service.is_valid_platform("unknown_platform"))

        spec = platform_intelligence_service.get_specification("youtube")
        self.assertIsNotNone(spec)
        self.assertEqual(spec.platform_id, PlatformId.YOUTUBE)

    def test_format_platform_context(self):
        context = platform_intelligence_service.format_platform_context("tiktok")
        self.assertIn("TIKTOK", context)
        self.assertIn("Mục tiêu nền tảng", context)
        self.assertIn("Quy tắc Hook", context)
        self.assertIn("Ràng buộc kỹ thuật", context)

        empty_context = platform_intelligence_service.format_platform_context("non_existent")
        self.assertEqual(empty_context, "")

    def test_prompt_service_integration_with_platforms(self):
        supported = get_supported_prompt_types()
        for p in [
            "facebook",
            "instagram",
            "tiktok",
            "google_ads",
            "youtube",
            "shopee",
            "email",
            "landing_page",
            "seo",
        ]:
            self.assertIn(p, supported)
            self.assertTrue(is_supported_prompt_type(p))

        self.assertEqual(normalize_prompt_type("yt"), "youtube")
        self.assertEqual(normalize_prompt_type("shorts"), "youtube")
        self.assertEqual(normalize_prompt_type("gads"), "google_ads")
        self.assertEqual(normalize_prompt_type("ecommerce"), "shopee")

        prompt = build_system_prompt(prompt_type="tiktok")
        self.assertIn("TIKTOK", prompt)
        self.assertIn("PLATFORM INTELLIGENCE", prompt)
        self.assertIn("VERIFIED KNOWLEDGE", prompt)

    def test_distinct_platform_prompts(self):
        yt_prompt = get_specialized_prompt("youtube")
        tiktok_prompt = get_specialized_prompt("tiktok")
        gads_prompt = get_specialized_prompt("google_ads")
        shopee_prompt = get_specialized_prompt("shopee")

        self.assertIn("YouTube", yt_prompt)
        self.assertIn("TikTok", tiktok_prompt)
        self.assertIn("Google", gads_prompt)
        self.assertIn("Shopee", shopee_prompt)

        # Ensure they are completely distinct specialized prompt contents
        self.assertNotEqual(yt_prompt, tiktok_prompt)
        self.assertNotEqual(gads_prompt, shopee_prompt)


if __name__ == "__main__":
    unittest.main()
