import tempfile
import unittest
from unittest.mock import patch

from app.core.config import settings
from app.schemas.voiceover import VoiceoverGenerateRequest
from app.services.voiceover.extractor import VoiceoverScriptExtractor
from app.services.voiceover.providers.mock_provider import MockTTSProvider
from app.services.voiceover.voiceover_service import VoiceoverService


class VoiceoverScriptExtractorTests(unittest.TestCase):
    def extract(self, text):
        return VoiceoverScriptExtractor.extract(text)

    def test_vo_marker_has_priority(self):
        result = self.extract("Visual: chai nuoc\nVO: Uong nuoc deu dan moi ngay.")
        self.assertEqual(result.status, "success")
        self.assertEqual(result.cleaned_script, "Uong nuoc deu dan moi ngay.")

    def test_loi_thoai_marker(self):
        result = self.extract("Lời thoại: Chọn giải pháp phù hợp với bạn.")
        self.assertEqual(result.status, "success")
        self.assertEqual(result.cleaned_script, "Chọn giải pháp phù hợp với bạn.")

    def test_narration_marker(self):
        result = self.extract("Narration - Một ngày hiệu quả bắt đầu từ điều nhỏ.")
        self.assertEqual(result.status, "success")
        self.assertIn("Một ngày hiệu quả", result.cleaned_script)

    def test_unmarked_multi_part_quoted_script_is_extracted(self):
        text = '''Tuyệt vời! Đây là nội dung thoại để bạn tạo giọng nói cho video TikTok của mình:

(Voice: Trẻ trung, năng động, thân thiện, truyền cảm)

"Sáng nay bạn dậy trễ? Hay cả ngày dài cứ cuốn mình đi? Đừng lo..."
"Bình giữ nhiệt [Tên Sản Phẩm] chính là người bạn đồng hành..."
"Dù đang cày deadline..."
"Không chỉ tiện lợi..."
"Sắm ngay [Tên Sản Phẩm]..."'''
        result = self.extract(text)
        self.assertEqual(result.status, "success")
        self.assertEqual(result.dialogue_blocks_count, 5)
        self.assertNotIn("Tuyệt vời", result.cleaned_script)
        self.assertNotIn("Voice:", result.cleaned_script)
        self.assertIn("[Tên Sản Phẩm]", result.cleaned_script)

    def test_heading_and_unquoted_script_blocks_are_candidates(self):
        result = self.extract("# Kịch bản video\nCảnh 1\nBạn đang vội cho một ngày dài.\nMột lựa chọn nhỏ giúp bạn chủ động hơn.")
        self.assertEqual(result.status, "uncertain")
        self.assertIn("Bạn đang vội", result.cleaned_script)
        self.assertIn("Một lựa chọn", result.cleaned_script)

    def test_production_cues_are_not_read(self):
        result = self.extract("Visual: Cận cảnh sản phẩm\nCamera: Zoom chậm\nNhạc: Nhịp nhanh\nVO: Sẵn sàng cho ngày mới! [Tên Sản Phẩm]")
        self.assertEqual(result.cleaned_script, "Sẵn sàng cho ngày mới! [Tên Sản Phẩm]")

    def test_markdown_and_formatting_are_removed_without_rewriting(self):
        result = self.extract("VO: \"_Ưu đãi hôm nay!_\"")
        self.assertEqual(result.cleaned_script, "Ưu đãi hôm nay!")

    def test_emoji_are_removed_from_filtered_dialogue(self):
        result = self.extract("VO: Me chan ga \U0001F62B ngon qua!")
        self.assertEqual(result.status, "success")
        self.assertEqual(result.cleaned_script, "Me chan ga ngon qua!")
    def test_plain_non_script_stays_uncertain_not_success(self):
        result = self.extract("Đây là câu trả lời thông thường về cách xây dựng nội dung quảng cáo.")
        self.assertEqual(result.status, "uncertain")
        self.assertEqual(result.cleaned_script, "Đây là câu trả lời thông thường về cách xây dựng nội dung quảng cáo.")

    def test_extraction_never_invents_or_reorders_words(self):
        result = self.extract('"Đoạn một nguyên bản."\n"Đoạn hai nguyên bản."')
        self.assertEqual(result.cleaned_script, "Đoạn một nguyên bản.\n\nĐoạn hai nguyên bản.")


class VoiceoverExtractionContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_clean_script_and_generate_share_extraction_contract(self):
        raw = "Visual: chai nuoc\nVO: Uong nuoc deu dan moi ngay."
        with tempfile.TemporaryDirectory() as directory, patch.object(settings, "UPLOAD_DIR", directory):
            service = VoiceoverService(provider=MockTTSProvider())
            cleaned = service.clean_script(raw)
            generated = await service.generate_voiceover(VoiceoverGenerateRequest(text=raw))

        self.assertEqual(cleaned.status, "success")
        self.assertEqual(generated.cleaned_text, cleaned.cleaned_script)
