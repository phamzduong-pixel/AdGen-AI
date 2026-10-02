import unittest
import tempfile
from pathlib import Path

from fastapi import FastAPI
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
from app.models.media_job import MediaJob
from app.models.user import User
from app.services.media.providers.video_generation import (
    GeneratedVideo,
    VideoGenerationProviderError,
    UnavailableVideoGenerationProvider,
    VideoGenerationInput,
    VideoGenerationProvider,
    VideoGenerationStatus,
    VideoGenerationSubmission,
)
from app.services.media.video_generation_service import VideoGenerationService
from app.services.media.video_processor import VideoMetadata
from app.services.media.video_service import VideoService


VALID_MP4 = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00"


class FakeVideoProcessor:
    def __init__(self):
        self.duration = 8.0
        self.width = 1280
        self.height = 720

    def probe(self, path):
        return VideoMetadata(
            self.duration, self.width, self.height, "video/mp4", True, "aac", "h264", "mov,mp4"
        )

class FakeVideoProvider(VideoGenerationProvider):
    def __init__(self, output=None):
        self.output = output or GeneratedVideo(VALID_MP4, "video/mp4")
        self.submissions = []
        self.references = []

    @property
    def provider_id(self):
        return "test-video-provider"

    @property
    def model_name(self):
        return "test-video-model"

    async def submit(self, request: VideoGenerationInput):
        self.references.append(request.references)
        self.submissions.append(request)
        return VideoGenerationSubmission("provider-job-1", "processing")

    async def get_status(self, provider_job_id: str):
        return VideoGenerationStatus(provider_job_id, "completed")

    async def retrieve_result(self, provider_job_id: str):
        return self.output


class TimeoutVideoProvider(FakeVideoProvider):
    async def submit(self, request: VideoGenerationInput):
        raise TimeoutError("provider timeout")


class QuotaVideoProvider(FakeVideoProvider):
    async def submit(self, request: VideoGenerationInput):
        error = VideoGenerationProviderError("Gemini không thể submit Veo video (429 RESOURCE_EXHAUSTED)")
        error.status_code = 429
        raise error


class FailedAfterSubmissionProvider(FakeVideoProvider):
    async def get_status(self, provider_job_id: str):
        return VideoGenerationStatus(provider_job_id, "failed", "provider operation failed")


class PollTimeoutVideoProvider(FakeVideoProvider):
    async def get_status(self, provider_job_id: str):
        raise TimeoutError("poll timeout")


class RetrieveFailureVideoProvider(FakeVideoProvider):
    async def retrieve_result(self, provider_job_id: str):
        raise RuntimeError("download failed")

class VideoGenerationApiTest(unittest.TestCase):
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
        self.original_upload_dir = settings.UPLOAD_DIR
        self.original_generation_service = media_api.video_generation_service
        self.original_media_storage = media_api.media_service.storage
        settings.UPLOAD_DIR = Path(self.temp_dir.name) / "uploads"
        self.provider = FakeVideoProvider()
        self.video_service = VideoService(processor=FakeVideoProcessor())
        self.generation_service = VideoGenerationService(
            provider=self.provider, video_service=self.video_service
        )
        media_api.video_generation_service = self.generation_service
        media_api.media_service.storage = self.video_service.storage
        self.owner = User(
            username="video-ai-owner",
            email="video-ai-owner@example.com",
            hashed_password="unused",
        )
        self.other = User(
            username="video-ai-other",
            email="video-ai-other@example.com",
            hashed_password="unused",
        )
        self.db.add_all([self.owner, self.other])
        self.db.commit()
        self.owner_conversation = self._conversation(self.owner)
        self.other_conversation = self._conversation(self.other)
        self.current_user = self.owner
        app = FastAPI()
        app.include_router(media_api.router)

        def override_db():
            yield self.db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: self.current_user
        self.client = TestClient(app)

    def tearDown(self):
        media_api.video_generation_service = self.original_generation_service
        media_api.media_service.storage = self.original_media_storage
        settings.UPLOAD_DIR = self.original_upload_dir
        self.db.close()
        self.temp_dir.cleanup()

    def _conversation(self, user):
        conversation = Conversation(title="Video AI", user_id=user.id)
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def _create(self, conversation_id=None, **payload):
        body = {"prompt": "Tạo video quảng cáo sản phẩm", "aspect_ratio": "16:9"}
        body.update(payload)
        return self.client.post(
            f"/media/conversations/{conversation_id or self.owner_conversation.id}/video-jobs",
            json=body,
        )

    def test_create_poll_and_download_completed_output(self):
        response = self._create(duration_seconds=8)
        self.assertEqual(response.status_code, 202)
        job = self.db.get(MediaJob, response.json()["id"])
        self.assertEqual(job.status, "processing")
        self.assertEqual(job.provider_job_id, "provider-job-1")

        completed = self.client.get(f"/media/jobs/{job.id}")
        self.assertEqual(completed.status_code, 200)
        data = completed.json()
        self.assertEqual(data["status"], "completed")
        self.assertIsNotNone(data["output_asset_id"])
        asset = self.db.get(MediaAsset, data["output_asset_id"])
        self.assertEqual(asset.status, "completed")
        self.assertEqual(asset.filepath.split("/")[0], "generated-videos")
        self.assertEqual(self.client.get(f"/media/assets/{asset.id}/download").content, VALID_MP4)

    def test_reference_assets_are_scoped_and_sent_as_bytes(self):
        path = settings.UPLOAD_DIR / "reference.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"reference")
        reference = MediaAsset(
            user_id=self.owner.id,
            conversation_id=self.owner_conversation.id,
            kind="image",
            operation="generate",
            status="completed",
            prompt="reference",
            content_type="image/png",
            filepath="reference.png",
            size=9,
        )
        self.db.add(reference)
        self.db.commit()
        response = self._create(reference_asset_ids=[reference.id])
        self.assertEqual(response.status_code, 202)
        self.assertEqual(self.provider.references[-1][0], (b"reference", "image/png"))

        cross_conversation = self._create(
            self.other_conversation.id, reference_asset_ids=[reference.id]
        )
        self.assertEqual(cross_conversation.status_code, 404)

    def test_provider_unavailable_creates_failed_job_without_fake_asset(self):
        media_api.video_generation_service = VideoGenerationService(
            provider=UnavailableVideoGenerationProvider(),
            video_service=self.video_service,
        )
        response = self._create()
        self.assertEqual(response.status_code, 202)
        job = self.db.get(MediaJob, response.json()["id"])
        self.assertEqual(job.status, "failed")
        self.assertIsNone(job.output_asset_id)
        self.assertEqual(self.db.query(MediaAsset).count(), 0)

    def test_invalid_provider_output_fails_job(self):
        self.provider.output = GeneratedVideo(b"not-video", "video/mp4")
        response = self._create()
        self.assertEqual(response.status_code, 202)
        job = self.db.get(MediaJob, response.json()["id"])
        self.assertEqual(job.status, "processing")
        failed = self.client.get(f"/media/jobs/{job.id}")
        self.assertEqual(failed.json()["status"], "failed")
        self.assertIsNone(failed.json()["output_asset_id"])

    def test_provider_submission_timeout_marks_job_failed(self):
        media_api.video_generation_service = VideoGenerationService(
            provider=TimeoutVideoProvider(),
            video_service=self.video_service,
        )
        response = self._create()
        self.assertEqual(response.status_code, 202)
        job = self.db.get(MediaJob, response.json()["id"])
        self.assertEqual(job.status, "failed")
        self.assertIsNone(job.output_asset_id)

    def test_http_429_submission_marks_job_failed_without_asset(self):
        media_api.video_generation_service = VideoGenerationService(
            provider=QuotaVideoProvider(),
            video_service=self.video_service,
        )
        response = self._create()
        self.assertEqual(response.status_code, 202)
        job = self.db.get(MediaJob, response.json()["id"])
        self.assertEqual(job.status, "failed")
        self.assertIn("429", job.error_message)
        self.assertIsNone(job.provider_job_id)
        self.assertIsNone(job.output_asset_id)
        self.assertEqual(self.db.query(MediaAsset).count(), 0)

    def test_provider_failure_after_operation_id_marks_job_failed(self):
        media_api.video_generation_service = VideoGenerationService(
            provider=FailedAfterSubmissionProvider(),
            video_service=self.video_service,
        )
        response = self._create()
        job = self.db.get(MediaJob, response.json()["id"])
        self.assertEqual(job.status, "processing")
        self.assertEqual(job.provider_job_id, "provider-job-1")
        failed = self.client.get(f"/media/jobs/{job.id}")
        self.assertEqual(failed.status_code, 200)
        self.assertEqual(failed.json()["status"], "failed")
        self.assertEqual(failed.json()["error_message"], "provider operation failed")
        self.assertIsNone(failed.json()["output_asset_id"])

    def test_poll_timeout_marks_existing_job_failed(self):
        media_api.video_generation_service = VideoGenerationService(
            provider=PollTimeoutVideoProvider(),
            video_service=self.video_service,
        )
        response = self._create()
        job = self.db.get(MediaJob, response.json()["id"])
        failed = self.client.get(f"/media/jobs/{job.id}")
        self.assertEqual(failed.json()["status"], "failed")
        self.assertIn("poll timeout", failed.json()["error_message"])
        self.assertIsNone(failed.json()["output_asset_id"])

    def test_retrieve_failure_does_not_create_completed_asset(self):
        media_api.video_generation_service = VideoGenerationService(
            provider=RetrieveFailureVideoProvider(),
            video_service=self.video_service,
        )
        response = self._create()
        job = self.db.get(MediaJob, response.json()["id"])
        failed = self.client.get(f"/media/jobs/{job.id}")
        self.assertEqual(failed.json()["status"], "failed")
        self.assertIn("download failed", failed.json()["error_message"])
        self.assertIsNone(failed.json()["output_asset_id"])
        self.assertEqual(self.db.query(MediaAsset).count(), 0)

    def test_job_list_is_scoped_to_owner_and_conversation(self):
        same_user_conversation = self._conversation(self.owner)
        owner_job = self._create()
        same_conversation_job = self._create(same_user_conversation.id)

        owner_jobs = self.client.get(
            f"/media/conversations/{self.owner_conversation.id}/video-jobs"
        )
        self.assertEqual(owner_jobs.status_code, 200)
        self.assertEqual([job["id"] for job in owner_jobs.json()], [owner_job.json()["id"]])

        same_jobs = self.client.get(
            f"/media/conversations/{same_user_conversation.id}/video-jobs"
        )
        self.assertEqual(same_jobs.status_code, 200)
        self.assertEqual([job["id"] for job in same_jobs.json()], [same_conversation_job.json()["id"]])

        self.current_user = self.other
        self.assertEqual(
            self.client.get(
                f"/media/conversations/{self.owner_conversation.id}/video-jobs"
            ).status_code,
            404,
        )
    def test_invalid_output_mime_size_duration_and_aspect_fail_job(self):
        for output in (GeneratedVideo(VALID_MP4, "video/webm"), GeneratedVideo(b"bad", "video/mp4")):
            self.provider.output = output
            response = self._create()
            job_id = response.json()["id"]
            self.assertEqual(self.client.get(f"/media/jobs/{job_id}").json()["status"], "failed")

        original_size = settings.MAX_VIDEO_SIZE
        try:
            settings.MAX_VIDEO_SIZE = 4
            self.provider.output = GeneratedVideo(VALID_MP4, "video/mp4")
            response = self._create()
            job_id = response.json()["id"]
            self.assertEqual(self.client.get(f"/media/jobs/{job_id}").json()["status"], "failed")
        finally:
            settings.MAX_VIDEO_SIZE = original_size

        self.video_service.processor.duration = 301
        response = self._create()
        job_id = response.json()["id"]
        self.assertEqual(self.client.get(f"/media/jobs/{job_id}").json()["status"], "failed")
        self.video_service.processor.duration = 4
        self.video_service.processor.width = 1000
        self.video_service.processor.height = 1000
        response = self._create()
        job_id = response.json()["id"]
        self.assertEqual(self.client.get(f"/media/jobs/{job_id}").json()["status"], "failed")

    def test_invalid_request_and_cross_user_job_access_are_rejected(self):
        self.assertEqual(self._create(prompt="x").status_code, 422)
        response = self._create()
        job_id = response.json()["id"]
        self.current_user = self.other
        self.assertEqual(self.client.get(f"/media/jobs/{job_id}").status_code, 404)


if __name__ == "__main__":
    unittest.main()
