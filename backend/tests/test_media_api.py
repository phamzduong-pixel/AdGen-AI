import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.api.media as media_api
from app.core.config import settings
from app.core.security import get_current_user
from app.database.database import Base, get_db
from app.models.conversation import Conversation
from app.models.media_asset import MediaAsset
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.services.media.media_service import MediaService
from app.services.media.providers.base import GeneratedImage, ImageGenerationProvider


VALID_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x04\x00\x00\x00\xb5\x1c\x0c\x02"
    b"\x00\x00\x00\x0bIDATx\xdac``\x00\x00\x00\x06\x00\x02"
    b"0\x81\xd0/\x00\x00\x00\x00IEND\xaeB`\x82"
)


VALID_JPEG = b"\xff\xd8\xff\xe0" + b"jpeg-test" + b"\xff\xd9"
VALID_WEBP = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"webp-test"

class RecordingImageProvider(ImageGenerationProvider):
    def __init__(self, outputs=None):
        self.outputs = list(outputs or [GeneratedImage(VALID_PNG, "image/png")])
        self.calls = []

    @property
    def provider_id(self) -> str:
        return "test"

    @property
    def model_name(self) -> str:
        return "test-image-model"

    async def generate(
        self,
        *,
        prompt,
        aspect_ratio,
        reference_image=None,
        reference_content_type=None,
    ):
        self.calls.append(
            {
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "reference_image": reference_image,
                "reference_content_type": reference_content_type,
            }
        )
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return output


class StructuredProviderError(RuntimeError):
    def __init__(self, code, status_code=None, message="provider failure"):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class MediaApiIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.Session = sessionmaker(bind=cls.engine)

    def setUp(self):
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.Session()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.upload_dir = Path(self.temp_dir.name) / "uploads"
        self.original_upload_dir = settings.UPLOAD_DIR
        self.original_media_service = media_api.media_service
        settings.UPLOAD_DIR = self.upload_dir
        self.provider = RecordingImageProvider(
            [GeneratedImage(VALID_PNG, "image/png")] * 12
        )
        self.service = MediaService(provider=self.provider)
        media_api.media_service = self.service

        self.owner = User(
            username="media-owner",
            email="media-owner@example.com",
            hashed_password="unused",
        )
        self.other = User(
            username="media-other",
            email="media-other@example.com",
            hashed_password="unused",
        )
        self.db.add_all([self.owner, self.other])
        self.db.commit()
        self.current_user = self.owner
        self.owner_conversation = self._create_conversation(self.owner)
        self.owner_other_conversation = self._create_conversation(self.owner)
        self.other_conversation = self._create_conversation(self.other)

        app = FastAPI()
        app.include_router(media_api.router)

        def override_db():
            yield self.db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: self.current_user
        self.client = TestClient(app)

    def tearDown(self):
        media_api.media_service = self.original_media_service
        settings.UPLOAD_DIR = self.original_upload_dir
        self.db.close()
        self.temp_dir.cleanup()

    def _create_conversation(self, user):
        conversation = Conversation(title="Media", user_id=user.id)
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def _generate(self, conversation_id=None, **payload):
        body = {"prompt": "Tạo ảnh quảng cáo hợp lệ", "aspect_ratio": "1:1"}
        body.update(payload)
        return self.client.post(
            f"/media/conversations/{conversation_id or self.owner_conversation.id}/images",
            json=body,
        )

    def _asset(self, asset_id):
        return self.db.get(MediaAsset, asset_id)

    def test_generate_success_persists_resolvable_asset_and_downloads(self):
        response = self._generate()
        self.assertEqual(response.status_code, 201)
        asset = self._asset(response.json()["id"])

        self.assertEqual(asset.status, "completed")
        self.assertEqual(asset.filepath, f"generated-images/{asset.filename}")
        self.assertEqual(asset.version_number, 1)
        self.assertIsNone(asset.parent_asset_id)
        resolved = self.service.get_asset_path(asset)
        self.assertTrue(resolved.is_file())
        self.assertEqual(resolved.read_bytes(), VALID_PNG)

        downloaded = self.client.get(f"/media/assets/{asset.id}/download")
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded.content, VALID_PNG)
        self.assertEqual(downloaded.headers["content-type"], "image/png")

    def test_reference_upload_is_passed_to_provider_and_output_is_saved(self):
        reference_path = self.upload_dir / "reference.png"
        reference_path.parent.mkdir(parents=True, exist_ok=True)
        reference_path.write_bytes(VALID_PNG)
        reference = UploadedFile(
            filename="reference.png",
            filepath=str(reference_path),
            content_type="image/png",
            size=len(VALID_PNG),
            conversation_id=self.owner_conversation.id,
        )
        self.db.add(reference)
        self.db.commit()

        response = self._generate(reference_file_id=reference.id)
        self.assertEqual(response.status_code, 201)
        asset = self._asset(response.json()["id"])
        self.assertEqual(asset.operation, "edit")
        self.assertEqual(asset.source_uploaded_file_id, reference.id)
        self.assertIsNone(asset.parent_asset_id)
        self.assertEqual(self.provider.calls[-1]["reference_image"], VALID_PNG)
        self.assertTrue(self.service.get_asset_path(asset).is_file())

    def test_generated_asset_edits_form_a_version_chain_without_overwrite(self):
        original_response = self._generate()
        self.assertEqual(original_response.status_code, 201)
        original = self._asset(original_response.json()["id"])
        original_path = self.service.get_asset_path(original)
        original_filename = original.filename

        second_response = self._generate(source_asset_id=original.id)
        self.assertEqual(second_response.status_code, 201)
        second = self._asset(second_response.json()["id"])
        self.assertEqual(second.parent_asset_id, original.id)
        self.assertEqual(second.version_number, 2)

        third_response = self._generate(source_asset_id=second.id)
        self.assertEqual(third_response.status_code, 201)
        third = self._asset(third_response.json()["id"])
        self.assertEqual(third.parent_asset_id, second.id)
        self.assertEqual(third.version_number, 3)

        self.assertEqual(original.filename, original_filename)
        self.assertTrue(original_path.is_file())
        self.assertEqual(original_path.read_bytes(), VALID_PNG)
        self.assertNotEqual(original.filename, second.filename)
        self.assertNotEqual(second.filename, third.filename)
        self.assertTrue(self.service.get_asset_path(second).is_file())
        self.assertTrue(self.service.get_asset_path(third).is_file())

    def test_reediting_old_image_version_uses_next_lineage_number(self):
        original = self._asset(self._generate().json()["id"])
        first_edit = self._asset(self._generate(source_asset_id=original.id).json()["id"])
        branch_edit = self._asset(self._generate(source_asset_id=original.id).json()["id"])

        self.assertEqual(first_edit.parent_asset_id, original.id)
        self.assertEqual(branch_edit.parent_asset_id, original.id)
        self.assertEqual(first_edit.version_number, 2)
        self.assertEqual(branch_edit.version_number, 3)
        self.assertTrue(self.service.get_asset_path(first_edit).is_file())
        self.assertTrue(self.service.get_asset_path(branch_edit).is_file())
    def test_delete_completed_image_removes_asset_and_file(self):
        response = self._generate()
        self.assertEqual(response.status_code, 201)
        asset_id = response.json()["id"]
        asset = self._asset(asset_id)
        path = self.service.get_asset_path(asset)
        self.assertTrue(path.is_file())

        deleted = self.client.delete(
            f"/media/conversations/{self.owner_conversation.id}/assets/{asset_id}"
        )

        self.assertEqual(deleted.status_code, 204)
        self.assertIsNone(self._asset(asset_id))
        self.assertFalse(path.exists())

    def test_delete_failed_image_removes_asset(self):
        self.provider.outputs = [RuntimeError("provider unavailable")]
        failed = self._generate()
        self.assertEqual(failed.status_code, 502)
        asset_id = failed.json().get("id")
        if asset_id is None:
            asset_id = self.db.query(MediaAsset).order_by(MediaAsset.id.desc()).first().id

        deleted = self.client.delete(
            f"/media/conversations/{self.owner_conversation.id}/assets/{asset_id}"
        )

        self.assertEqual(deleted.status_code, 204)
        self.assertIsNone(self._asset(asset_id))

    def test_delete_image_preserves_lineage_and_enforces_scope(self):
        original = self._asset(self._generate().json()["id"])
        child = self._asset(self._generate(source_asset_id=original.id).json()["id"])
        original_path = self.service.get_asset_path(original)

        blocked = self.client.delete(
            f"/media/conversations/{self.owner_conversation.id}/assets/{original.id}"
        )
        self.assertEqual(blocked.status_code, 409)
        self.assertIsNotNone(self._asset(original.id))
        self.assertTrue(original_path.is_file())

        self.current_user = self.other
        cross_user = self.client.delete(
            f"/media/conversations/{self.owner_conversation.id}/assets/{child.id}"
        )
        self.assertEqual(cross_user.status_code, 404)

        self.current_user = self.owner
        cross_conversation = self.client.delete(
            f"/media/conversations/{self.owner_other_conversation.id}/assets/{child.id}"
        )
        self.assertEqual(cross_conversation.status_code, 404)
    def test_permissions_block_other_user_and_other_conversation(self):
        asset_response = self._generate()
        asset_id = asset_response.json()["id"]

        self.current_user = self.other
        self.assertEqual(
            self.client.get(f"/media/assets/{asset_id}/download").status_code,
            404,
        )
        self.assertEqual(
            self._generate(
                self.other_conversation.id,
                source_asset_id=asset_id,
            ).status_code,
            404,
        )

        self.current_user = self.owner
        self.assertEqual(
            self._generate(
                self.owner_other_conversation.id,
                source_asset_id=asset_id,
            ).status_code,
            404,
        )

    def test_provider_timeout_marks_asset_failed_without_raw_error(self):
        async def slow_generate(**kwargs):
            await asyncio.sleep(0.02)
            return GeneratedImage(VALID_PNG, "image/png")

        self.provider.generate = slow_generate
        original_timeout = settings.IMAGE_GENERATION_TIMEOUT_SECONDS
        settings.IMAGE_GENERATION_TIMEOUT_SECONDS = 0.001
        try:
            response = self._generate()
        finally:
            settings.IMAGE_GENERATION_TIMEOUT_SECONDS = original_timeout
        self.assertEqual(response.status_code, 504)
        self.assertEqual(response.json()["detail"]["code"], "PROVIDER_TIMEOUT")
        asset = self.db.query(MediaAsset).order_by(MediaAsset.id.desc()).first()
        self.assertEqual(asset.status, "failed")
        self.assertEqual(asset.error_message, "Image provider timeout")
        self.assertNotIn("TimeoutError", response.text)
        self.assertEqual(list((self.upload_dir / "generated-images").glob("*")), [])
    def test_provider_http_exception_is_sanitized_and_marks_asset_failed(self):
        self.provider.outputs = [
            HTTPException(
                status_code=429,
                detail="api_key=SECRET https://internal.example/request",
            )
        ]
        response = self._generate()
        self.assertEqual(response.status_code, 429)
        detail = response.json()["detail"]
        self.assertEqual(detail["code"], "PROVIDER_ERROR")
        self.assertIn("limited by provider request or resource", detail["message"])
        self.assertNotIn("SECRET", response.text)
        self.assertNotIn("internal.example", response.text)
        asset = self.db.query(MediaAsset).order_by(MediaAsset.id.desc()).first()
        self.assertEqual(asset.status, "failed")
        self.assertEqual(asset.error_message, "Image provider failed")

    def test_generic_provider_quota_error_keeps_safe_429_contract(self):
        class ProviderQuotaError(RuntimeError):
            code = 429

        self.provider.outputs = [ProviderQuotaError("api_key=SECRET provider-url=https://internal.example")]
        response = self._generate()
        self.assertEqual(response.status_code, 429)
        self.assertNotIn("SECRET", response.text)
        self.assertNotIn("internal.example", response.text)
        asset = self.db.query(MediaAsset).order_by(MediaAsset.id.desc()).first()
        self.assertEqual(asset.status, "failed")
        self.assertEqual(asset.error_message, "Image provider failed")
        self.assertEqual(list((self.upload_dir / "generated-images").glob("*")), [])

    def test_generic_too_many_requests_is_not_labeled_as_quota(self):
        class GenericRateLimitError(RuntimeError):
            status_code = 429

        self.provider.outputs = [GenericRateLimitError("429 Too Many Requests")]
        response = self._generate()

        self.assertEqual(response.status_code, 429)
        detail = response.json()["detail"]
        self.assertEqual(detail["code"], "PROVIDER_ERROR")
        self.assertIn("limited by provider request or resource", detail["message"])
        self.assertNotIn("quota", detail["message"].lower())

    def test_string_only_quota_error_maps_to_safe_429(self):
        self.provider.outputs = [RuntimeError("429 RESOURCE_EXHAUSTED api_key=SECRET") ]
        response = self._generate()

        self.assertEqual(response.status_code, 429)
        detail = response.json()["detail"]
        self.assertEqual(detail["code"], "RESOURCE_EXHAUSTED")
        self.assertIn("verified provider quota", detail["message"])
        self.assertNotIn("SECRET", response.text)
        asset = self.db.query(MediaAsset).order_by(MediaAsset.id.desc()).first()
        self.assertEqual(asset.status, "failed")
        self.assertEqual(asset.error_message, "Image provider quota exceeded")

    def test_structured_provider_codes_are_preserved(self):
        cases = [
            ("RESOURCE_EXHAUSTED", 429),
            ("INVALID_ARGUMENT", 400),
            ("MODEL_NOT_FOUND", 502),
            ("PERMISSION_DENIED", 502),
            ("UNAUTHENTICATED", 502),
        ]
        for code, expected_status in cases:
            with self.subTest(code=code):
                self.provider.outputs = [StructuredProviderError(code, message=f"{code} internal secret")]
                response = self._generate()
                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(response.json()["detail"]["code"], code)
                self.assertNotIn("secret", response.text.lower())

    def test_provider_error_without_code_is_not_labeled_as_quota(self):
        self.provider.outputs = [RuntimeError("provider unavailable")]
        response = self._generate()
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["detail"]["code"], "PROVIDER_ERROR")

    def test_file_write_failure_marks_asset_failed_and_cleans_output(self):
        with patch.object(Path, "write_bytes", side_effect=OSError("disk full")):
            response = self._generate()
        self.assertEqual(response.status_code, 502)
        asset = self.db.query(MediaAsset).order_by(MediaAsset.id.desc()).first()
        self.assertEqual(asset.status, "failed")
        self.assertEqual(asset.error_message, "Image storage failed")
        self.assertNotIn("disk full", response.text)
        self.assertEqual(list((self.upload_dir / "generated-images").glob("*")), [])

    def test_jpeg_and_webp_reference_bytes_are_validated_and_passed_through(self):
        references = [
            ("reference.jpg", "image/jpeg", VALID_JPEG),
            ("reference.webp", "image/webp", VALID_WEBP),
        ]
        for filename, content_type, data in references:
            path = self.upload_dir / filename
            path.write_bytes(data)
            reference = UploadedFile(
                filename=filename,
                filepath=str(path),
                content_type=content_type,
                size=len(data),
                conversation_id=self.owner_conversation.id,
            )
            self.db.add(reference)
            self.db.commit()
            response = self._generate(reference_file_id=reference.id)
            self.assertEqual(response.status_code, 201)
            self.assertEqual(self.provider.calls[-1]["reference_image"], data)
            self.assertEqual(
                self.provider.calls[-1]["reference_content_type"], content_type
            )

    def test_reference_with_fake_signature_is_rejected_before_provider(self):
        path = self.upload_dir / "fake.png"
        path.write_bytes(b"not-a-png")
        reference = UploadedFile(
            filename="fake.png",
            filepath=str(path),
            content_type="image/png",
            size=9,
            conversation_id=self.owner_conversation.id,
        )
        self.db.add(reference)
        self.db.commit()
        call_count = len(self.provider.calls)
        response = self._generate(reference_file_id=reference.id)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(self.provider.calls), call_count)
        self.assertNotIn("not-a-png", response.text)

    def test_reference_with_mismatched_mime_and_signature_is_rejected(self):
        path = self.upload_dir / "mismatch.png"
        path.write_bytes(VALID_JPEG)
        reference = UploadedFile(
            filename="mismatch.png",
            filepath=str(path),
            content_type="image/png",
            size=len(VALID_JPEG),
            conversation_id=self.owner_conversation.id,
        )
        self.db.add(reference)
        self.db.commit()
        call_count = len(self.provider.calls)
        response = self._generate(reference_file_id=reference.id)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(self.provider.calls), call_count)
    def test_unreadable_reference_is_rejected_without_raw_error(self):
        path = self.upload_dir / "unreadable.png"
        path.write_bytes(VALID_PNG)
        reference = UploadedFile(
            filename="unreadable.png",
            filepath=str(path),
            content_type="image/png",
            size=len(VALID_PNG),
            conversation_id=self.owner_conversation.id,
        )
        self.db.add(reference)
        self.db.commit()
        call_count = len(self.provider.calls)
        with patch.object(Path, "read_bytes", side_effect=PermissionError("secret path")):
            response = self._generate(reference_file_id=reference.id)
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("secret path", response.text)
        self.assertEqual(len(self.provider.calls), call_count)
    def test_missing_reference_file_is_rejected_before_provider(self):
        reference = UploadedFile(
            filename="missing.png",
            filepath=str(self.upload_dir / "missing.png"),
            content_type="image/png",
            size=len(VALID_PNG),
            conversation_id=self.owner_conversation.id,
        )
        self.db.add(reference)
        self.db.commit()
        call_count = len(self.provider.calls)
        response = self._generate(reference_file_id=reference.id)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(len(self.provider.calls), call_count)

    def test_completed_asset_is_never_downgraded_by_failure_marker(self):
        asset = self._asset(self._generate().json()["id"])
        self.service._mark_failed(self.db, asset, "unsafe downgrade")
        self.db.refresh(asset)
        self.assertEqual(asset.status, "completed")
        self.assertIsNone(asset.error_message)
    def test_provider_failure_marks_asset_failed_without_output_file(self):
        self.provider.outputs = [RuntimeError("provider unavailable")]
        response = self._generate()
        self.assertEqual(response.status_code, 502)
        asset = self.db.query(MediaAsset).order_by(MediaAsset.id.desc()).first()
        self.assertEqual(asset.status, "failed")
        self.assertIsNone(asset.filepath)
        self.assertEqual(list((self.upload_dir / "generated-images").glob("*")), [])

    def test_invalid_provider_outputs_are_rejected_and_marked_failed(self):
        self.provider.outputs = [
            GeneratedImage(VALID_PNG, "image/gif"),
            GeneratedImage(b"not-a-png", "image/png"),
        ]
        for _ in range(2):
            response = self._generate()
            self.assertEqual(response.status_code, 502)

        original_max_upload_size = settings.MAX_UPLOAD_SIZE
        try:
            settings.MAX_UPLOAD_SIZE = 8
            self.provider.outputs = [GeneratedImage(VALID_PNG, "image/png")]
            self.assertEqual(self._generate().status_code, 502)
        finally:
            settings.MAX_UPLOAD_SIZE = original_max_upload_size

        assets = self.db.query(MediaAsset).order_by(MediaAsset.id).all()
        self.assertEqual([asset.status for asset in assets], ["failed"] * 3)
        self.assertTrue(all(asset.filepath is None for asset in assets))
        self.assertEqual(list((self.upload_dir / "generated-images").glob("*")), [])


if __name__ == "__main__":
    unittest.main()
