import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import UploadFile
from starlette.datastructures import Headers

from app.core.config import settings
from app.services.voice_studio.video_input import (
    FFProbeFailedError,
    FFProbeNotConfiguredError,
    FFProbeTimeoutError,
    PROBE_OUTPUT_MAX_BYTES,
    VideoDurationInvalidError,
    VideoDurationTooLongError,
    VideoEmptyError,
    VideoInputError,
    VideoMimeMismatchError,
    VideoNoVideoStreamError,
    VideoSignatureInvalidError,
    VideoTooLargeError,
    VideoUnsupportedFormatError,
    VoiceStudioVideoInputService,
    VoiceStudioVideoProbe,
)


def make_upload(filename: str, content_type: str, content: bytes) -> UploadFile:
    return UploadFile(
        file=io.BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


class _FakeProbeProcess:
    def __init__(self, output: bytes):
        self.stdout = io.BytesIO(output)
        self.returncode: int | None = None

    def poll(self):
        return self.returncode

    def kill(self):
        self.returncode = -9

    def wait(self, timeout=None):
        return self.returncode


class VideoInputValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ffmpeg_binary = shutil.which(settings.FFMPEG_BINARY)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.original_max_size = settings.MAX_VIDEO_SIZE
        self.original_max_duration = settings.MAX_VIDEO_DURATION_SECONDS

    def tearDown(self):
        settings.MAX_VIDEO_SIZE = self.original_max_size
        settings.MAX_VIDEO_DURATION_SECONDS = self.original_max_duration
        self.temp_dir.cleanup()

    def _require_ffmpeg(self):
        if not self.ffmpeg_binary:
            self.skipTest("FFmpeg is not available in the current environment")

    def _make_video(self, extension: str, *, with_audio: bool = False) -> Path:
        self._require_ffmpeg()
        output = self.root / f"fixture{extension}"
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
        if extension == ".webm":
            args.extend(["-c:v", "libvpx-vp9"])
            if with_audio:
                args.extend(["-c:a", "libopus"])
        else:
            args.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p"])
            if with_audio:
                args.extend(["-c:a", "aac"])
            args.extend(["-movflags", "+faststart"])
        args.append(str(output))
        subprocess.run(args, check=True, capture_output=True, timeout=30)
        return output

    def test_real_ffprobe_validates_mp4_mov_and_webm(self):
        probe = VoiceStudioVideoProbe()
        for extension, content_type in (
            (".mp4", "video/mp4"),
            (".mov", "video/quicktime"),
            (".webm", "video/webm"),
        ):
            with self.subTest(extension=extension):
                path = self._make_video(extension)
                metadata = probe.validate_path(
                    path,
                    extension=extension,
                    content_type=content_type,
                )
                self.assertGreater(metadata.duration_seconds, 0)
                self.assertEqual((metadata.width, metadata.height), (16, 16))
                self.assertFalse(metadata.has_audio)

    def test_real_ffprobe_records_optional_audio_stream(self):
        path = self._make_video(".mp4", with_audio=True)
        metadata = VoiceStudioVideoProbe().validate_path(
            path,
            extension=".mp4",
            content_type="video/mp4",
        )

        self.assertTrue(metadata.has_audio)
        self.assertEqual(metadata.audio_codec, "aac")

    def test_validation_service_cleans_temporary_video(self):
        source = self._make_video(".mp4")
        upload_dir = self.root / "temporary-upload"
        upload_dir.mkdir()
        service = VoiceStudioVideoInputService(temp_dir=upload_dir)

        metadata = __import__("asyncio").run(
            service.validate_upload(
                make_upload("clip.mp4", "video/mp4", source.read_bytes())
            )
        )

        self.assertGreater(metadata.duration_seconds, 0)
        self.assertEqual(list(upload_dir.iterdir()), [])

    def test_extension_mime_signature_and_empty_validation(self):
        service = VoiceStudioVideoInputService(temp_dir=self.root)
        with self.assertRaises(VideoUnsupportedFormatError):
            __import__("asyncio").run(
                service.validate_upload(make_upload("clip.avi", "video/avi", b"data"))
            )
        with self.assertRaises(VideoMimeMismatchError):
            __import__("asyncio").run(
                service.validate_upload(make_upload("clip.mp4", "video/webm", b"data"))
            )
        with self.assertRaises(VideoEmptyError):
            __import__("asyncio").run(
                service.validate_upload(make_upload("clip.mp4", "video/mp4", b""))
            )

        malformed = self.root / "malformed.mp4"
        malformed.write_bytes(b"not a video")
        with self.assertRaises(VideoSignatureInvalidError):
            VoiceStudioVideoProbe().validate_path(
                malformed,
                extension=".mp4",
                content_type="video/mp4",
            )

    def test_video_size_is_separate_from_audio_limit(self):
        settings.MAX_VIDEO_SIZE = 3
        service = VoiceStudioVideoInputService(temp_dir=self.root)
        with self.assertRaises(VideoTooLargeError):
            __import__("asyncio").run(
                service.validate_upload(
                    make_upload("clip.mp4", "video/mp4", b"1234")
                )
            )

    def test_video_without_audio_is_valid_but_without_video_is_rejected(self):
        video_only = self._make_video(".mp4")
        metadata = VoiceStudioVideoProbe().validate_path(
            video_only,
            extension=".mp4",
            content_type="video/mp4",
        )
        self.assertFalse(metadata.has_audio)

        self._require_ffmpeg()
        audio_only = self.root / "audio-only.mp4"
        subprocess.run(
            [
                self.ffmpeg_binary,
                "-v",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:sample_rate=8000:d=0.5",
                "-c:a",
                "aac",
                str(audio_only),
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
        with self.assertRaises(VideoNoVideoStreamError):
            VoiceStudioVideoProbe().validate_path(
                audio_only,
                extension=".mp4",
                content_type="video/mp4",
            )

    def test_duration_invalid_and_too_long_are_distinct(self):
        path = self._make_video(".mp4")
        probe = VoiceStudioVideoProbe()
        invalid_payload = json.dumps(
            {
                "streams": [{"codec_type": "video", "codec_name": "h264"}],
                "format": {"format_name": "mov,mp4", "duration": "N/A"},
            }
        ).encode()
        with patch.object(probe, "_run_bounded", return_value=invalid_payload):
            with self.assertRaises(VideoDurationInvalidError):
                probe.validate_path(path, extension=".mp4", content_type="video/mp4")

        too_long_payload = json.dumps(
            {
                "streams": [{"codec_type": "video", "codec_name": "h264"}],
                "format": {"format_name": "mov,mp4", "duration": "301"},
            }
        ).encode()
        with patch.object(probe, "_run_bounded", return_value=too_long_payload):
            with self.assertRaises(VideoDurationTooLongError):
                probe.validate_path(path, extension=".mp4", content_type="video/mp4")

    def test_malformed_json_and_missing_ffprobe_do_not_fallback(self):
        path = self._make_video(".mp4")
        probe = VoiceStudioVideoProbe()
        with patch.object(probe, "_run_bounded", return_value=b"not-json"):
            with self.assertRaises(FFProbeFailedError):
                probe.validate_path(path, extension=".mp4", content_type="video/mp4")

        missing_probe = VoiceStudioVideoProbe(ffprobe_binary="missing-ffprobe-for-test")
        with self.assertRaises(FFProbeNotConfiguredError):
            missing_probe.validate_path(
                path,
                extension=".mp4",
                content_type="video/mp4",
            )

    def test_ffprobe_timeout_and_metadata_output_are_bounded(self):
        fake_timeout_process = _FakeProbeProcess(b"{}")
        probe = VoiceStudioVideoProbe(timeout_seconds=1)
        with patch(
            "app.services.voice_studio.video_input.subprocess.Popen",
            return_value=fake_timeout_process,
        ), patch(
            "app.services.voice_studio.video_input.time.monotonic",
            side_effect=[0, 2],
        ):
            with self.assertRaises(FFProbeTimeoutError):
                probe._run_bounded(["ffprobe", "video.mp4"])

        fake_large_output_process = _FakeProbeProcess(b"x" * (PROBE_OUTPUT_MAX_BYTES + 1))
        with patch(
            "app.services.voice_studio.video_input.subprocess.Popen",
            return_value=fake_large_output_process,
        ):
            with self.assertRaises(FFProbeFailedError):
                probe._run_bounded(["ffprobe", "video.mp4"])


if __name__ == "__main__":
    unittest.main()
