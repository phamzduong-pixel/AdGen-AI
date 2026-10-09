import asyncio
import io
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI, UploadFile
from fastapi.testclient import TestClient
from starlette.datastructures import Headers

import app.api.voice_conversion as voice_conversion_api
from app.api.voice_conversion import router as voice_conversion_router
from app.core.config import settings
from tests.audio_fixtures import make_wav_bytes
from app.core.security import get_current_user
from app.models.user import User
from app.services.voice_conversion.models import (
    VoiceConversionError,
    VoiceConversionAudioInvalidError,
    VoiceConversionOptions,
    VoiceConversionOutputInvalidError,
    VoiceConversionProviderNotConfiguredError,
    VoiceConversionProviderTimeoutError,
    VoiceConversionResult,
    VoiceConversionTargetVoiceRequiredError,
    VoiceConversionTooLargeError,
    VoiceConversionUnsupportedFormatError,
    VoiceConversionUnsupportedOutputFormatError,
)
from app.services.voice_conversion.providers.base import BaseVoiceConversionProvider
from app.services.voice_conversion.providers.factory import (
    build_voice_conversion_provider,
)
from app.services.voice_conversion.providers.unavailable import (
    UnavailableVoiceConversionProvider,
)
from app.services.voice_conversion.service import VoiceConversionService


def make_upload(filename: str, content_type: str, content: bytes) -> UploadFile:
    return UploadFile(
        file=io.BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


class RecordingProvider(BaseVoiceConversionProvider):
    def __init__(self):
        self.path: Path | None = None
        self.path_existed_during_call = False
        self.target_voice_id: str | None = None
        self.language: str | None = None
        self.options: VoiceConversionOptions | None = None

    @property
    def provider_id(self) -> str:
        return "unit-test-provider"

    async def convert(
        self,
        source_audio_path: Path,
        *,
        source_content_type: str,
        target_voice_id: str,
        language: str | None,
        options: VoiceConversionOptions,
    ) -> VoiceConversionResult:
        self.path = source_audio_path
        self.path_existed_during_call = source_audio_path.is_file()
        self.target_voice_id = target_voice_id
        self.language = language
        self.options = options
        if options.output_format == "wav":
            return VoiceConversionResult(
                audio_bytes=b"unit-test-wav",
                content_type="audio/wav",
                file_extension=".wav",
                provider_id=self.provider_id,
                metadata={"path": str(source_audio_path), "output_format": "wav"},
            )
        return VoiceConversionResult(
            audio_bytes=b"unit-test-mp3",
            content_type="audio/mpeg",
            file_extension=".mp3",
            provider_id=self.provider_id,
            metadata={"path": str(source_audio_path), "output_format": "mp3"},
        )


class RaisingProvider(BaseVoiceConversionProvider):
    def __init__(self):
        self.path: Path | None = None

    @property
    def provider_id(self) -> str:
        return "unit-test-provider"

    async def convert(self, source_audio_path, **kwargs):
        self.path = source_audio_path
        raise RuntimeError("synthetic provider failure")


class TimeoutProvider(BaseVoiceConversionProvider):
    def __init__(self):
        self.path: Path | None = None

    @property
    def provider_id(self) -> str:
        return "unit-test-provider"

    async def convert(self, source_audio_path, **kwargs):
        self.path = source_audio_path
        await asyncio.sleep(0.05)
        return VoiceConversionResult(b"late", "audio/mpeg", ".mp3", self.provider_id)


class InvalidOutputProvider(BaseVoiceConversionProvider):
    @property
    def provider_id(self) -> str:
        return "unit-test-provider"

    async def convert(self, source_audio_path, **kwargs):
        return VoiceConversionResult(
            audio_bytes=b"not-a-supported-result",
            content_type="application/octet-stream",
            file_extension=".bin",
            provider_id=self.provider_id,
        )


class VoiceConversionServiceTests(unittest.TestCase):
    def setUp(self):
        self.original_max_size = settings.VC_AUDIO_MAX_SIZE_BYTES
        self.original_timeout = settings.VC_PROVIDER_TIMEOUT_SECONDS
        self.original_output_max_size = settings.VC_OUTPUT_MAX_SIZE_BYTES

    def tearDown(self):
        settings.VC_AUDIO_MAX_SIZE_BYTES = self.original_max_size
        settings.VC_PROVIDER_TIMEOUT_SECONDS = self.original_timeout
        settings.VC_OUTPUT_MAX_SIZE_BYTES = self.original_output_max_size

    def test_factory_is_disabled_by_default_and_never_fabricates_audio(self):
        with patch.object(settings, "VC_PROVIDER", "disabled"):
            provider = build_voice_conversion_provider()

        self.assertIsInstance(provider, UnavailableVoiceConversionProvider)
        with self.assertRaises(VoiceConversionProviderNotConfiguredError):
            asyncio.run(
                VoiceConversionService(provider=provider).convert_upload(
                    make_upload("voice.wav", "audio/wav", make_wav_bytes()),
                    target_voice_id="target",
                )
            )

    def test_valid_audio_calls_provider_and_cleans_temp_file(self):
        provider = RecordingProvider()
        result = asyncio.run(
            VoiceConversionService(provider=provider).convert_upload(
                make_upload("voice.wav", "audio/wav", make_wav_bytes()),
                target_voice_id="  target-voice  ",
                language="vi-VN",
                output_format="wav",
                remove_background_noise=True,
            )
        )

        self.assertEqual(result.audio_bytes, b"unit-test-wav")
        self.assertEqual(result.content_type, "audio/wav")
        self.assertTrue(provider.path_existed_during_call)
        self.assertIsNotNone(provider.path)
        self.assertFalse(provider.path.exists())
        self.assertEqual(provider.target_voice_id, "target-voice")
        self.assertEqual(provider.language, "vi-VN")
        self.assertEqual(provider.options.output_format, "wav")
        self.assertTrue(provider.options.remove_background_noise)
        self.assertEqual(result.metadata["filename"], "voice.wav")
        self.assertNotIn("path", result.metadata)

    def test_malformed_audio_is_rejected_before_provider_call(self):
        provider = RecordingProvider()
        with self.assertRaises(VoiceConversionAudioInvalidError):
            asyncio.run(
                VoiceConversionService(provider=provider).convert_upload(
                    make_upload(
                        "voice.wav",
                        "audio/wav",
                        b"RIFF\x00\x00\x00\x00WAVE",
                    ),
                    target_voice_id="target",
                )
            )
        self.assertIsNone(provider.path)
    def test_validation_errors_are_stable(self):
        service = VoiceConversionService(provider=RecordingProvider())
        with self.assertRaises(VoiceConversionTargetVoiceRequiredError):
            asyncio.run(
                service.convert_upload(
                    make_upload("voice.wav", "audio/wav", make_wav_bytes()),
                    target_voice_id=" ",
                )
            )
        with self.assertRaises(VoiceConversionUnsupportedFormatError):
            asyncio.run(
                service.convert_upload(
                    make_upload("voice.exe", "application/octet-stream", b"data"),
                    target_voice_id="target",
                )
            )
        with self.assertRaises(VoiceConversionUnsupportedOutputFormatError):
            asyncio.run(
                service.convert_upload(
                    make_upload("voice.wav", "audio/wav", make_wav_bytes()),
                    target_voice_id="target",
                    output_format="ogg",
                )
            )

    def test_empty_mismatched_and_oversized_audio_are_rejected(self):
        service = VoiceConversionService(provider=RecordingProvider())
        with self.assertRaises(VoiceConversionError) as empty_context:
            asyncio.run(
                service.convert_upload(
                    make_upload("voice.wav", "audio/wav", b""),
                    target_voice_id="target",
                )
            )
        self.assertEqual(empty_context.exception.code, "VC_EMPTY_AUDIO")

        with self.assertRaises(VoiceConversionError) as mismatch_context:
            asyncio.run(
                service.convert_upload(
                    make_upload("voice.wav", "audio/mpeg", make_wav_bytes()),
                    target_voice_id="target",
                )
            )
        self.assertEqual(mismatch_context.exception.code, "VC_AUDIO_MIME_MISMATCH")

        settings.VC_AUDIO_MAX_SIZE_BYTES = 3
        with self.assertRaises(VoiceConversionTooLargeError):
            asyncio.run(
                service.convert_upload(
                    make_upload("voice.wav", "audio/wav", b"1234"),
                    target_voice_id="target",
                )
            )

    def test_provider_failure_and_timeout_clean_temp_files(self):
        failing_provider = RaisingProvider()
        with self.assertRaises(VoiceConversionError) as failure_context:
            asyncio.run(
                VoiceConversionService(provider=failing_provider).convert_upload(
                    make_upload("voice.wav", "audio/wav", make_wav_bytes()),
                    target_voice_id="target",
                )
            )
        self.assertEqual(failure_context.exception.code, "VC_CONVERSION_FAILED")
        self.assertIsNotNone(failing_provider.path)
        self.assertFalse(failing_provider.path.exists())

        settings.VC_PROVIDER_TIMEOUT_SECONDS = 0.001
        timeout_provider = TimeoutProvider()
        with self.assertRaises(VoiceConversionProviderTimeoutError):
            asyncio.run(
                VoiceConversionService(provider=timeout_provider).convert_upload(
                    make_upload("voice.wav", "audio/wav", make_wav_bytes()),
                    target_voice_id="target",
                )
            )
        self.assertIsNotNone(timeout_provider.path)
        self.assertFalse(timeout_provider.path.exists())

    def test_invalid_provider_output_is_rejected(self):
        with self.assertRaises(VoiceConversionOutputInvalidError):
            asyncio.run(
                VoiceConversionService(provider=InvalidOutputProvider()).convert_upload(
                    make_upload("voice.wav", "audio/wav", make_wav_bytes()),
                    target_voice_id="target",
                )
            )


class VoiceConversionApiTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(voice_conversion_router)
        self.user = User(
            username="vc-owner",
            email="vc-owner@example.com",
            hashed_password="unused",
            email_verified=True,
        )
        self.app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close()

    def test_disabled_provider_returns_explicit_503_without_audio(self):
        with patch.object(
            voice_conversion_api.voice_conversion_service,
            "provider",
            UnavailableVoiceConversionProvider("disabled for contract test"),
        ):
            response = self.client.post(
                "/voice-conversion/convert",
                files={"file": ("voice.wav", io.BytesIO(make_wav_bytes()), "audio/wav")},
                data={"target_voice_id": "target"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"]["code"], "VC_PROVIDER_NOT_CONFIGURED"
        )
        self.assertTrue(response.headers["content-type"].startswith("application/json"))

    def test_endpoint_requires_authentication(self):
        self.app.dependency_overrides.clear()
        response = self.client.post(
            "/voice-conversion/convert",
            files={"file": ("voice.wav", io.BytesIO(make_wav_bytes()), "audio/wav")},
            data={"target_voice_id": "target"},
        )
        self.assertEqual(response.status_code, 401)

    def test_missing_target_voice_returns_stable_422(self):
        response = self.client.post(
            "/voice-conversion/convert",
            files={"file": ("voice.wav", io.BytesIO(make_wav_bytes()), "audio/wav")},
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"]["code"], "VC_TARGET_VOICE_REQUIRED")

    def test_contract_success_returns_audio_with_provider_headers(self):
        provider = RecordingProvider()
        with patch.object(
            voice_conversion_api,
            "voice_conversion_service",
            VoiceConversionService(provider=provider),
        ):
            response = self.client.post(
                "/voice-conversion/convert",
                files={"file": ("voice.wav", io.BytesIO(make_wav_bytes()), "audio/wav")},
                data={
                    "target_voice_id": "target",
                    "language": "vi-VN",
                    "output_format": "wav",
                    "remove_background_noise": "true",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"unit-test-wav")
        self.assertEqual(response.headers["content-type"], "audio/wav")
        self.assertEqual(response.headers["x-vc-provider"], "unit-test-provider")
        self.assertIn("voice-converted.wav", response.headers["content-disposition"])


if __name__ == "__main__":
    unittest.main()
