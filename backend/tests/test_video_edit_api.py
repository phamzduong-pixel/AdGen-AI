import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.api.media as media_api
import app.services.upload_service as upload_service
from app.core.config import settings
from app.core.security import get_current_user
from app.database.database import Base, get_db
from app.models.conversation import Conversation
from app.models.media_asset import MediaAsset
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.services.media.video_processor import VideoMetadata, VideoProcessorError
from app.services.media.video_service import VideoService


class FakeVideoProcessor:
    def __init__(self, fail=False):
        self.fail = fail
        self.unexpected = False
        self.probe_dimensions = (1280, 720)
        self.aspect_output_dimensions = None
        self.output_has_audio = True
        self.probe_overrides = {}
        self.trim_calls = []
        self.operation_calls = 0
        self.fail_on_operation_call = None
        self.output_duration_override = None
        self.trim_output_duration_override = None
        self.force_invalid_output_duration = False

    def _render_should_fail(self):
        self.operation_calls += 1
        return self.fail or self.fail_on_operation_call == self.operation_calls

    def _write_output(self, destination):
        destination.write_bytes(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00")

    def aspect_crop(self, source, destination, width, height):
        self.probe_dimensions = self.aspect_output_dimensions or (width, height)
        if self.unexpected:
            raise RuntimeError("unexpected processor failure")
        if self._render_should_fail():
            raise VideoProcessorError("render failure")
        if self.output_duration_override is None:
            self.output_duration_override = 20.0
        self._write_output(destination)

    def text_overlay(self, source, destination, text, start, end, position, font_size, text_color, background):
        if self.unexpected:
            raise RuntimeError("unexpected processor failure")
        if self._render_should_fail():
            raise VideoProcessorError("render failure")
        if self.output_duration_override is None:
            self.output_duration_override = 20.0
        self._write_output(destination)

    def subtitles(self, source, destination, entries, position):
        if self.unexpected:
            raise RuntimeError("unexpected processor failure")
        if self._render_should_fail():
            raise VideoProcessorError("render failure")
        if self.output_duration_override is None:
            self.output_duration_override = 20.0
        self._write_output(destination)

    def volume(self, source, destination, factor, mute=False):
        if self._render_should_fail():
            raise VideoProcessorError("audio failure")
        self.output_duration_override = 0.0 if self.force_invalid_output_duration else (self.output_duration_override if self.output_duration_override is not None else 20.0)
        self._write_output(destination)

    def merge(self, sources, destination):
        if self._render_should_fail():
            raise VideoProcessorError("merge failure")
        self.output_duration_override = 40.0
        self._write_output(destination)

    def probe(self, path):
        if self.fail:
            raise VideoProcessorError("processor unavailable")
        width, height = self.probe_overrides.get(str(path), self.probe_dimensions)
        has_audio = self.output_has_audio if "edited-videos" in str(path) else True
        duration = 20.0
        if "edited-videos" in str(path):
            duration = self.output_duration_override if self.output_duration_override is not None else 20.0
        return VideoMetadata(duration, width, height, "video/mp4", has_audio, "aac" if has_audio else None, "h264", "mov,mp4")

    def trim(self, source, destination, start, end):
        self.trim_calls.append((source, destination, start, end))
        if self.unexpected:
            raise RuntimeError("unexpected processor failure")
        if self._render_should_fail():
            raise VideoProcessorError("render failure")
        self.output_duration_override = self.trim_output_duration_override if self.trim_output_duration_override is not None else end - start
        self._write_output(destination)

class VideoEditApiIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        cls.Session = sessionmaker(bind=cls.engine)

    def setUp(self):
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.Session()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_upload_dir = settings.UPLOAD_DIR
        self.original_video_service = media_api.video_service
        settings.UPLOAD_DIR = Path(self.temp_dir.name) / "uploads"
        self.processor = FakeVideoProcessor()
        self.service = VideoService(processor=self.processor)
        media_api.video_service = self.service
        self.original_media_storage = media_api.media_service.storage
        media_api.media_service.storage = self.service.storage
        self.original_upload_storage = upload_service.file_storage
        upload_service.file_storage = self.service.storage
        self.owner = User(username="video-owner", email="video-owner@example.com", hashed_password="x")
        self.other = User(username="video-other", email="video-other@example.com", hashed_password="x")
        self.db.add_all([self.owner, self.other])
        self.db.commit()
        self.conversation = self._conversation(self.owner)
        self.other_conversation = self._conversation(self.owner)
        self.foreign_conversation = self._conversation(self.other)
        self.current_user = self.owner
        app = FastAPI()
        app.include_router(media_api.router)
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.current_user
        self.client = TestClient(app)

    def tearDown(self):
        media_api.video_service = self.original_video_service
        media_api.media_service.storage = self.original_media_storage
        upload_service.file_storage = self.original_upload_storage
        settings.UPLOAD_DIR = self.original_upload_dir
        self.db.close()
        self.temp_dir.cleanup()

    def _conversation(self, user):
        item = Conversation(title="Video", user_id=user.id)
        self.db.add(item); self.db.commit(); self.db.refresh(item)
        return item

    def _upload(self, conversation=None, user=None, content_type="video/mp4"):
        conversation = conversation or self.conversation
        path = settings.UPLOAD_DIR / f"source-{conversation.id}-{self.db.query(UploadedFile).count()}.mp4"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00")
        item = UploadedFile(filename="source.mp4", filepath=str(path), content_type=content_type, size=path.stat().st_size, conversation_id=conversation.id)
        self.db.add(item); self.db.commit(); self.db.refresh(item)
        return item

    def _register(self, file_id, conversation=None):
        return self.client.post(f"/media/conversations/{(conversation or self.conversation).id}/videos/from-upload", json={"source_file_id": file_id})

    def _trim(self, asset_id, payload=None, conversation=None):
        return self.client.post(f"/media/conversations/{(conversation or self.conversation).id}/videos/{asset_id}/edits", json=payload or {"operation":"trim", "start":2, "end":12})

    def test_trim_creates_downloadable_version_without_overwriting_original(self):
        uploaded = self._upload()
        original_response = self._register(uploaded.id)
        self.assertEqual(original_response.status_code, 201)
        original = self.db.get(MediaAsset, original_response.json()["id"])
        source_before = self.service.storage.resolve(original.filepath).read_bytes()
        edited_response = self._trim(original.id)
        self.assertEqual(edited_response.status_code, 201)
        edited = self.db.get(MediaAsset, edited_response.json()["id"])
        self.assertEqual((edited.parent_asset_id, edited.version_number, edited.operation), (original.id, 2, "trim"))
        self.assertEqual(edited.operation_params, {"operation":"trim", "start":2.0, "end":12.0})
        self.assertEqual(self.service.storage.resolve(original.filepath).read_bytes(), source_before)
        self.assertTrue(self.service.storage.resolve(edited.filepath).is_file())
        self.assertEqual(self.client.get(f"/media/assets/{edited.id}/download").status_code, 200)

        reopened = self._trim(edited.id, {"operation":"trim", "start":1, "end":10})
        self.assertEqual(reopened.status_code, 201)
        third = self.db.get(MediaAsset, reopened.json()["id"])
        self.assertEqual((third.parent_asset_id, third.version_number), (edited.id, 3))

    def test_reediting_old_video_version_uses_next_lineage_number(self):
        original = self.db.get(MediaAsset, self._register(self._upload().id).json()["id"])
        first_edit = self.db.get(MediaAsset, self._trim(original.id).json()["id"])
        branch_edit = self.db.get(MediaAsset, self._trim(original.id).json()["id"])

        self.assertEqual(first_edit.parent_asset_id, original.id)
        self.assertEqual(branch_edit.parent_asset_id, original.id)
        self.assertEqual(first_edit.version_number, 2)
        self.assertEqual(branch_edit.version_number, 3)
        self.assertTrue(self.service.storage.resolve(first_edit.filepath).is_file())
        self.assertTrue(self.service.storage.resolve(branch_edit.filepath).is_file())
    def test_aspect_crop_allowlist_preserves_source_and_continues_version_chain(self):
        original = self._register(self._upload().id).json()
        source = self.db.get(MediaAsset, original["id"])
        source_bytes = self.service.storage.resolve(source.filepath).read_bytes()
        for ratio in ("16:9", "9:16", "1:1", "4:5"):
            response = self._trim(source.id, {"operation": "aspect_crop", "aspect_ratio": ratio})
            self.assertEqual(response.status_code, 201)
            edited = self.db.get(MediaAsset, response.json()["id"])
            self.assertEqual(edited.operation_params["aspect_ratio"], ratio)
            self.assertEqual(edited.parent_asset_id, source.id)
            self.assertTrue(self.service.storage.resolve(edited.filepath).is_file())
            self.assertEqual(self.client.get(f"/media/assets/{edited.id}/download").status_code, 200)
        self.assertEqual(self.service.storage.resolve(source.filepath).read_bytes(), source_bytes)

    def test_aspect_crop_rejects_invalid_ratio(self):
        original = self._register(self._upload().id).json()
        response = self._trim(original["id"], {"operation": "aspect_crop", "aspect_ratio": "2:3"})
        self.assertEqual(response.status_code, 422)
    def test_text_overlay_and_cta_validate_timing_and_preserve_source(self):
        original = self._register(self._upload().id).json()
        source = self.db.get(MediaAsset, original["id"])
        source_bytes = self.service.storage.resolve(source.filepath).read_bytes()
        payload = {"operation": "cta_overlay", "text": "Mua ngay hôm nay", "start": 5, "end": 10,
                   "position": "bottom", "font_size": 54, "text_color": "yellow"}
        response = self._trim(original["id"], payload)
        self.assertEqual(response.status_code, 201)
        edited = self.db.get(MediaAsset, response.json()["id"])
        self.assertEqual(edited.operation, "cta_overlay")
        self.assertEqual(edited.operation_params["text"], "Mua ngay hôm nay")
        self.assertEqual(self.service.storage.resolve(source.filepath).read_bytes(), source_bytes)
        self.assertEqual(self._trim(original["id"], {**payload, "start": 19, "end": 25}).status_code, 422)
    def test_subtitle_supports_unicode_multiple_entries_and_validation(self):
        original = self._register(self._upload().id).json()
        source = self.db.get(MediaAsset, original["id"])
        source_bytes = self.service.storage.resolve(source.filepath).read_bytes()
        payload = {"operation": "subtitle", "position": "bottom", "entries": [
            {"text": "Xin chào Việt Nam", "start": 1, "end": 3},
            {"text": "Mua ngay hôm nay", "start": 5, "end": 8},
        ]}
        response = self._trim(original["id"], payload)
        self.assertEqual(response.status_code, 201)
        edited = self.db.get(MediaAsset, response.json()["id"])
        self.assertEqual(len(edited.operation_params["entries"]), 2)
        self.assertEqual(self.service.storage.resolve(source.filepath).read_bytes(), source_bytes)
        self.assertEqual(self.client.get(f"/media/assets/{edited.id}/download").status_code, 200)
        self.assertEqual(self._trim(original["id"], {"operation": "subtitle", "entries": [{"text": "", "start": 1, "end": 2}]}).status_code, 422)
        self.assertEqual(self._trim(original["id"], {"operation": "subtitle", "entries": [{"text": "Sai timing", "start": 9, "end": 25}]}).status_code, 422)
    def test_volume_and_mute_create_versions_and_preserve_source(self):
        original = self._register(self._upload().id).json()
        source = self.db.get(MediaAsset, original["id"])
        source_bytes = self.service.storage.resolve(source.filepath).read_bytes()
        for payload in ({"operation": "volume", "volume": 0.5}, {"operation": "mute"}):
            response = self._trim(original["id"], payload)
            self.assertEqual(response.status_code, 201)
            edited = self.db.get(MediaAsset, response.json()["id"])
            self.assertEqual(edited.operation, payload["operation"])
            self.assertTrue(self.service.storage.resolve(edited.filepath).is_file())
            self.assertEqual(self.client.get(f"/media/assets/{edited.id}/download").status_code, 200)
        self.assertEqual(self.service.storage.resolve(source.filepath).read_bytes(), source_bytes)

    def test_audio_rejects_invalid_volume_and_processor_failure_keeps_source(self):
        original = self._register(self._upload().id).json()
        source = self.db.get(MediaAsset, original["id"])
        source_bytes = self.service.storage.resolve(source.filepath).read_bytes()
        self.assertEqual(self._trim(source.id, {"operation": "volume", "volume": 5}).status_code, 422)
        self.assertEqual(self._trim(source.id, {"operation": "mute", "volume": 0}).status_code, 422)
        self.processor.fail = True
        self.assertEqual(self._trim(source.id, {"operation": "volume", "volume": 0.5}).status_code, 502)
        self.assertEqual(self.service.storage.resolve(source.filepath).read_bytes(), source_bytes)
    def test_merge_two_videos_preserves_both_sources_and_downloads_output(self):
        first = self._register(self._upload().id).json()
        second = self._register(self._upload().id).json()
        first_asset = self.db.get(MediaAsset, first["id"])
        second_asset = self.db.get(MediaAsset, second["id"])
        first_bytes = self.service.storage.resolve(first_asset.filepath).read_bytes()
        second_bytes = self.service.storage.resolve(second_asset.filepath).read_bytes()
        response = self._trim(first_asset.id, {"operation": "merge", "source_asset_ids": [first_asset.id, second_asset.id]})
        self.assertEqual(response.status_code, 201)
        merged = self.db.get(MediaAsset, response.json()["id"])
        self.assertEqual(merged.operation, "merge")
        self.assertEqual(merged.parent_asset_id, first_asset.id)
        self.assertTrue(self.service.storage.resolve(merged.filepath).is_file())
        self.assertEqual(self.client.get(f"/media/assets/{merged.id}/download").status_code, 200)
        self.assertEqual(self.service.storage.resolve(first_asset.filepath).read_bytes(), first_bytes)
        self.assertEqual(self.service.storage.resolve(second_asset.filepath).read_bytes(), second_bytes)

    def test_merge_rejects_duplicate_or_missing_source(self):
        first = self._register(self._upload().id).json()
        self.assertEqual(self._trim(first["id"], {"operation": "merge", "source_asset_ids": [first["id"], first["id"]]}).status_code, 422)
        self.assertEqual(self._trim(first["id"], {"operation": "merge", "source_asset_ids": [first["id"], 99999]}).status_code, 404)
    def test_aspect_dimensions_mismatch_fails_before_completed(self):
        original = self._register(self._upload().id).json()
        self.processor.aspect_output_dimensions = (640, 480)
        response = self._trim(original["id"], {"operation": "aspect_crop", "aspect_ratio": "9:16"})
        self.assertEqual(response.status_code, 502)
        failed = self.db.query(MediaAsset).order_by(MediaAsset.id.desc()).first()
        self.assertEqual(failed.status, "failed")
        self.assertIsNone(failed.filepath)

    def test_whitespace_only_text_is_rejected(self):
        original = self._register(self._upload().id).json()
        response = self._trim(original["id"], {"operation": "cta_overlay", "text": "   ", "start": 1, "end": 3})
        self.assertEqual(response.status_code, 422)

    def test_unexpected_processor_exception_marks_asset_failed(self):
        original = self._register(self._upload().id).json()
        source = self.db.get(MediaAsset, original["id"])
        source_bytes = self.service.storage.resolve(source.filepath).read_bytes()
        self.processor.unexpected = True
        response = self._trim(source.id, {"operation": "trim", "start": 1, "end": 3})
        self.assertEqual(response.status_code, 502)
        failed = self.db.query(MediaAsset).order_by(MediaAsset.id.desc()).first()
        self.assertEqual(failed.status, "failed")
        self.assertIsNone(failed.filepath)
        self.assertEqual(self.service.storage.resolve(source.filepath).read_bytes(), source_bytes)

    def test_invalid_source_signature_is_rejected_during_registration(self):
        uploaded = self._upload()
        self.service.storage.resolve(uploaded.filepath).write_bytes(b"not-a-video")
        response = self._register(uploaded.id)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.db.query(MediaAsset).count(), 0)
    def test_mute_fails_when_output_audio_state_does_not_match_contract(self):
        original = self._register(self._upload().id).json()
        self.processor.output_has_audio = False
        response = self._trim(original["id"], {"operation": "mute"})
        self.assertEqual(response.status_code, 502)
        failed = self.db.query(MediaAsset).order_by(MediaAsset.id.desc()).first()
        self.assertEqual(failed.status, "failed")

    def test_merge_incompatible_dimensions_rejected_before_processor(self):
        first = self._register(self._upload().id).json()
        second = self._register(self._upload().id).json()
        second_asset = self.db.get(MediaAsset, second["id"])
        second_path = self.service.storage.resolve(second_asset.filepath)
        self.processor.probe_overrides[str(second_path)] = (640, 480)
        response = self._trim(first["id"], {"operation": "merge", "source_asset_ids": [first["id"], second["id"]]})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.db.query(MediaAsset).count(), 2)
    def test_rejects_invalid_operation_and_invalid_parameters(self):
        original = self._register(self._upload().id).json()
        self.assertEqual(self._trim(original["id"], {"operation":"shell", "command":"rm -rf /"}).status_code, 422)
        self.assertEqual(self._trim(original["id"], {"operation":"trim", "start":9, "end":2}).status_code, 422)
        self.assertEqual(self._trim(original["id"], {"operation":"trim", "start":0, "end":25}).status_code, 422)

    def test_blocks_cross_user_cross_conversation_and_non_video_source(self):
        original = self._register(self._upload().id).json()
        self.current_user = self.other
        self.assertEqual(self._trim(original["id"], conversation=self.foreign_conversation).status_code, 404)
        self.current_user = self.owner
        self.assertEqual(self._trim(original["id"], conversation=self.other_conversation).status_code, 404)
        image = self._upload(content_type="image/png")
        self.assertEqual(self._register(image.id).status_code, 400)

    def test_processor_failure_marks_version_failed_and_keeps_source(self):
        original = self._register(self._upload().id).json()
        source = self.db.get(MediaAsset, original["id"])
        source_bytes = self.service.storage.resolve(source.filepath).read_bytes()
        self.processor.fail = True
        result = self._trim(source.id)
        self.assertEqual(result.status_code, 502)
        failed = self.db.query(MediaAsset).order_by(MediaAsset.id.desc()).first()
        self.assertEqual(failed.status, "failed")
        self.assertIsNone(failed.filepath)
        self.assertEqual(self.service.storage.resolve(source.filepath).read_bytes(), source_bytes)


    def test_registration_error_is_sanitized(self):
        uploaded = self._upload()
        self.processor.fail = True
        response = self._register(uploaded.id)
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("processor unavailable", response.text)
        self.assertNotIn(str(self.service.storage.root), response.text)
        self.assertEqual(self.db.query(MediaAsset).count(), 0)

    def test_edit_error_message_is_sanitized(self):
        original = self._register(self._upload().id).json()
        self.processor.fail = True
        response = self._trim(original["id"])
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("processor unavailable", response.text)
        failed = self.db.query(MediaAsset).order_by(MediaAsset.id.desc()).first()
        self.assertEqual(failed.error_message, "Video trim failed")
        self.assertNotIn(str(self.service.storage.root), failed.error_message)

    def test_failed_state_commit_failure_does_not_hide_original_error(self):
        original = self._register(self._upload().id).json()
        self.processor.fail = True
        real_commit = self.db.commit
        commit_calls = 0

        def commit_with_failure():
            nonlocal commit_calls
            commit_calls += 1
            if commit_calls == 2:
                raise RuntimeError("database failure at private path")
            return real_commit()

        with patch.object(self.db, "commit", side_effect=commit_with_failure):
            response = self._trim(original["id"])
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("database failure", response.text)
        failed = self.db.query(MediaAsset).order_by(MediaAsset.id.desc()).first()
        self.assertEqual(failed.status, "processing")

    def test_trim_duration_is_validated_and_persisted(self):
        original = self._register(self._upload().id).json()
        response = self._trim(original["id"], {"operation": "trim", "start": 2, "end": 12})
        self.assertEqual(response.status_code, 201)
        edited = self.db.get(MediaAsset, response.json()["id"])
        self.assertAlmostEqual(edited.duration_seconds, 10.0)

        self.processor.trim_output_duration_override = 20.0
        mismatch = self._trim(original["id"], {"operation": "trim", "start": 2, "end": 12})
        self.assertEqual(mismatch.status_code, 502)
        failed = self.db.query(MediaAsset).order_by(MediaAsset.id.desc()).first()
        self.assertEqual(failed.status, "failed")
        self.assertEqual(failed.error_message, "Video trim failed")

    def test_invalid_output_duration_is_rejected(self):
        original = self._register(self._upload().id).json()
        self.processor.force_invalid_output_duration = True
        response = self._trim(original["id"], {"operation": "volume", "volume": 0.5})
        self.assertEqual(response.status_code, 502)
        failed = self.db.query(MediaAsset).order_by(MediaAsset.id.desc()).first()
        self.assertEqual(failed.status, "failed")
        self.assertEqual(failed.error_message, "Video volume failed")

    def test_referenced_upload_cannot_be_deleted(self):
        uploaded = self._upload()
        registered = self._register(uploaded.id)
        self.assertEqual(registered.status_code, 201)
        path = self.service.storage.resolve(uploaded.filepath)
        with self.assertRaises(HTTPException) as context:
            upload_service.delete_uploaded_file_service(
                file_id=uploaded.id,
                db=self.db,
                current_user=self.owner,
            )
        self.assertEqual(context.exception.status_code, 409)
        self.assertTrue(path.is_file())
        self.assertIsNotNone(self.db.get(UploadedFile, uploaded.id))
        self.assertIsNotNone(self.db.get(MediaAsset, registered.json()["id"]))

    def test_unreferenced_upload_can_still_be_deleted(self):
        uploaded = self._upload()
        path = self.service.storage.resolve(uploaded.filepath)
        result = upload_service.delete_uploaded_file_service(
            file_id=uploaded.id,
            db=self.db,
            current_user=self.owner,
        )
        self.assertEqual(result["message"], "Xóa tệp thành công")
        self.assertFalse(path.exists())
        self.assertIsNone(self.db.get(UploadedFile, uploaded.id))

if __name__ == "__main__":
    unittest.main()
