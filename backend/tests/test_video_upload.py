import io
import unittest
from unittest.mock import MagicMock

from fastapi import HTTPException, UploadFile

from app.models.conversation import Conversation
from app.models.user import User
from app.services.multimodal.models import ModalityType
from app.services.multimodal.service import multimodal_service
from app.services.upload_service import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    _validate_filename,
    determine_file_type,
)


class VideoUploadTest(unittest.TestCase):
    def test_video_extensions_and_mime_types_allowed(self):
        # Video extensions
        self.assertIn(".mp4", ALLOWED_EXTENSIONS)
        self.assertIn(".mov", ALLOWED_EXTENSIONS)
        self.assertIn(".webm", ALLOWED_EXTENSIONS)

        # Video MIME types
        self.assertIn("video/mp4", ALLOWED_MIME_TYPES[".mp4"])
        self.assertIn("video/quicktime", ALLOWED_MIME_TYPES[".mov"])
        self.assertIn("video/webm", ALLOWED_MIME_TYPES[".webm"])

        # Preserved previous extensions
        self.assertIn(".png", ALLOWED_EXTENSIONS)
        self.assertIn(".jpg", ALLOWED_EXTENSIONS)
        self.assertIn(".pdf", ALLOWED_EXTENSIONS)
        self.assertIn(".docx", ALLOWED_EXTENSIONS)

    def test_determine_file_type(self):
        self.assertEqual(determine_file_type("video/mp4", "promo.mp4"), "video")
        self.assertEqual(determine_file_type("video/quicktime", "clip.mov"), "video")
        self.assertEqual(determine_file_type("video/webm", "reel.webm"), "video")
        self.assertEqual(determine_file_type("image/png", "banner.png"), "image")
        self.assertEqual(determine_file_type("application/pdf", "brief.pdf"), "pdf")
        self.assertEqual(determine_file_type("text/plain", "notes.txt"), "document")

    def test_validate_video_filename(self):
        safe_name, ext = _validate_filename("my_video_ad.MP4")
        self.assertEqual(ext, ".mp4")
        self.assertEqual(safe_name, "my_video_ad.mp4")

        safe_name_mov, ext_mov = _validate_filename("c:\\path\\to\\iphone_shoot.MOV")
        self.assertEqual(ext_mov, ".mov")
        self.assertEqual(safe_name_mov, "iphone_shoot.mov")

    def test_validate_invalid_extension_rejected(self):
        with self.assertRaises(HTTPException) as ctx:
            _validate_filename("malicious_file.exe")
        self.assertEqual(ctx.exception.status_code, 400)

        with self.assertRaises(HTTPException) as ctx:
            _validate_filename("script.sh")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_multimodal_service_recognizes_video_media_asset(self):
        asset = multimodal_service.create_media_asset(
            asset_id="video-01",
            file_path="uploads/test_video.mp4",
            filename="test_video.mp4",
            mime_type="video/mp4",
        )
        self.assertEqual(asset.modality, ModalityType.VIDEO)
        self.assertEqual(asset.filename, "test_video.mp4")

        img_asset = multimodal_service.create_media_asset(
            asset_id="img-01",
            file_path="uploads/test_img.png",
            filename="test_img.png",
            mime_type="image/png",
        )
        self.assertEqual(img_asset.modality, ModalityType.IMAGE)


if __name__ == "__main__":
    unittest.main()
