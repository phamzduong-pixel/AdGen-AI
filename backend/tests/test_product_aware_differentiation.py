import unittest

from app.services.product_aware.models import (
    AudienceProfile,
    CampaignObjectiveType,
    ProductAwareContext,
    ProductProfile,
)
from app.services.product_aware.service import product_aware_engine


class ProductAwareDifferentiationVerify(unittest.TestCase):
    def setUp(self):
        self.sample_product = ProductProfile(
            name="Serum Phục Hồi Da Rau Má AdGen Cica B5",
            category="Mỹ phẩm & Chăm sóc da",
            description="Serum làm dịu da mẩn đỏ, phục hồi hàng rào bảo vệ da sau mụn",
            key_features=["Chiết xuất rau má tươi 85%", "Vitamin B5 (Panthenol) 5%", "Hyaluronic Acid đa tầng"],
            key_benefits=["Làm dịu da kích ứng trong 24h", "Cấp ẩm sâu không nhờn rít"],
            usp="Công nghệ ép lạnh giữ trọn 99% hoạt chất Cica sinh học",
            price="349.000 VNĐ",
            offer="Mua 1 tặng 1 mặt nạ làm dịu da trị giá 45.000đ",
            warranty="Cam kết hoàn tiền 100% nếu phát hiện hàng giả",
            technical_specs={"Dung tích": "30ml", "Xuất xứ": "Việt Nam", "Hạn sử dụng": "36 tháng"},
            forbidden_claims=["Trị dứt điểm mụn 100% sau 1 đêm"],
        )
        self.sample_audience = AudienceProfile(
            persona_name="Gen Z và dân văn phòng da dầu mụn",
            pain_points=["Da treatment bị đỏ rát", "Dễ bít tắc lỗ chân lông khi dùng dưỡng ẩm đặc"],
            desires=["Da khỏe, kiềm dầu, mờ thâm mụn nhẹ nhàng"],
        )

    def test_three_platforms_distinct_outputs(self):
        # 1. TikTok Context
        tiktok_ctx = ProductAwareContext(
            product=self.sample_product,
            platform="tiktok",
            audience=self.sample_audience,
            objective=CampaignObjectiveType.ENGAGEMENT,
        )
        tiktok_output = product_aware_engine.build_full_context(tiktok_ctx)

        # 2. Google Ads Context
        gads_ctx = ProductAwareContext(
            product=self.sample_product,
            platform="google_ads",
            audience=self.sample_audience,
            objective=CampaignObjectiveType.CONVERSION,
        )
        gads_output = product_aware_engine.build_full_context(gads_ctx)

        # 3. Shopee Context
        shopee_ctx = ProductAwareContext(
            product=self.sample_product,
            platform="shopee",
            audience=self.sample_audience,
            objective=CampaignObjectiveType.CONVERSION,
        )
        shopee_output = product_aware_engine.build_full_context(shopee_ctx)

        # Verify TikTok specific features
        self.assertIn("TIKTOK", tiktok_output)
        self.assertIn("1-3 giây", tiktok_output)
        self.assertIn("Timeline", tiktok_output)

        # Verify Google Ads specific features
        self.assertIn("GOOGLE SEARCH ADS", gads_output)
        self.assertIn("Tối đa 30 ký tự", gads_output)
        self.assertIn("Tối đa 90 ký tự", gads_output)

        # Verify Shopee specific features
        self.assertIn("SHOPEE", shopee_output)
        self.assertIn("Tiêu đề chuẩn SEO", shopee_output)
        self.assertIn("Bảng thông số kỹ thuật", shopee_output)

        # Verify product grounding across all 3
        for out in [tiktok_output, gads_output, shopee_output]:
            self.assertIn("Serum Phục Hồi Da Rau Má AdGen Cica B5", out)
            self.assertIn("349.000 VNĐ", out)
            self.assertIn("Trị dứt điểm mụn 100% sau 1 đêm", out)
            self.assertIn("STRICT GROUNDING", out)


if __name__ == "__main__":
    unittest.main()
