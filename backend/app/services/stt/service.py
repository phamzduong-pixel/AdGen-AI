import asyncio
import tempfile
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.services.stt.models import (
    STTAudioTooLargeError,
    STTAudioTooLongError,
    STTAudioProbeNotConfiguredError,
    STTAudioProbeTimeoutError,
    STTAudioValidationError,
    STTEmptyAudioError,
    STTError,
    STTInvalidLanguageError,
    STTProviderTimeoutError,
    STTUnsupportedCodecError,
    STTUnsupportedFormatError,
    STTUnsupportedMimeTypeError,
    TranscriptionResult,
)
from app.services.stt.providers.base import BaseSTTProvider
from app.services.stt.providers.factory import build_stt_provider
from app.services.voice_conversion.audio_probe import VoiceConversionAudioProbe
from app.services.voice_conversion.models import (
    VoiceConversionAudioInvalidError,
    VoiceConversionAudioProbeOutputTooLargeError,
    VoiceConversionAudioProbeTimeoutError,
    VoiceConversionAudioTooLongError,
    VoiceConversionProbeMetadataError,
    VoiceConversionProbeNotConfiguredError,
    VoiceConversionUnsupportedContainerError,
)


SUPPORTED_AUDIO_MIME_TYPES = {
    ".flac": {"audio/flac", "audio/x-flac"},
    ".m4a": {"audio/mp4", "audio/x-m4a"},
    ".mp3": {"audio/mpeg", "audio/mp3"},
    ".ogg": {"audio/ogg", "application/ogg"},
    ".wav": {"audio/wav", "audio/wave", "audio/x-wav"},
    ".webm": {"audio/webm"},
}
TEMP_CHUNK_SIZE = 1024 * 1024


def _safe_filename(filename: str | None) -> tuple[str, str]:
    if not filename:
        raise STTUnsupportedFormatError("Audio filename is missing")

    safe_name = Path(filename.replace("\\", "/")).name.strip()
    extension = Path(safe_name).suffix.lower()
    if not safe_name or extension not in SUPPORTED_AUDIO_MIME_TYPES:
        raise STTUnsupportedFormatError("Audio extension is not supported")
    return safe_name, extension


def _normalize_content_type(content_type: str | None) -> str:
    return (content_type or "").lower().split(";", 1)[0].strip()


def _validate_language(language: str | None) -> str | None:
    if language is None or not language.strip():
        return settings.STT_DEFAULT_LANGUAGE or None
    normalized = language.strip()
    if len(normalized) > 20 or not all(
        character.isalnum() or character == "-" for character in normalized
    ):
        raise STTInvalidLanguageError("Language code contains unsupported characters")
    return normalized


def _validate_provider_codec(
    provider: BaseSTTProvider,
    *,
    extension: str,
    codec_name: str,
) -> None:
    supported_codecs = getattr(provider, "supported_audio_codecs", {}).get(extension)
    if supported_codecs and codec_name.strip().lower() not in supported_codecs:
        raise STTUnsupportedCodecError


class STTService:
    def __init__(
        self,
        provider: BaseSTTProvider | None = None,
        *,
        audio_probe: VoiceConversionAudioProbe | None = None,
    ):
        self.provider = provider or build_stt_provider()
        self.audio_probe = audio_probe or VoiceConversionAudioProbe()

    async def _write_temp_audio(
        self,
        upload: UploadFile,
        *,
        extension: str,
    ) -> tuple[Path, int]:
        temp_path: Path | None = None
        total_size = 0
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix="adgen-stt-",
                suffix=extension,
                delete=False,
            ) as temporary_file:
                temp_path = Path(temporary_file.name)
                while chunk := await upload.read(TEMP_CHUNK_SIZE):
                    total_size += len(chunk)
                    if total_size > settings.STT_AUDIO_MAX_SIZE:
                        raise STTAudioTooLargeError("Audio exceeds the configured limit")
                    temporary_file.write(chunk)

            if total_size == 0:
                raise STTEmptyAudioError("Audio has no content")
            return temp_path, total_size
        except Exception:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            raise

    async def transcribe_upload(
        self,
        upload: UploadFile,
        *,
        language: str | None = None,
    ) -> TranscriptionResult:
        safe_name, extension = _safe_filename(upload.filename)
        content_type = _normalize_content_type(upload.content_type)
        if content_type not in SUPPORTED_AUDIO_MIME_TYPES[extension]:
            raise STTUnsupportedMimeTypeError("Audio MIME does not match extension")

        configured_language = _validate_language(language)
        temp_path: Path | None = None
        try:
            temp_path, size_bytes = await self._write_temp_audio(
                upload,
                extension=extension,
            )
            try:
                probe_result = self.audio_probe.validate(
                    temp_path,
                    extension=extension,
                    content_type=content_type,
                    max_duration_seconds=settings.STT_AUDIO_MAX_DURATION_SECONDS,
                )
                _validate_provider_codec(
                    self.provider,
                    extension=extension,
                    codec_name=probe_result.codec_name,
                )
            except VoiceConversionAudioTooLongError as error:
                raise STTAudioTooLongError from error
            except (
                VoiceConversionProbeNotConfiguredError,
                VoiceConversionAudioProbeTimeoutError,
            ) as error:
                if isinstance(error, VoiceConversionProbeNotConfiguredError):
                    raise STTAudioProbeNotConfiguredError from error
                raise STTAudioProbeTimeoutError from error
            except (
                VoiceConversionAudioInvalidError,
                VoiceConversionAudioProbeOutputTooLargeError,
                VoiceConversionProbeMetadataError,
                VoiceConversionUnsupportedContainerError,
            ) as error:
                raise STTAudioValidationError from error
            try:
                result = await asyncio.wait_for(
                    self.provider.transcribe(
                        temp_path,
                        content_type=content_type,
                        language=configured_language,
                    ),
                    timeout=settings.STT_PROVIDER_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError as error:
                raise STTProviderTimeoutError from error
            except STTError:
                raise
            except Exception as error:
                raise STTError from error

            if not isinstance(result, TranscriptionResult):
                raise STTError("STT provider returned an invalid result")

            metadata = {
                "filename": safe_name,
                "content_type": content_type,
                "size_bytes": size_bytes,
            }
            for key, value in result.metadata.items():
                if key in {"path", "audio_path", "file_path", "credential", "token"}:
                    continue
                if isinstance(value, (str, int, float, bool)) or value is None:
                    metadata[key] = value
            return TranscriptionResult(
                transcript=result.transcript,
                language=result.language or configured_language,
                provider=result.provider,
                metadata=metadata,
            )
        finally:
            try:
                await upload.close()
            finally:
                if temp_path is not None:
                    temp_path.unlink(missing_ok=True)


stt_service = STTService()
