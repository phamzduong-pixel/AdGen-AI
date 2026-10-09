"""Video audio extraction followed by the existing STT service.

This module owns only the bridge between Voice Studio video validation and the
existing audio STT contract. It does not persist media, call a provider
directly, or fall back to synthetic transcripts.
"""

from __future__ import annotations

import asyncio
import subprocess
import tempfile
import threading
from pathlib import Path

from fastapi import UploadFile
from starlette.datastructures import Headers

from app.core.config import settings
from app.services.stt.models import (
    STTAudioTooLargeError,
    STTAudioTooLongError,
    TranscriptionResult,
)
from app.services.stt.service import STTService, stt_service
from app.services.voice_conversion.audio_probe import probe_audio_file
from app.services.voice_conversion.models import (
    VoiceConversionAudioProbeTimeoutError,
    VoiceConversionAudioTooLongError,
    VoiceConversionError,
    VoiceConversionProbeNotConfiguredError,
)
from app.services.voice_studio.video_input import (
    FFProbeNotConfiguredError,
    FFProbeTimeoutError,
    ValidatedVideoUpload,
    VideoNoAudioStreamError,
    VoiceStudioVideoInputService,
)


EXTRACTED_AUDIO_EXTENSION = ".flac"
EXTRACTED_AUDIO_CONTENT_TYPE = "audio/flac"
EXTRACTED_AUDIO_FILENAME = "video-audio.flac"
EXTRACTION_CONCURRENCY_LIMIT = 2
EXTRACTION_CHUNK_SAFE_SAMPLE_RATE = 16_000
EXTRACTION_CHANNELS = 1
_EXTRACTION_SLOTS = threading.BoundedSemaphore(EXTRACTION_CONCURRENCY_LIMIT)


class VideoToSTTError(RuntimeError):
    """Base error with a safe public code for video-to-STT failures."""

    code = "VIDEO_AUDIO_EXTRACTION_FAILED"
    http_status = 502
    public_message = "Video audio extraction failed."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.public_message)
        self.internal_message = message or self.public_message


class FFmpegNotConfiguredError(VideoToSTTError):
    code = "FFMPEG_NOT_CONFIGURED"
    http_status = 503
    public_message = "Video audio extraction tool is not configured."


class VideoAudioExtractionTimeoutError(VideoToSTTError):
    code = "VIDEO_AUDIO_EXTRACTION_TIMEOUT"
    http_status = 504
    public_message = "Video audio extraction timed out."


class VideoAudioExtractionFailedError(VideoToSTTError):
    code = "VIDEO_AUDIO_EXTRACTION_FAILED"
    public_message = "Video audio extraction failed."


class VideoExtractedAudioInvalidError(VideoToSTTError):
    code = "VIDEO_EXTRACTED_AUDIO_INVALID"
    http_status = 422
    public_message = "The extracted audio could not be validated."


def _terminate_process(process: subprocess.Popen[bytes]) -> None:
    try:
        process.kill()
    except OSError:
        return
    try:
        process.wait(timeout=1)
    except (OSError, subprocess.TimeoutExpired):
        return


class VideoToSTTService:
    """Validate a video, extract bounded audio, then delegate to STTService."""

    def __init__(
        self,
        *,
        video_input: VoiceStudioVideoInputService | None = None,
        transcription_service: STTService | None = None,
        ffmpeg_binary: str | None = None,
        extraction_timeout_seconds: float | None = None,
        temp_dir: Path | None = None,
    ):
        self.video_input = video_input or VoiceStudioVideoInputService(
            temp_dir=temp_dir
        )
        self.transcription_service = transcription_service or stt_service
        self.ffmpeg_binary = (
            settings.FFMPEG_BINARY if ffmpeg_binary is None else ffmpeg_binary
        )
        self.extraction_timeout_seconds = (
            settings.VIDEO_AUDIO_EXTRACTION_TIMEOUT_SECONDS
            if extraction_timeout_seconds is None
            else extraction_timeout_seconds
        )
        self.temp_dir = (
            temp_dir
            if temp_dir is not None
            else getattr(self.video_input, "temp_dir", None)
        )

    async def transcribe_upload(
        self,
        upload: UploadFile,
        *,
        language: str | None = None,
    ) -> TranscriptionResult:
        async with self.video_input.validated_upload(upload) as validated:
            if not validated.metadata.has_audio:
                raise VideoNoAudioStreamError

            extracted_audio_path = self._create_temp_audio_path()
            try:
                await asyncio.to_thread(
                    self._extract_audio,
                    validated,
                    extracted_audio_path,
                )
                self._validate_extracted_audio(extracted_audio_path)
                result = await self._transcribe_extracted_audio(
                    extracted_audio_path,
                    language=language,
                )
                return self._with_video_metadata(result, validated)
            finally:
                extracted_audio_path.unlink(missing_ok=True)

    def _create_temp_audio_path(self) -> Path:
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix="adgen-voice-studio-audio-",
                suffix=EXTRACTED_AUDIO_EXTENSION,
                dir=str(self.temp_dir) if self.temp_dir else None,
                delete=False,
            ) as temporary_file:
                return Path(temporary_file.name)
        except OSError as error:
            raise VideoAudioExtractionFailedError from error

    def _extract_audio(
        self,
        validated: ValidatedVideoUpload,
        output_path: Path,
    ) -> None:
        if not isinstance(self.ffmpeg_binary, str) or not self.ffmpeg_binary.strip():
            raise FFmpegNotConfiguredError
        if self.extraction_timeout_seconds <= 0:
            raise VideoAudioExtractionTimeoutError

        args = [
            self.ffmpeg_binary,
            "-v",
            "error",
            "-nostdin",
            "-y",
            "-i",
            str(validated.path),
            "-map",
            "0:a:0",
            "-vn",
            "-ac",
            str(EXTRACTION_CHANNELS),
            "-ar",
            str(EXTRACTION_CHUNK_SAFE_SAMPLE_RATE),
            "-c:a",
            "flac",
            "-f",
            "flac",
            str(output_path),
        ]

        acquired = _EXTRACTION_SLOTS.acquire(
            timeout=max(float(self.extraction_timeout_seconds), 0.001)
        )
        if not acquired:
            raise VideoAudioExtractionTimeoutError
        try:
            try:
                process = subprocess.Popen(
                    args,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    shell=False,
                )
            except (FileNotFoundError, OSError) as error:
                raise FFmpegNotConfiguredError from error

            try:
                process.wait(timeout=self.extraction_timeout_seconds)
            except subprocess.TimeoutExpired as error:
                _terminate_process(process)
                raise VideoAudioExtractionTimeoutError from error
            except OSError as error:
                _terminate_process(process)
                raise VideoAudioExtractionFailedError from error
            if process.returncode != 0:
                raise VideoAudioExtractionFailedError
        finally:
            _EXTRACTION_SLOTS.release()

    @staticmethod
    def _validate_extracted_audio(audio_path: Path) -> None:
        try:
            size_bytes = audio_path.stat().st_size
        except OSError as error:
            raise VideoExtractedAudioInvalidError from error
        if size_bytes <= 0:
            raise VideoExtractedAudioInvalidError
        if size_bytes > settings.STT_AUDIO_MAX_SIZE:
            raise STTAudioTooLargeError

        try:
            probe_audio_file(
                audio_path,
                extension=EXTRACTED_AUDIO_EXTENSION,
                content_type=EXTRACTED_AUDIO_CONTENT_TYPE,
                max_duration_seconds=settings.STT_AUDIO_MAX_DURATION_SECONDS,
            )
        except VoiceConversionProbeNotConfiguredError as error:
            raise FFProbeNotConfiguredError from error
        except VoiceConversionAudioProbeTimeoutError as error:
            raise FFProbeTimeoutError from error
        except VoiceConversionAudioTooLongError as error:
            raise STTAudioTooLongError from error
        except VoiceConversionError as error:
            raise VideoExtractedAudioInvalidError from error

    async def _transcribe_extracted_audio(
        self,
        audio_path: Path,
        *,
        language: str | None,
    ) -> TranscriptionResult:
        try:
            audio_file = audio_path.open("rb")
        except OSError as error:
            raise VideoExtractedAudioInvalidError from error

        upload = UploadFile(
            file=audio_file,
            filename=EXTRACTED_AUDIO_FILENAME,
            headers=Headers({"content-type": EXTRACTED_AUDIO_CONTENT_TYPE}),
        )
        try:
            return await self.transcription_service.transcribe_upload(
                upload,
                language=language,
            )
        finally:
            await upload.close()

    @staticmethod
    def _with_video_metadata(
        result: TranscriptionResult,
        validated: ValidatedVideoUpload,
    ) -> TranscriptionResult:
        metadata: dict[str, str | int | float | bool | None] = {}
        for key, value in result.metadata.items():
            if key in {"path", "audio_path", "file_path", "credential", "token"}:
                continue
            if isinstance(value, (str, int, float, bool)) or value is None:
                metadata[key] = value
        metadata.update(
            {
                "source_type": "video",
                "video_container": validated.metadata.container_format,
                "video_duration_seconds": validated.metadata.duration_seconds,
                "video_has_audio": validated.metadata.has_audio,
            }
        )
        return TranscriptionResult(
            transcript=result.transcript,
            language=result.language,
            provider=result.provider,
            metadata=metadata,
        )


video_to_stt_service = VideoToSTTService()
