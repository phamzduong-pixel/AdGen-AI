"""Google Cloud Speech-to-Text V2 adapter.

The SDK is imported lazily so the application remains fail-closed when the
optional provider dependency or credentials are unavailable. Provider calls
are synchronous in the Google SDK and are run in a worker thread by this
async adapter.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Callable

from app.core.config import settings
from app.services.stt.models import (
    STTAudioTooLargeError,
    STTEmptyAudioError,
    STTEmptyTranscriptError,
    STTError,
    STTProviderAuthenticationError,
    STTProviderInvalidResponseError,
    STTProviderNotConfiguredError,
    STTProviderQuotaExceededError,
    STTProviderRateLimitedError,
    STTProviderTimeoutError,
    TranscriptionResult,
)
from app.services.stt.providers.base import BaseSTTProvider


GoogleClientFactory = Callable[[], Any]


GOOGLE_SUPPORTED_AUDIO_CODECS = {
    ".flac": frozenset({"flac"}),
    ".m4a": frozenset({"aac"}),
    ".mp3": frozenset({"mp3"}),
    ".ogg": frozenset({"opus"}),
    ".wav": frozenset({"pcm_s16le", "pcm_mulaw", "pcm_alaw"}),
    ".webm": frozenset({"opus"}),
}


def _load_speech_sdk() -> tuple[Any, Any]:
    try:
        from google.cloud import speech_v2
        from google.cloud.speech_v2.types import cloud_speech
    except (ImportError, ModuleNotFoundError) as error:
        raise STTProviderNotConfiguredError(
            "Google Cloud Speech SDK is not installed"
        ) from error
    return speech_v2, cloud_speech


def _error_name(error: BaseException) -> str:
    return error.__class__.__name__.lower()


class GoogleCloudSTTProvider(BaseSTTProvider):
    """Transcribe bounded local audio through Cloud Speech-to-Text V2."""

    provider_id = "google-cloud"
    supported_audio_codecs = GOOGLE_SUPPORTED_AUDIO_CODECS
    model = "chirp_3"
    location = "us"

    def __init__(
        self,
        *,
        project_id: str | None = None,
        timeout_seconds: float | None = None,
        client: Any | None = None,
        client_factory: GoogleClientFactory | None = None,
    ):
        self.project_id = (project_id or settings.GOOGLE_CLOUD_PROJECT).strip()
        if not self.project_id:
            raise STTProviderNotConfiguredError(
                "GOOGLE_CLOUD_PROJECT is not configured"
            )

        self.timeout_seconds = (
            settings.STT_PROVIDER_TIMEOUT_SECONDS
            if timeout_seconds is None
            else timeout_seconds
        )
        if self.timeout_seconds <= 0:
            raise STTProviderNotConfiguredError(
                "STT_PROVIDER_TIMEOUT_SECONDS must be greater than zero"
            )

        if client is not None:
            self.client = client
        elif client_factory is not None:
            try:
                self.client = client_factory()
            except Exception as error:
                raise STTProviderNotConfiguredError(
                    "Google Cloud Speech client could not be initialized"
                ) from error
        else:
            self.client = self._create_client()

    @staticmethod
    def _create_client() -> Any:
        speech_v2, _ = _load_speech_sdk()
        try:
            return speech_v2.SpeechClient()
        except Exception as error:
            if _error_name(error) in {
                "defaultcredentialserror",
                "refresherror",
                "googleautherror",
                "unauthenticated",
                "permissiondenied",
                "forbidden",
            }:
                raise STTProviderNotConfiguredError(
                    "Google Cloud Speech credentials are unavailable"
                ) from error
            raise STTProviderNotConfiguredError(
                "Google Cloud Speech client could not be initialized"
            ) from error

    @property
    def recognizer(self) -> str:
        return (
            f"projects/{self.project_id}/locations/{self.location}/recognizers/_"
        )

    @staticmethod
    def _read_audio(audio_path: Path) -> bytes:
        try:
            with audio_path.open("rb") as audio_file:
                content = audio_file.read(settings.STT_AUDIO_MAX_SIZE + 1)
        except OSError as error:
            raise STTError from error

        if not content:
            raise STTEmptyAudioError
        if len(content) > settings.STT_AUDIO_MAX_SIZE:
            raise STTAudioTooLargeError
        return content

    def _build_request(
        self,
        cloud_speech: Any,
        *,
        content: bytes,
        language: str,
    ) -> Any:
        config = cloud_speech.RecognitionConfig(
            auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
            language_codes=[language],
            model=self.model,
        )
        return cloud_speech.RecognizeRequest(
            recognizer=self.recognizer,
            config=config,
            content=content,
        )

    @staticmethod
    def _extract_transcript(response: Any) -> str:
        results = getattr(response, "results", None)
        if results is None or isinstance(results, (str, bytes)):
            raise STTProviderInvalidResponseError

        try:
            result_items = list(results)
        except TypeError as error:
            raise STTProviderInvalidResponseError from error

        if not result_items:
            raise STTEmptyTranscriptError

        transcripts: list[str] = []
        for result in result_items:
            alternatives = getattr(result, "alternatives", None)
            if alternatives is None or isinstance(alternatives, (str, bytes)):
                raise STTProviderInvalidResponseError
            try:
                first_alternative = next(iter(alternatives))
            except (StopIteration, TypeError) as error:
                raise STTProviderInvalidResponseError from error
            transcript = getattr(first_alternative, "transcript", None)
            if not isinstance(transcript, str):
                raise STTProviderInvalidResponseError
            if transcript.strip():
                transcripts.append(transcript.strip())

        if not transcripts:
            raise STTEmptyTranscriptError
        return " ".join(transcripts)

    @staticmethod
    def _raise_mapped_error(error: BaseException) -> None:
        if isinstance(error, STTError):
            raise error

        name = _error_name(error)
        if name in {"timeouterror", "asyncio timeouterror", "deadlineexceeded"}:
            raise STTProviderTimeoutError from error
        if name in {
            "defaultcredentialserror",
            "refresherror",
            "googleautherror",
            "unauthenticated",
            "permissiondenied",
            "forbidden",
        }:
            raise STTProviderAuthenticationError from error
        if name in {"toomanyrequests", "ratelimited", "ratelimitexceeded"}:
            raise STTProviderRateLimitedError from error
        if name in {"resourceexhausted", "quotaexceeded"}:
            raise STTProviderQuotaExceededError from error
        if name in {"invalidargument", "failedprecondition", "notfound"}:
            raise STTProviderInvalidResponseError from error
        raise STTError from error

    async def transcribe(
        self,
        audio_path: Path,
        *,
        content_type: str,
        language: str | None,
    ) -> TranscriptionResult:
        del content_type
        effective_language = language or settings.STT_DEFAULT_LANGUAGE or "vi-VN"
        content = self._read_audio(audio_path)

        try:
            _, cloud_speech = _load_speech_sdk()
            request = self._build_request(
                cloud_speech,
                content=content,
                language=effective_language,
            )
            response = await asyncio.to_thread(
                self.client.recognize,
                request=request,
                timeout=self.timeout_seconds,
            )
            transcript = self._extract_transcript(response)
        except Exception as error:
            self._raise_mapped_error(error)

        return TranscriptionResult(
            transcript=transcript,
            language=effective_language,
            provider=self.provider_id,
            metadata={"model": self.model, "location": self.location},
        )
