import unittest

from app.services.knowledge_base.models import (
    KnowledgeDomain,
    KnowledgeEntry,
)
from app.services.knowledge_base.service import (
    KnowledgeService,
    knowledge_service,
)


class KnowledgeBaseTest(unittest.TestCase):
    def setUp(self):
        self.service = KnowledgeService()

    def test_default_seeded_knowledge_covers_domains(self):
        marketing_entries = self.service.query_knowledge(domain=KnowledgeDomain.MARKETING)
        platform_entries = self.service.query_knowledge(domain=KnowledgeDomain.PLATFORM)

        self.assertGreaterEqual(len(marketing_entries), 2)
        self.assertGreaterEqual(len(platform_entries), 2)

        titles = [e.title for e in marketing_entries]
        self.assertTrue(any("AIDA" in t for t in titles))
        self.assertTrue(any("PAS" in t for t in titles))

    def test_register_and_query_custom_knowledge(self):
        custom_entry = KnowledgeEntry(
            id="brand-rules-adgen",
            domain=KnowledgeDomain.BRAND,
            title="Nguyên tắc thương hiệu AdGen AI",
            summary="Định vị thương hiệu và tone of voice.",
            content="Luôn giữ tinh thần công nghệ cao, hiện đại và bảo mật dữ liệu khách hàng.",
            tags=["brand", "tone", "security"],
            verified_source="AdGen Brand Identity 2026",
        )
        self.service.register_entry(custom_entry)

        res = self.service.query_knowledge(domain=KnowledgeDomain.BRAND, tags=["security"])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].id, "brand-rules-adgen")

    def test_format_knowledge_context_includes_grounding_policy(self):
        formatted = self.service.format_knowledge_context(
            platform_name="google_ads",
            product_context="Sản phẩm tai nghe không dây pin 40h.",
            brand_context="Thương hiệu AdGen Sound.",
        )
        self.assertIn("GROUNDING POLICY", formatted)
        self.assertIn("TUYỆT ĐỐI KHÔNG tự bịa đặt", formatted)
        self.assertIn("Sản phẩm tai nghe không dây pin 40h", formatted)
        self.assertIn("Thương hiệu AdGen Sound", formatted)


if __name__ == "__main__":
    unittest.main()
