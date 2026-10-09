import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.core.config import settings
from app.services.stt.models import (
    STTEmptyTranscriptError,
    STTProviderAuthenticationError,
    STTProviderInvalidResponseError,
    STTProviderNotConfiguredError,
    STTProviderQuotaExceededError,
    STTProviderRateLimitedError,
    STTProviderTimeoutError,
)
from app.services.stt.providers.factory import build_stt_provider
from app.services.stt.providers.google_cloud import GoogleCloudSTTProvider


class FakeAutoDetectDecodingConfig:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeRecognitionConfig:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeRecognizeRequest:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeCloudSpeech:
    AutoDetectDecodingConfig = FakeAutoDetectDecodingConfig
    RecognitionConfig = FakeRecognitionConfig
    RecognizeRequest = FakeRecognizeRequest


class FakeClient:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.request = None
        self.timeout = None

    def recognize(self, *, request, timeout):
        self.request = request
        self.timeout = timeout
        if self.error is not None:
            raise self.error
        return self.response


def response_with_transcript(text: str):
    return SimpleNamespace(
        results=[
            SimpleNamespace(
                alternatives=[SimpleNamespace(transcript=text)],
            )
        ]
    )


class GoogleCloudSTTProviderTests(unittest.TestCase):
    def setUp(self):
        self.original_max_size = settings.STT_AUDIO_MAX_SIZE
        self.original_timeout = settings.STT_PROVIDER_TIMEOUT_SECONDS
        self.original_provider = settings.STT_PROVIDER
        self.original_credentials = settings.GOOGLE_APPLICATION_CREDENTIALS
        self.original_project = settings.GOOGLE_CLOUD_PROJECT
        settings.STT_AUDIO_MAX_SIZE = 1024
        settings.STT_PROVIDER_TIMEOUT_SECONDS = 7
        settings.GOOGLE_CLOUD_PROJECT = "test-project"

    def tearDown(self):
        settings.STT_AUDIO_MAX_SIZE = self.original_max_size
        settings.STT_PROVIDER_TIMEOUT_SECONDS = self.original_timeout
        settings.STT_PROVIDER = self.original_provider
        settings.GOOGLE_APPLICATION_CREDENTIALS = self.original_credentials
        settings.GOOGLE_CLOUD_PROJECT = self.original_project

    def _audio_path(self, temporary_directory: str) -> Path:
        path = Path(temporary_directory) / "voice.wav"
        path.write_bytes(b"bounded-audio")
        return path

    def test_success_propagates_vi_vn_and_builds_v2_request(self):
        client = FakeClient(response=response_with_transcript("Xin chao"))
        provider = GoogleCloudSTTProvider(client=client)

        with patch(
            "app.services.stt.providers.google_cloud._load_speech_sdk",
            return_value=(object(), FakeCloudSpeech),
        ):
            with tempfile.TemporaryDirectory() as temporary_directory:
                result = asyncio.run(
                    provider.transcribe(
                        self._audio_path(temporary_directory),
                        content_type="audio/wav",
                        language="vi-VN",
                    )
                )

        self.assertEqual(result.transcript, "Xin chao")
        self.assertEqual(result.language, "vi-VN")
        self.assertEqual(result.provider, "google-cloud")
        self.assertEqual(client.request.config.language_codes, ["vi-VN"])
        self.assertEqual(client.request.config.model, "chirp_3")
        self.assertEqual(
            client.request.recognizer,
            "projects/test-project/locations/us/recognizers/_",
        )
        self.assertEqual(client.timeout, 7)

    def test_caller_selected_language_is_not_silently_changed(self):
        client = FakeClient(response=response_with_transcript("Hello"))
        provider = GoogleCloudSTTProvider(client=client)

        with patch(
            "app.services.stt.providers.google_cloud._load_speech_sdk",
            return_value=(object(), FakeCloudSpeech),
        ):
            with tempfile.TemporaryDirectory() as temporary_directory:
                result = asyncio.run(
                    provider.transcribe(
                        self._audio_path(temporary_directory),
                        content_type="audio/wav",
                        language="en-US",
                    )
                )

        self.assertEqual(result.language, "en-US")
        self.assertEqual(client.request.config.language_codes, ["en-US"])

    def test_empty_transcript_is_rejected(self):
        client = FakeClient(response=SimpleNamespace(results=[]))
        provider = GoogleCloudSTTProvider(client=client)

        with patch(
            "app.services.stt.providers.google_cloud._load_speech_sdk",
            return_value=(object(), FakeCloudSpeech),
        ):
            with tempfile.TemporaryDirectory() as temporary_directory:
                with self.assertRaises(STTEmptyTranscriptError):
                    asyncio.run(
                        provider.transcribe(
                            self._audio_path(temporary_directory),
                            content_type="audio/wav",
                            language="vi-VN",
                        )
                    )

    def test_malformed_response_is_rejected(self):
        responses = (
            SimpleNamespace(results=None),
            SimpleNamespace(results=[SimpleNamespace(alternatives=[])]),
            SimpleNamespace(
                results=[
                    SimpleNamespace(
                        alternatives=[SimpleNamespace(transcript=None)]
                    )
                ]
            ),
        )
        for response in responses:
            with self.subTest(response=response):
                client = FakeClient(response=response)
                provider = GoogleCloudSTTProvider(client=client)
                with patch(
                    "app.services.stt.providers.google_cloud._load_speech_sdk",
                    return_value=(object(), FakeCloudSpeech),
                ):
                    with tempfile.TemporaryDirectory() as temporary_directory:
                        with self.assertRaises(STTProviderInvalidResponseError):
                            asyncio.run(
                                provider.transcribe(
                                    self._audio_path(temporary_directory),
                                    content_type="audio/wav",
                                    language="vi-VN",
                                )
                            )

    def test_provider_errors_map_without_leaking_details(self):
        error_cases = (
            (type("Unauthenticated", (RuntimeError,), {}), STTProviderAuthenticationError),
            (type("PermissionDenied", (RuntimeError,), {}), STTProviderAuthenticationError),
            (type("TooManyRequests", (RuntimeError,), {}), STTProviderRateLimitedError),
            (type("ResourceExhausted", (RuntimeError,), {}), STTProviderQuotaExceededError),
            (type("DeadlineExceeded", (RuntimeError,), {}), STTProviderTimeoutError),
        )
        for error_type, expected in error_cases:
            with self.subTest(error_type=error_type.__name__):
                client = FakeClient(error=error_type("secret path must not surface"))
                provider = GoogleCloudSTTProvider(client=client)
                with patch(
                    "app.services.stt.providers.google_cloud._load_speech_sdk",
                    return_value=(object(), FakeCloudSpeech),
                ):
                    with tempfile.TemporaryDirectory() as temporary_directory:
                        with self.assertRaises(expected) as context:
                            asyncio.run(
                                provider.transcribe(
                                    self._audio_path(temporary_directory),
                                    content_type="audio/wav",
                                    language="vi-VN",
                                )
                            )
                self.assertNotIn("secret", str(context.exception))

    def test_missing_sdk_fails_closed(self):
        with patch(
            "app.services.stt.providers.google_cloud._load_speech_sdk",
            side_effect=STTProviderNotConfiguredError("sdk unavailable"),
        ):
            with self.assertRaises(STTProviderNotConfiguredError):
                GoogleCloudSTTProvider()

    def test_factory_keeps_unavailable_provider_when_sdk_is_missing(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            credentials = Path(temporary_directory) / "credentials.json"
            credentials.write_text("not-read-by-test", encoding="utf-8")
            settings.STT_PROVIDER = "google-cloud"
            settings.GOOGLE_APPLICATION_CREDENTIALS = str(credentials)
            with patch(
                "app.services.stt.providers.factory._google_speech_sdk_available",
                return_value=False,
            ):
                provider = build_stt_provider()

        self.assertEqual(provider.provider_id, "unavailable")

    def test_factory_allows_application_default_credentials_without_path(self):
        settings.STT_PROVIDER = "google-cloud"
        settings.GOOGLE_APPLICATION_CREDENTIALS = ""
        sentinel = object()
        with patch(
            "app.services.stt.providers.factory._google_speech_sdk_available",
            return_value=True,
        ), patch(
            "app.services.stt.providers.factory.GoogleCloudSTTProvider",
            return_value=sentinel,
        ):
            provider = build_stt_provider()

        self.assertIs(provider, sentinel)
    def test_factory_keeps_unavailable_provider_when_provider_initialization_fails(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            credentials = Path(temporary_directory) / "credentials.json"
            credentials.write_text("not-read-by-test", encoding="utf-8")
            settings.STT_PROVIDER = "google-cloud"
            settings.GOOGLE_APPLICATION_CREDENTIALS = str(credentials)
            with patch(
                "app.services.stt.providers.factory._google_speech_sdk_available",
                return_value=True,
            ), patch(
                "app.services.stt.providers.factory.GoogleCloudSTTProvider",
                side_effect=STTProviderNotConfiguredError("not configured"),
            ):
                provider = build_stt_provider()

        self.assertEqual(provider.provider_id, "unavailable")


if __name__ == "__main__":
    unittest.main()
