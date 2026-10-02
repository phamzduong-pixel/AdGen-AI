import tempfile
from pathlib import Path
import unittest

from app.services.multimodal.models import (
    MediaAsset,
    ModalityType,
    MultimodalPayload,
    MultimodalTaskType,
)
from app.services.multimodal.service import (
    MultimodalService,
    StandardMultimodalProcessor,
    multimodal_service,
)


class MultimodalArchitectureTest(unittest.TestCase):
    def setUp(self):
        self.processor = StandardMultimodalProcessor()
        self.service = MultimodalService(self.processor)

    def test_processor_handles_all_multimodal_task_types(self):
        tasks = [
            MultimodalTaskType.TEXT_TO_TEXT,
            MultimodalTaskType.IMAGE_TO_TEXT,
            MultimodalTaskType.VIDEO_TO_TEXT,
            MultimodalTaskType.TEXT_TO_IMAGE,
            MultimodalTaskType.TEXT_TO_VIDEO,
            MultimodalTaskType.VIDEO_TO_EDITED_VIDEO,
        ]
        for t in tasks:
            self.assertTrue(self.processor.can_handle(t))

    def test_media_asset_creation_and_modality_detection(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"fake image bytes")
            img_path = f.name

        try:
            asset = self.service.create_media_asset(
                asset_id="asset-1",
                file_path=img_path,
                filename="product_photo.jpg",
                mime_type="image/jpeg",
            )
            self.assertEqual(asset.modality, ModalityType.IMAGE)
            self.assertEqual(asset.filename, "product_photo.jpg")
            self.assertTrue(asset.exists())
            self.assertEqual(asset.read_bytes(), b"fake image bytes")

            # Test payload conversion to parts
            payload = MultimodalPayload(
                prompt_text="Tạo bài viết bán hàng từ ảnh sản phẩm này",
                task_type=MultimodalTaskType.IMAGE_TO_TEXT,
                media_assets=[asset],
            )
            parts = self.service.prepare_multimodal_context(payload)
            self.assertEqual(len(parts), 2)
            self.assertEqual(parts[0]["type"], "text")
            self.assertEqual(parts[1]["type"], "binary")
            self.assertEqual(parts[1]["mime_type"], "image/jpeg")
            self.assertEqual(parts[1]["bytes"], b"fake image bytes")
        finally:
            Path(img_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
