from datetime import datetime, timezone
import unittest

from app.services.trend_intelligence.models import (
    TrendCategory,
    TrendItem,
    TrendQuery,
    TrendSourceType,
    ValidatedTrend,
)
from app.services.trend_intelligence.service import (
    StandardTrendNormalizer,
    StandardTrendValidator,
    TrendIntelligenceService,
    VerifiedTrendRegistryCollector,
    InMemoryTrendCache,
)


class TrendNormalizationTest(unittest.TestCase):
    def setUp(self):
        self.normalizer = StandardTrendNormalizer()
        self.validator = StandardTrendValidator()

    def test_trend_normalizer_cleans_html_and_hashtags(self):
        raw_item = TrendItem(
            topic="  E-commerce Live   ",
            headline="<b>Shopee Live</b> bùng nổ doanh số!",
            description="<p>Người tiêu dùng ưu tiên <i>mua sắm livestream</i>.</p>",
            source_name="  Báo Cáo TMĐT 2026  ",
            source_type=TrendSourceType.OFFICIAL_REPORT,
            category=TrendCategory.ECOMMERCE,
            published_at=datetime(2026, 8, 20, 10, 0, 0),  # Naive datetime
            target_platforms=["SHOPEE", "  tiktok  "],
            keywords=["#livestream", " #shopee_live ", "TMĐT"],
        )
        val = ValidatedTrend(
            item=raw_item,
            is_valid=True,
            credibility_score=0.95,
            validation_notes="Nguồn chính thống",
        )

        norm = self.normalizer.normalize(val)
        norm_item = norm.item

        self.assertEqual(norm_item.topic, "E-commerce Live")
        self.assertEqual(norm_item.headline, "Shopee Live bùng nổ doanh số!")
        self.assertEqual(norm_item.description, "Người tiêu dùng ưu tiên mua sắm livestream.")
        self.assertEqual(norm_item.source_name, "Báo Cáo TMĐT 2026")
        self.assertEqual(norm_item.published_at.tzinfo, timezone.utc)
        self.assertEqual(norm_item.target_platforms, ["shopee", "tiktok"])
        self.assertIn("livestream", norm_item.keywords)
        self.assertIn("shopee_live", norm_item.keywords)
        self.assertIn("tmđt", norm_item.keywords)

    def test_full_pipeline_with_normalization(self):
        collector = VerifiedTrendRegistryCollector()
        service = TrendIntelligenceService(
            collectors=[collector],
            validator=self.validator,
            normalizer=self.normalizer,
            cache=InMemoryTrendCache(),
        )

        raw_item = TrendItem(
            topic="AI Copywriting",
            headline="<span>70% Copywriter</span> ứng dụng AI",
            description="Tăng tốc độ sản xuất nội dung 3x.",
            source_name="Tech Times",
            source_type=TrendSourceType.PLATFORM_ANALYTICS,
            category=TrendCategory.MARKETING,
            published_at=datetime.now(timezone.utc),
            target_platforms=["Facebook", "Instagram"],
            keywords=["#AI", "Copywriting"],
        )
        collector.register_verified_trend(raw_item)

        results = service.retrieve_trends(TrendQuery(query="AI"))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].item.headline, "70% Copywriter ứng dụng AI")
        self.assertEqual(results[0].item.target_platforms, ["facebook", "instagram"])


if __name__ == "__main__":
    unittest.main()
