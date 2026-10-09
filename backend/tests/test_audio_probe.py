import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.core.config import settings
from app.services.voice_conversion.audio_probe import (
    AudioProbeResult,
    PROBE_OUTPUT_MAX_BYTES,
    VoiceConversionAudioProbe,
    _signature_matches,
)
from app.services.voice_conversion.models import (
    VoiceConversionAudioInvalidError,
    VoiceConversionAudioProbeOutputTooLargeError,
    VoiceConversionAudioProbeTimeoutError,
    VoiceConversionAudioTooLongError,
    VoiceConversionProbeMetadataError,
    VoiceConversionProbeNotConfiguredError,
    VoiceConversionUnsupportedContainerError,
)
from tests.audio_fixtures import make_wav_bytes


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


class AudioProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.audio_path = Path(self.temp_dir.name) / "fixture.wav"
        self.audio_path.write_bytes(make_wav_bytes())
        self.original_max_duration = settings.VC_AUDIO_MAX_DURATION_SECONDS

    def tearDown(self):
        settings.VC_AUDIO_MAX_DURATION_SECONDS = self.original_max_duration
        self.temp_dir.cleanup()

    def test_real_ffprobe_validates_reproducible_wav_fixture(self):
        result = VoiceConversionAudioProbe().validate(
            self.audio_path,
            extension=".wav",
            content_type="audio/wav",
        )

        self.assertEqual(result.container_format, "wav")
        self.assertEqual(result.codec_name, "pcm_s16le")
        self.assertGreater(result.duration_seconds, 0)
        self.assertEqual(result.sample_rate, 8000)
        self.assertEqual(result.channels, 1)

    def test_real_ffprobe_reports_opus_for_ogg_and_webm_fixtures(self):
        ffmpeg_binary = shutil.which(settings.FFMPEG_BINARY)
        if not ffmpeg_binary:
            self.skipTest("FFmpeg is not available")

        for extension, content_type in (
            (".ogg", "audio/ogg"),
            (".webm", "audio/webm"),
        ):
            with self.subTest(extension=extension):
                output_path = Path(self.temp_dir.name) / f"fixture{extension}"
                subprocess.run(
                    [
                        ffmpeg_binary,
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-y",
                        "-i",
                        str(self.audio_path),
                        "-c:a",
                        "libopus",
                        "-b:a",
                        "16k",
                        str(output_path),
                    ],
                    check=True,
                )
                result = VoiceConversionAudioProbe().validate(
                    output_path,
                    extension=extension,
                    content_type=content_type,
                )
                self.assertEqual(result.codec_name, "opus")

    def test_minimum_signatures_are_checked_per_allowlisted_extension(self):
        signatures = {
            ".wav": b"RIFF\x00\x00\x00\x00WAVE",
            ".flac": b"fLaC",
            ".mp3": b"ID3\x04\x00\x00",
            ".m4a": b"\x00\x00\x00\x18ftypM4A ",
            ".ogg": b"OggS\x00\x02",
            ".oga": b"OggS\x00\x02",
            ".webm": b"\x1a\x45\xdf\xa3",
        }
        for extension, header in signatures.items():
            with self.subTest(extension=extension):
                self.assertTrue(_signature_matches(extension, header))

    def test_signature_spoof_is_rejected_before_ffprobe(self):
        spoofed_path = Path(self.temp_dir.name) / "spoofed.mp3"
        spoofed_path.write_bytes(make_wav_bytes())
        probe = VoiceConversionAudioProbe()

        with patch.object(probe, "_probe") as probe_mock:
            with self.assertRaises(VoiceConversionAudioInvalidError):
                probe.validate(
                    spoofed_path,
                    extension=".mp3",
                    content_type="audio/mpeg",
                )

        probe_mock.assert_not_called()

    def test_malformed_audio_with_matching_header_is_rejected(self):
        malformed_path = Path(self.temp_dir.name) / "malformed.wav"
        malformed_path.write_bytes(b"RIFF\x00\x00\x00\x00WAVE")

        with self.assertRaises(VoiceConversionAudioInvalidError):
            VoiceConversionAudioProbe().validate(
                malformed_path,
                extension=".wav",
                content_type="audio/wav",
            )

    def test_duration_limit_is_enforced_after_probe(self):
        probe = VoiceConversionAudioProbe()
        with patch.object(
            probe,
            "_probe",
            return_value=AudioProbeResult("wav", "pcm_s16le", 301.0),
        ):
            with self.assertRaises(VoiceConversionAudioTooLongError):
                probe.validate(
                    self.audio_path,
                    extension=".wav",
                    content_type="audio/wav",
                )

    def test_missing_audio_stream_is_distinguished_from_invalid_json(self):
        probe = VoiceConversionAudioProbe()
        no_audio = json.dumps(
            {"streams": [], "format": {"format_name": "wav", "duration": "0.1"}}
        ).encode()
        with patch.object(probe, "_run_bounded", return_value=no_audio):
            with self.assertRaises(VoiceConversionUnsupportedContainerError):
                probe._probe(self.audio_path)

        with patch.object(probe, "_run_bounded", return_value=b"not-json"):
            with self.assertRaises(VoiceConversionProbeMetadataError):
                probe._probe(self.audio_path)

    def test_format_duration_is_used_when_stream_duration_is_unavailable(self):
        probe = VoiceConversionAudioProbe()
        payload = json.dumps(
            {
                "streams": [
                    {
                        "codec_type": "audio",
                        "codec_name": "pcm_s16le",
                        "duration": "N/A",
                    }
                ],
                "format": {"format_name": "wav", "duration": "0.1"},
            }
        ).encode()
        with patch.object(probe, "_run_bounded", return_value=payload):
            result = probe._probe(self.audio_path)

        self.assertAlmostEqual(result.duration_seconds, 0.1)
    def test_missing_ffprobe_is_not_fallback_to_mock(self):
        probe = VoiceConversionAudioProbe(ffprobe_binary="missing-ffprobe-for-test")
        with self.assertRaises(VoiceConversionProbeNotConfiguredError):
            probe.validate(
                self.audio_path,
                extension=".wav",
                content_type="audio/wav",
            )

    def test_probe_timeout_is_bounded(self):
        fake_process = _FakeProbeProcess(b"{}")
        probe = VoiceConversionAudioProbe(timeout_seconds=1)
        with patch(
            "app.services.voice_conversion.audio_probe.subprocess.Popen",
            return_value=fake_process,
        ), patch(
            "app.services.voice_conversion.audio_probe.time.monotonic",
            side_effect=[0, 2],
        ):
            with self.assertRaises(VoiceConversionAudioProbeTimeoutError):
                probe._run_bounded(["ffprobe", "fixture.wav"])

    def test_probe_output_limit_is_bounded(self):
        fake_process = _FakeProbeProcess(b"x" * (PROBE_OUTPUT_MAX_BYTES + 1))
        probe = VoiceConversionAudioProbe(timeout_seconds=1)
        with patch(
            "app.services.voice_conversion.audio_probe.subprocess.Popen",
            return_value=fake_process,
        ):
            with self.assertRaises(VoiceConversionAudioProbeOutputTooLargeError):
                probe._run_bounded(["ffprobe", "fixture.wav"])


if __name__ == "__main__":
    unittest.main()
