import asyncio
import io
import unittest
from pathlib import Path

from fastapi import UploadFile
from starlette.datastructures import Headers

from app.core.config import settings
from app.services.voice_conversion.audio_probe import AudioProbeResult
from app.services.stt.models import (
    STTAudioTooLargeError,
    STTAudioTooLongError,
    STTEmptyAudioError,
    STTError,
    STTProviderNotConfiguredError,
    STTProviderTimeoutError,
    STTInvalidLanguageError,
    STTUnsupportedFormatError,
    STTUnsupportedMimeTypeError,
    STTUnsupportedCodecError,
    TranscriptionResult,
)
from app.services.stt.providers.base import BaseSTTProvider
from app.services.stt.providers.google_cloud import GoogleCloudSTTProvider
from app.services.stt.providers.unavailable import UnavailableSTTProvider
from app.services.stt.service import STTService
from tests.audio_fixtures import make_wav_bytes



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


class StubAudioProbe:
    def validate(self, source_path, *, extension, content_type, max_duration_seconds):
        return AudioProbeResult(
            container_format="wav",
            codec_name="pcm_s16le",
            duration_seconds=0.1,
        )

class RecordingProvider(BaseSTTProvider):
    def __init__(self):
        self.path: Path | None = None
        self.path_existed_during_call = False
        self.content_type = None
        self.language = None

    @property
    def provider_id(self) -> str:
        return "unit-test-provider"

    async def transcribe(
        self,
        audio_path: Path,
        *,
        content_type: str,
        language: str | None,
    ) -> TranscriptionResult:
        self.path = audio_path
        self.path_existed_during_call = audio_path.is_file()
        self.content_type = content_type
        self.language = language
        return TranscriptionResult(
            transcript="Xin chao",
            language=language,
            provider=self.provider_id,
            metadata={"unit_test": True},
        )


class RaisingProvider(BaseSTTProvider):
    def __init__(self):
        self.path: Path | None = None

    @property
    def provider_id(self) -> str:
        return "unit-test-provider"

    async def transcribe(self, audio_path, *, content_type, language):
        self.path = audio_path
        raise RuntimeError("synthetic provider failure")


class TimeoutProvider(BaseSTTProvider):
    def __init__(self):
        self.path: Path | None = None

    @property
    def provider_id(self) -> str:
        return "unit-test-provider"

    async def transcribe(self, audio_path, *, content_type, language):
        self.path = audio_path
        await asyncio.sleep(0.05)
        return TranscriptionResult("late", language, self.provider_id)


class STTServiceTests(unittest.TestCase):
    def setUp(self):
        self.original_max_size = settings.STT_AUDIO_MAX_SIZE
        self.original_timeout = settings.STT_PROVIDER_TIMEOUT_SECONDS

    def tearDown(self):
        settings.STT_AUDIO_MAX_SIZE = self.original_max_size
        settings.STT_PROVIDER_TIMEOUT_SECONDS = self.original_timeout

    def test_valid_audio_uses_provider_and_cleans_temp_file(self):
        provider = RecordingProvider()
        service = STTService(provider=provider, audio_probe=StubAudioProbe())

        result = asyncio.run(
            service.transcribe_upload(
                make_upload("voice.wav", "audio/wav", b"RIFF-unit-test"),
                language="vi-VN",
            )
        )

        self.assertEqual(result.transcript, "Xin chao")
        self.assertEqual(result.language, "vi-VN")
        self.assertEqual(result.provider, "unit-test-provider")
        self.assertTrue(provider.path_existed_during_call)
        self.assertIsNotNone(provider.path)
        self.assertFalse(provider.path.exists())
        self.assertEqual(result.metadata["filename"], "voice.wav")
        self.assertNotIn("path", result.metadata)

    def test_supported_formats_accept_matching_mime_types(self):
        for filename, content_type in (
            ("voice.flac", "audio/flac"),
            ("voice.m4a", "audio/mp4"),
            ("voice.mp3", "audio/mpeg"),
            ("voice.ogg", "audio/ogg"),
            ("voice.wav", "audio/wav"),
            ("voice.webm", "audio/webm"),
        ):
            with self.subTest(filename=filename):
                result = asyncio.run(
                    STTService(provider=RecordingProvider(), audio_probe=StubAudioProbe()).transcribe_upload(
                        make_upload(filename, content_type, b"audio"),
                    )
                )
                self.assertEqual(result.provider, "unit-test-provider")

    def test_unsupported_format_is_rejected(self):
        with self.assertRaises(STTUnsupportedFormatError):
            asyncio.run(
                STTService(provider=RecordingProvider(), audio_probe=StubAudioProbe()).transcribe_upload(
                    make_upload("voice.exe", "application/octet-stream", b"data"),
                )
            )

    def test_mismatched_mime_type_is_rejected(self):
        with self.assertRaises(STTUnsupportedMimeTypeError):
            asyncio.run(
                STTService(provider=RecordingProvider(), audio_probe=StubAudioProbe()).transcribe_upload(
                    make_upload("voice.wav", "audio/mpeg", b"data"),
                )
            )

    def test_google_provider_rejects_ogg_and_webm_non_opus_before_provider_call(self):
        class CodecProbe:
            def __init__(self, codec_name):
                self.codec_name = codec_name

            def validate(self, source_path, *, extension, content_type, max_duration_seconds):
                return AudioProbeResult(
                    container_format=extension.lstrip("."),
                    codec_name=self.codec_name,
                    duration_seconds=0.1,
                )

        provider = GoogleCloudSTTProvider(project_id="test-project", client=object())
        for filename, content_type in (
            ("voice.ogg", "audio/ogg"),
            ("voice.webm", "audio/webm"),
        ):
            with self.subTest(filename=filename):
                with self.assertRaises(STTUnsupportedCodecError) as context:
                    asyncio.run(
                        STTService(
                            provider=provider,
                            audio_probe=CodecProbe("vorbis"),
                        ).transcribe_upload(
                            make_upload(filename, content_type, b"audio"),
                        )
                    )
                self.assertEqual(context.exception.code, "STT_UNSUPPORTED_AUDIO_CODEC")

    def test_empty_audio_is_rejected(self):
        with self.assertRaises(STTEmptyAudioError):
            asyncio.run(
                STTService(provider=RecordingProvider(), audio_probe=StubAudioProbe()).transcribe_upload(
                    make_upload("voice.wav", "audio/wav", b""),
                )
            )

    def test_invalid_language_is_rejected(self):
        with self.assertRaises(STTInvalidLanguageError):
            asyncio.run(
                STTService(provider=RecordingProvider(), audio_probe=StubAudioProbe()).transcribe_upload(
                    make_upload("voice.wav", "audio/wav", b"audio"),
                    language="vi VN",
                )
            )

    def test_oversized_audio_is_rejected(self):
        settings.STT_AUDIO_MAX_SIZE = 3
        with self.assertRaises(STTAudioTooLargeError):
            asyncio.run(
                STTService(provider=RecordingProvider(), audio_probe=StubAudioProbe()).transcribe_upload(
                    make_upload("voice.wav", "audio/wav", b"1234"),
                )
            )

    def test_unavailable_provider_never_fabricates_transcript(self):
        with self.assertRaises(STTProviderNotConfiguredError):
            asyncio.run(
                STTService(provider=UnavailableSTTProvider(), audio_probe=StubAudioProbe()).transcribe_upload(
                    make_upload("voice.wav", "audio/wav", b"audio"),
                )
            )

    def test_provider_error_cleans_temp_file_and_is_safe(self):
        provider = RaisingProvider()
        service = STTService(provider=provider, audio_probe=StubAudioProbe())
        with self.assertRaises(STTError) as context:
            asyncio.run(
                service.transcribe_upload(
                    make_upload("voice.wav", "audio/wav", b"audio"),
                )
            )
        self.assertEqual(context.exception.code, "STT_PROVIDER_ERROR")
        self.assertIsNotNone(provider.path)
        self.assertFalse(provider.path.exists())

    def test_real_probe_rejects_malformed_audio_before_provider(self):
        provider = RecordingProvider()
        with self.assertRaises(STTError) as context:
            asyncio.run(
                STTService(provider=provider).transcribe_upload(
                    make_upload("voice.wav", "audio/wav", b"not-a-wav"),
                )
            )
        self.assertEqual(context.exception.code, "STT_INVALID_AUDIO")
        self.assertIsNone(provider.path)

    def test_real_probe_accepts_audio_at_60_seconds(self):
        provider = RecordingProvider()
        settings.STT_AUDIO_MAX_DURATION_SECONDS = 60
        result = asyncio.run(
            STTService(provider=provider).transcribe_upload(
                make_upload(
                    "voice.wav",
                    "audio/wav",
                    make_wav_bytes(duration_seconds=60.0),
                ),
            )
        )
        self.assertEqual(result.provider, "unit-test-provider")
        self.assertTrue(provider.path_existed_during_call)
    def test_real_probe_rejects_audio_over_60_seconds_before_provider(self):
        provider = RecordingProvider()
        settings.STT_AUDIO_MAX_DURATION_SECONDS = 60
        with self.assertRaises(STTAudioTooLongError):
            asyncio.run(
                STTService(provider=provider).transcribe_upload(
                    make_upload(
                        "voice.wav",
                        "audio/wav",
                        make_wav_bytes(duration_seconds=60.1),
                    ),
                )
            )
        self.assertIsNone(provider.path)
    def test_provider_timeout_is_mapped_and_cleans_temp_file(self):
        settings.STT_PROVIDER_TIMEOUT_SECONDS = 0.001
        provider = TimeoutProvider()
        with self.assertRaises(STTProviderTimeoutError):
            asyncio.run(
                STTService(provider=provider, audio_probe=StubAudioProbe()).transcribe_upload(
                    make_upload("voice.wav", "audio/wav", b"audio"),
                )
            )
        self.assertIsNotNone(provider.path)
        self.assertFalse(provider.path.exists())


if __name__ == "__main__":
    unittest.main()
