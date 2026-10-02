from datetime import datetime, timezone, timedelta
import unittest

from app.services.trend_intelligence.models import (
    TrendCategory,
    TrendItem,
    TrendQuery,
    TrendSourceType,
)
from app.services.trend_intelligence.service import (
    InMemoryTrendCache,
    StandardTrendValidator,
    TrendIntelligenceService,
    VerifiedTrendRegistryCollector,
    trend_intelligence_service,
)


class TrendIntelligenceTest(unittest.TestCase):
    def setUp(self):
        self.validator = StandardTrendValidator()
        self.cache = InMemoryTrendCache()
        self.collector = VerifiedTrendRegistryCollector()
        self.service = TrendIntelligenceService(
            collectors=[self.collector],
            validator=self.validator,
            cache=self.cache,
        )

    def test_validation_freshness_and_credibility(self):
        query = TrendQuery(max_age_days=15, min_credibility=0.7)

        # Fresh verified item
        fresh_item = TrendItem(
            topic="AI Copywriting Adoption",
            headline="68% doanh nghiệp ứng dụng AI trong tạo nội dung 2026",
            description="Báo cáo thị trường chỉ ra mức tăng trưởng vượt bậc trong quảng cáo AI.",
            source_name="Vietnam Digital Marketing Report 2026",
            source_type=TrendSourceType.OFFICIAL_REPORT,
            category=TrendCategory.MARKETING,
            published_at=datetime.now(timezone.utc) - timedelta(days=2),
        )
        val = self.validator.validate(fresh_item, query)
        self.assertTrue(val.is_valid)
        self.assertGreaterEqual(val.credibility_score, 0.7)

        # Expired item
        expired_item = TrendItem(
            topic="Cũ",
            headline="Tin cũ năm ngoái",
            description="Nội dung đã hết hạn",
            source_name="Old Report",
            source_type=TrendSourceType.OFFICIAL_REPORT,
            category=TrendCategory.MARKETING,
            published_at=datetime.now(timezone.utc) - timedelta(days=40),
        )
        val_expired = self.validator.validate(expired_item, query)
        self.assertFalse(val_expired.is_valid)
        self.assertIn("Dữ liệu đã cũ", val_expired.validation_notes)

    def test_cache_mechanism(self):
        query = TrendQuery(query="tech")
        cache_key = "trends:test"

        # Check empty
        self.assertIsNone(self.cache.get(cache_key))

        # Add item and retrieve through service
        fresh_item = TrendItem(
            topic="Tech Gear",
            headline="Tai nghe ANC xu hướng 2026",
            description="Người dùng ưu tiên thời lượng pin trên 30h và chống ồn chủ động.",
            source_name="TechReview VN",
            source_type=TrendSourceType.MARKET_DATA,
            category=TrendCategory.CONSUMER_TECH,
            published_at=datetime.now(timezone.utc),
            target_platforms=["tiktok", "shopee"],
            keywords=["tai nghe", "anc"],
        )
        self.collector.register_verified_trend(fresh_item)

        results = self.service.retrieve_trends(query)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].item.topic, "Tech Gear")

    def test_grounding_policy_when_no_trends_found(self):
        empty_service = TrendIntelligenceService(
            collectors=[VerifiedTrendRegistryCollector()],
            validator=StandardTrendValidator(),
            cache=InMemoryTrendCache(),
        )
        formatted = empty_service.format_trend_context(query="non_existent_topic")
        self.assertIn("Hiện không có dữ liệu xu hướng được xác thực", formatted)
        self.assertIn("Không tự bịa đặt số liệu thống kê", formatted)

    def test_format_trend_context_with_valid_trend(self):
        fresh_item = TrendItem(
            topic="TikTok UGC Trends",
            headline="Nội dung UGC dạng POV đạt tỷ lệ chuyển đổi cao hơn 42%",
            description="Người xem TikTok phản hồi tích cực với video phong cách trải nghiệm cá nhân chân thực.",
            source_name="TikTok Creative Center",
            source_type=TrendSourceType.PLATFORM_ANALYTICS,
            category=TrendCategory.MARKETING,
            published_at=datetime.now(timezone.utc),
            target_platforms=["tiktok"],
        )
        self.collector.register_verified_trend(fresh_item)
        formatted = self.service.format_trend_context(platform="tiktok")
        self.assertIn("THÔNG TIN XU HƯỚNG ĐÃ XÁC THỰC", formatted)
        self.assertIn("TikTok UGC Trends", formatted)
        self.assertIn("42%", formatted)


if __name__ == "__main__":
    unittest.main()
