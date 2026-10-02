import unittest

from app.services.product_aware.models import (
    AudienceProfile,
    CampaignObjectiveType,
    ProductAwareContext,
    ProductProfile,
)
from app.services.product_aware.service import (
    ProductAwareEngine,
    product_aware_engine,
)


class ProductAwareEngineTest(unittest.TestCase):
    def setUp(self):
        self.product = ProductProfile(
            name="Bộ Chuột Không Dây Công Thái Học Ergonomic AdGen M1",
            category="Phụ kiện công nghệ",
            description="Chuột không dây thiết kế công thái học chống mỏi cổ tay",
            key_features=["Form cầm công thái học", "Silent click êm ái", "Pin sạc 500mAh dùng 60 ngày", "Bluetooth 5.3 & 2.4G"],
            key_benefits=["Bảo vệ cổ tay khi làm việc 8 tiếng", "Không gây ồn trong văn phòng yên tĩnh"],
            usp="Góc nghiêng 57 độ tự nhiên theo cấu trúc giải phẫu bàn tay",
            price="590.000 VNĐ",
            offer="Tặng lót chuột đệm cổ tay cao cấp",
            warranty="Bảo hành 1 đổi 1 trong 12 tháng",
            technical_specs={"Trọng lượng": "95g", "Độ phân giải": "800-1600-2400-4000 DPI"},
            forbidden_claims=["Chữa khỏi 100% hội chứng ống cổ tay"],
        )
        self.audience = AudienceProfile(
            persona_name="Dân văn phòng, lập trình viên, designer",
            pain_points=["Đau mỏi cổ tay sau ngày dài gõ phím", "Tiếng click chuột làm phiền đồng nghiệp"],
            desires=["Cầm nắm thoải mái", "Bàn làm việc gọn gàng không vướng dây"],
            common_objections=["Sợ pin nhanh hết", "Sợ bị trễ kết nối không dây"],
        )

    def test_product_aware_context_construction(self):
        ctx = ProductAwareContext(
            product=self.product,
            platform="shopee",
            audience=self.audience,
            objective=CampaignObjectiveType.CONVERSION,
            brand_name="AdGen Tech",
            brand_voice="Hiện đại, đáng tin cậy",
        )

        formatted = product_aware_engine.build_full_context(ctx)

        # 1. Product Data Check
        self.assertIn("Bộ Chuột Không Dây Công Thái Học Ergonomic AdGen M1", formatted)
        self.assertIn("590.000 VNĐ", formatted)
        self.assertIn("Góc nghiêng 57 độ", formatted)
        self.assertIn("Chữa khỏi 100% hội chứng ống cổ tay", formatted)

        # 2. Audience Data Check
        self.assertIn("Dân văn phòng, lập trình viên, designer", formatted)
        self.assertIn("Đau mỏi cổ tay sau ngày dài gõ phím", formatted)

        # 3. Campaign Objective Check
        self.assertIn("Chuyển đổi bán hàng / Chốt đơn trực tiếp", formatted)

        # 4. Platform Intelligence Check
        self.assertIn("SHOPEE", formatted)
        self.assertIn("Tiêu đề chuẩn SEO", formatted)

        # 5. Marketing & Platform Knowledge Check
        self.assertIn("VERIFIED KNOWLEDGE", formatted)
        self.assertIn("AdGen Tech", formatted)
        self.assertIn("BRAND KNOWLEDGE", formatted)

        # 6. Anti-hallucination Grounding Rule Check
        self.assertIn("STRICT GROUNDING", formatted)
        self.assertIn("Tuyệt đối KHÔNG tự ý đưa ra mức giá", formatted)


if __name__ == "__main__":
    unittest.main()
