import json
import unittest

from app.services.prompt_service import build_system_prompt
from app.services.platform_intelligence.service import platform_intelligence_service


class MultiPlatformDifferentiationTest(unittest.TestCase):
    """
    Kiểm tra tính phân hóa rõ rệt giữa các nền tảng khi sử dụng chung 1 sản phẩm mẫu:
    'Tai nghe chống ồn không dây AdGen SoundMax ANC, pin 40h, chống nước IPX5, giá 1.290.000đ'
    """

    def setUp(self):
        self.sample_product = {
            "product_name": "Tai nghe chống ồn không dây AdGen SoundMax ANC",
            "key_features": "Chống ồn chủ động 45dB, Pin 40 giờ, Chống nước IPX5, Bluetooth 5.4",
            "target_audience": "Dân văn phòng, người thường xuyên làm việc tại quán cafe, người yêu âm nhạc",
            "price": "1.290.000 VNĐ",
            "offer": "Tặng kèm bao da cao cấp và miễn phí vận chuyển toàn quốc",
        }

    def test_tiktok_intelligence_characteristics(self):
        prompt = build_system_prompt(
            prompt_type="tiktok",
            product_context=json.dumps(self.sample_product, ensure_ascii=False),
        )
        self.assertIn("TIKTOK", prompt)
        self.assertIn("1-3 giây", prompt)
        self.assertIn("Timeline", prompt)
        self.assertIn("giỏ hàng TikTok Shop", prompt)
        self.assertNotIn("Responsive Search Ads", prompt)
        self.assertNotIn("Bảng thông số kỹ thuật", prompt)

    def test_google_ads_intelligence_characteristics(self):
        prompt = build_system_prompt(
            prompt_type="google_ads",
            product_context=json.dumps(self.sample_product, ensure_ascii=False),
        )
        self.assertIn("GOOGLE SEARCH ADS", prompt)
        self.assertIn("Tối đa 30 ký tự", prompt)
        self.assertIn("Tối đa 90 ký tự", prompt)
        self.assertIn("RSA", prompt)
        self.assertNotIn("giỏ hàng TikTok Shop", prompt)
        self.assertNotIn("B-Roll", prompt)

    def test_shopee_intelligence_characteristics(self):
        prompt = build_system_prompt(
            prompt_type="shopee",
            product_context=json.dumps(self.sample_product, ensure_ascii=False),
        )
        self.assertIn("SHOPEE", prompt)
        self.assertIn("Tiêu đề chuẩn SEO", prompt)
        self.assertIn("Bảng thông số kỹ thuật", prompt)
        self.assertNotIn("Headlines: <= 30 ký tự", prompt)
        self.assertNotIn("On-screen text", prompt)

    def test_youtube_intelligence_characteristics(self):
        prompt = build_system_prompt(
            prompt_type="youtube",
            product_context=json.dumps(self.sample_product, ensure_ascii=False),
        )
        self.assertIn("YOUTUBE", prompt)
        self.assertIn("Retention", prompt)
        self.assertIn("Timestamps", prompt)
        self.assertIn("Subscribe", prompt)


if __name__ == "__main__":
    unittest.main()
