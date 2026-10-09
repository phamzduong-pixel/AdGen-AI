import asyncio
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI, UploadFile
from fastapi.testclient import TestClient
from starlette.datastructures import Headers

from app.api.video_stt import router as video_stt_router
from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User
from app.services.stt.models import (
    STTAudioTooLongError,
    STTError,
    STTProviderNotConfiguredError,
    TranscriptionResult,
)
from app.services.stt.providers.base import BaseSTTProvider
from app.services.stt.providers.unavailable import UnavailableSTTProvider
from app.services.stt.service import STTService
from app.services.voice_conversion.models import VoiceConversionAudioTooLongError
from app.services.voice_studio.video_input import (
    VideoDurationTooLongError,
    VideoInputMetadata,
    VideoMimeMismatchError,
    VideoNoAudioStreamError,
    VideoSignatureInvalidError,
    VideoTooLargeError,
    VoiceStudioVideoInputService,
    VoiceStudioVideoProbe,
)
from app.services.voice_studio.video_to_stt import (
    FFmpegNotConfiguredError,
    VideoAudioExtractionFailedError,
    VideoAudioExtractionTimeoutError,
    VideoExtractedAudioInvalidError,
    VideoToSTTService,
)


def make_upload(
    filename: str,
    content_type: str,
    content: bytes,
) -> UploadFile:
    return UploadFile(
        file=io.BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


def valid_mp4_header() -> bytes:
    return b"\x00\x00\x00\x18ftypisom" + b"video-bytes"


class FakeVideoProbe:
    def __init__(self, *, has_audio: bool = True, duration: float = 1.0):
        self.metadata = VideoInputMetadata(
            container_format="mov,mp4",
            video_codec="h264",
            duration_seconds=duration,
            width=16,
            height=16,
            has_audio=has_audio,
            audio_codec="aac" if has_audio else None,
        )

    def validate_path(self, source_path, *, extension, content_type):
        return self.metadata


class RecordingProvider(BaseSTTProvider):
    provider_id = "video-unit-provider"

    def __init__(self):
        self.paths: list[Path] = []
        self.content_types: list[str] = []

    async def transcribe(self, audio_path, *, content_type, language):
        self.paths.append(audio_path)
        self.content_types.append(content_type)
        return TranscriptionResult(
            transcript="Transcript tu video",
            language=language,
            provider=self.provider_id,
            metadata={"fixture": True},
        )


class RaisingProvider(BaseSTTProvider):
    provider_id = "video-raising-provider"

    async def transcribe(self, audio_path, *, content_type, language):
        raise RuntimeError("provider internals must not leak")


class FakeProcess:
    def __init__(self, *, returncode: int | None = 0, timeout: bool = False):
        self.returncode = returncode
        self.timeout = timeout
        self.killed = False

    def wait(self, timeout=None):
        if self.timeout:
            raise subprocess.TimeoutExpired("ffmpeg", timeout)
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -9


class VideoToSTTServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ffmpeg_binary = shutil.which(settings.FFMPEG_BINARY)
        cls.ffprobe_binary = shutil.which(settings.FFPROBE_BINARY)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.original_max_size = settings.MAX_VIDEO_SIZE
        self.original_max_duration = settings.MAX_VIDEO_DURATION_SECONDS

    def tearDown(self):
        settings.MAX_VIDEO_SIZE = self.original_max_size
        settings.MAX_VIDEO_DURATION_SECONDS = self.original_max_duration
        self.temp_dir.cleanup()

    def _make_real_video(self, *, with_audio: bool = True) -> Path:
        if not self.ffmpeg_binary or not self.ffprobe_binary:
            self.skipTest("FFmpeg/FFprobe are not available")
        output = self.root / "fixture.mp4"
        args = [
            self.ffmpeg_binary,
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=16x16:r=2:d=0.5",
        ]
        if with_audio:
            args.extend(
                [
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:sample_rate=8000:d=0.5",
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                ]
            )
        else:
            args.extend(["-map", "0:v:0"])
        args.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p"])
        if with_audio:
            args.extend(["-c:a", "aac"])
        args.extend(["-movflags", "+faststart", str(output)])
        subprocess.run(args, check=True, capture_output=True, timeout=30)
        return output

    def _service(
        self,
        *,
        probe=None,
        provider=None,
        ffmpeg_binary=None,
        timeout=30,
    ):
        video_input = VoiceStudioVideoInputService(
            probe=probe or FakeVideoProbe(),
            temp_dir=self.root,
        )
        transcription = STTService(provider=provider or RecordingProvider())
        return VideoToSTTService(
            video_input=video_input,
            transcription_service=transcription,
            ffmpeg_binary=ffmpeg_binary or self.ffmpeg_binary or "ffmpeg",
            extraction_timeout_seconds=timeout,
            temp_dir=self.root,
        )

    def test_real_video_audio_is_extracted_and_delegated_to_existing_stt(self):
        source = self._make_real_video(with_audio=True)
        provider = RecordingProvider()
        service = self._service(
            probe=VoiceStudioVideoProbe(),
            provider=provider,
            timeout=30,
        )

        result = asyncio.run(
            service.transcribe_upload(
                make_upload("clip.mp4", "video/mp4", source.read_bytes()),
                language="vi-VN",
            )
        )

        self.assertEqual(result.transcript, "Transcript tu video")
        self.assertEqual(result.provider, "video-unit-provider")
        self.assertEqual(result.metadata["source_type"], "video")
        self.assertEqual(provider.content_types, ["audio/flac"])
        self.assertEqual(len(provider.paths), 1)
        self.assertFalse(provider.paths[0].exists())
        self.assertEqual([path.name for path in self.root.iterdir()], [source.name])

    def test_video_without_audio_is_rejected_before_stt(self):
        provider = RecordingProvider()
        service = self._service(probe=FakeVideoProbe(has_audio=False), provider=provider)

        with self.assertRaises(VideoNoAudioStreamError):
            asyncio.run(
                service.transcribe_upload(
                    make_upload("clip.mp4", "video/mp4", valid_mp4_header()),
                )
            )

        self.assertEqual(provider.paths, [])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_validation_rejects_signature_extension_mime_and_size(self):
        provider = RecordingProvider()
        service = self._service(
            probe=VoiceStudioVideoProbe(),
            provider=provider,
        )

        invalid_upload = make_upload("clip.mp4", "video/mp4", b"not-video")
        with self.assertRaises(VideoSignatureInvalidError):
            asyncio.run(service.transcribe_upload(invalid_upload))
        self.assertTrue(invalid_upload.file.closed)
        with self.assertRaises(VideoMimeMismatchError):
            asyncio.run(
                service.transcribe_upload(
                    make_upload("clip.mp4", "video/webm", valid_mp4_header()),
                )
            )
        with self.assertRaises(Exception) as unsupported:
            asyncio.run(
                service.transcribe_upload(
                    make_upload("clip.avi", "video/avi", b"data"),
                )
            )
        self.assertEqual(unsupported.exception.code, "VIDEO_UNSUPPORTED_FORMAT")

        settings.MAX_VIDEO_SIZE = 3
        with self.assertRaises(VideoTooLargeError):
            asyncio.run(
                service.transcribe_upload(
                    make_upload("clip.mp4", "video/mp4", valid_mp4_header()),
                )
            )
        self.assertEqual(provider.paths, [])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_over_duration_is_rejected_before_extraction(self):
        source = self._make_real_video(with_audio=True)
        probe = VoiceStudioVideoProbe()
        payload = json.dumps(
            {
                "streams": [
                    {"codec_type": "video", "codec_name": "h264", "width": 16, "height": 16},
                    {"codec_type": "audio", "codec_name": "aac"},
                ],
                "format": {"format_name": "mov,mp4", "duration": "301"},
            }
        ).encode()
        service = self._service(probe=probe)

        with patch.object(probe, "_run_bounded", return_value=payload):
            with self.assertRaises(VideoDurationTooLongError):
                asyncio.run(
                    service.transcribe_upload(
                        make_upload("clip.mp4", "video/mp4", source.read_bytes()),
                    )
                )

    def test_missing_ffmpeg_is_configuration_error_and_cleans_video(self):
        service = self._service(ffmpeg_binary="missing-ffmpeg-for-test")

        with self.assertRaises(FFmpegNotConfiguredError):
            asyncio.run(
                service.transcribe_upload(
                    make_upload("clip.mp4", "video/mp4", valid_mp4_header()),
                )
            )
        self.assertEqual(list(self.root.iterdir()), [])

    def test_extraction_timeout_and_failure_cleanup(self):
        service = self._service()
        timeout_process = FakeProcess(timeout=True)
        with patch(
            "app.services.voice_studio.video_to_stt.subprocess.Popen",
            return_value=timeout_process,
        ):
            with self.assertRaises(VideoAudioExtractionTimeoutError):
                asyncio.run(
                    service.transcribe_upload(
                        make_upload("clip.mp4", "video/mp4", valid_mp4_header()),
                    )
                )
        self.assertTrue(timeout_process.killed)
        self.assertEqual(list(self.root.iterdir()), [])

        failure_process = FakeProcess(returncode=1)
        with patch(
            "app.services.voice_studio.video_to_stt.subprocess.Popen",
            return_value=failure_process,
        ):
            with self.assertRaises(VideoAudioExtractionFailedError):
                asyncio.run(
                    service.transcribe_upload(
                        make_upload("clip.mp4", "video/mp4", valid_mp4_header()),
                    )
                )
        self.assertEqual(list(self.root.iterdir()), [])

    def test_empty_and_invalid_extracted_audio_never_call_stt(self):
        provider = RecordingProvider()
        service = self._service(provider=provider)
        with patch.object(service, "_extract_audio", return_value=None):
            with self.assertRaises(VideoExtractedAudioInvalidError):
                asyncio.run(
                    service.transcribe_upload(
                        make_upload("clip.mp4", "video/mp4", valid_mp4_header()),
                    )
                )

        def write_invalid_audio(_validated, output_path):
            output_path.write_bytes(b"not-flac")

        with patch.object(service, "_extract_audio", side_effect=write_invalid_audio):
            with self.assertRaises(VideoExtractedAudioInvalidError):
                asyncio.run(
                    service.transcribe_upload(
                        make_upload("clip.mp4", "video/mp4", valid_mp4_header()),
                    )
                )
        self.assertEqual(provider.paths, [])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_extracted_audio_over_60_seconds_is_rejected_before_stt(self):
        provider = RecordingProvider()
        service = self._service(provider=provider)

        def write_audio(_validated, output_path):
            output_path.write_bytes(b"extracted-audio")

        with patch.object(service, "_extract_audio", side_effect=write_audio), patch(
            "app.services.voice_studio.video_to_stt.probe_audio_file",
            side_effect=VoiceConversionAudioTooLongError,
        ):
            with self.assertRaises(STTAudioTooLongError):
                asyncio.run(
                    service.transcribe_upload(
                        make_upload("clip.mp4", "video/mp4", valid_mp4_header()),
                    )
                )

        self.assertEqual(provider.paths, [])
        self.assertEqual(list(self.root.iterdir()), [])
    def test_provider_unavailable_and_failure_cleanup(self):
        source = self._make_real_video(with_audio=True)
        source_bytes = source.read_bytes()
        unavailable_service = self._service(
            provider=UnavailableSTTProvider("test provider unavailable")
        )
        with self.assertRaises(STTProviderNotConfiguredError):
            asyncio.run(
                unavailable_service.transcribe_upload(
                    make_upload("clip.mp4", "video/mp4", source_bytes),
                )
            )
        self.assertEqual([path.name for path in self.root.iterdir()], [source.name])

        failing_service = self._service(provider=RaisingProvider())
        with self.assertRaises(STTError):
            asyncio.run(
                failing_service.transcribe_upload(
                    make_upload("clip.mp4", "video/mp4", source_bytes),
                )
            )
        self.assertEqual([path.name for path in self.root.iterdir()], [source.name])

    def test_missing_ffprobe_is_reported_by_existing_video_validator(self):
        source = self._make_real_video(with_audio=True)
        probe = VoiceStudioVideoProbe(ffprobe_binary="missing-ffprobe-for-test")
        service = self._service(probe=probe)

        with self.assertRaises(Exception) as context:
            asyncio.run(
                service.transcribe_upload(
                    make_upload("clip.mp4", "video/mp4", source.read_bytes()),
                )
            )
        self.assertEqual(context.exception.code, "FFPROBE_NOT_CONFIGURED")
        self.assertEqual([path.name for path in self.root.iterdir()], [source.name])


class VideoSTTApiTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(video_stt_router)
        self.user = User(
            username="video-stt-owner",
            email="video-stt-owner@example.com",
            hashed_password="unused",
            email_verified=True,
        )
        self.app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close()

    def test_authenticated_endpoint_uses_existing_response_contract(self):
        result = TranscriptionResult(
            transcript="Video transcript",
            language="vi-VN",
            provider="unit-provider",
            metadata={"source_type": "video", "video_has_audio": True},
        )
        with patch(
            "app.api.video_stt.video_to_stt_service.transcribe_upload",
            new=AsyncMock(return_value=result),
        ) as transcribe:
            response = self.client.post(
                "/stt/transcribe-video",
                files={"file": ("clip.mp4", io.BytesIO(valid_mp4_header()), "video/mp4")},
                data={"language": "vi-VN"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["transcript"], "Video transcript")
        self.assertEqual(response.json()["provider"], "unit-provider")
        transcribe.assert_awaited_once()

    def test_endpoint_requires_authentication(self):
        self.app.dependency_overrides.clear()
        response = self.client.post(
            "/stt/transcribe-video",
            files={"file": ("clip.mp4", io.BytesIO(valid_mp4_header()), "video/mp4")},
        )
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
