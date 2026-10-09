import asyncio
import re
import tempfile
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.services.voice_conversion.models import (
    VoiceConversionEmptyAudioError,
    VoiceConversionError,
    VoiceConversionInvalidLanguageError,
    VoiceConversionMimeMismatchError,
    VoiceConversionOptions,
    VoiceConversionOutputInvalidError,
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


from app.services.voice_conversion.audio_probe import probe_audio_file

SUPPORTED_AUDIO_MIME_TYPES = {
    ".flac": {"audio/flac", "audio/x-flac"},
    ".m4a": {"audio/mp4", "audio/x-m4a"},
    ".mp3": {"audio/mpeg", "audio/mp3"},
    ".oga": {"audio/ogg", "application/ogg"},
    ".ogg": {"audio/ogg", "application/ogg"},
    ".wav": {"audio/wav", "audio/wave", "audio/x-wav"},
    ".webm": {"audio/webm"},
}
SUPPORTED_OUTPUT_FORMATS = {"mp3", "wav"}
TEMP_CHUNK_SIZE = 1024 * 1024
LANGUAGE_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,20}$")
SAFE_METADATA_KEYS = {
    "filename",
    "content_type",
    "size_bytes",
    "output_format",
    "duration_seconds",
}


def _safe_filename(filename: str | None) -> tuple[str, str]:
    if not filename:
        raise VoiceConversionUnsupportedFormatError("Audio filename is missing")

    safe_name = Path(filename.replace("\\", "/")).name.strip()
    extension = Path(safe_name).suffix.lower()
    if not safe_name or extension not in SUPPORTED_AUDIO_MIME_TYPES:
        raise VoiceConversionUnsupportedFormatError(
            "Audio extension is not supported"
        )
    return safe_name, extension


def _normalize_content_type(content_type: str | None) -> str:
    return (content_type or "").lower().split(";", 1)[0].strip()


def _validate_language(language: str | None) -> str | None:
    if language is None or not language.strip():
        return None
    normalized = language.strip()
    if not LANGUAGE_PATTERN.fullmatch(normalized):
        raise VoiceConversionInvalidLanguageError(
            "Language code contains unsupported characters"
        )
    return normalized


def _normalize_output_format(output_format: str | None) -> str:
    normalized = (output_format or "mp3").strip().lower()
    if normalized not in SUPPORTED_OUTPUT_FORMATS:
        raise VoiceConversionUnsupportedOutputFormatError(
            "Output format is not supported"
        )
    return normalized


class VoiceConversionService:
    def __init__(self, provider: BaseVoiceConversionProvider | None = None):
        self.provider = provider or build_voice_conversion_provider()

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
                prefix="adgen-voice-conversion-",
                suffix=extension,
                delete=False,
            ) as temporary_file:
                temp_path = Path(temporary_file.name)
                while chunk := await upload.read(TEMP_CHUNK_SIZE):
                    total_size += len(chunk)
                    if total_size > settings.VC_AUDIO_MAX_SIZE_BYTES:
                        raise VoiceConversionTooLargeError(
                            "Audio exceeds the configured limit"
                        )
                    temporary_file.write(chunk)

            if total_size == 0:
                raise VoiceConversionEmptyAudioError("Audio has no content")
            return temp_path, total_size
        except Exception:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            raise

    @staticmethod
    def _safe_result_metadata(
        result: VoiceConversionResult,
        *,
        filename: str,
        source_content_type: str,
        source_size_bytes: int,
    ) -> dict[str, str | int | float | bool | None]:
        metadata: dict[str, str | int | float | bool | None] = {
            "filename": filename,
            "content_type": source_content_type,
            "size_bytes": source_size_bytes,
        }
        for key, value in result.metadata.items():
            if key not in SAFE_METADATA_KEYS:
                continue
            if isinstance(value, (str, int, float, bool)) or value is None:
                metadata[key] = value
        return metadata

    @staticmethod
    def _validate_provider_result(result: VoiceConversionResult) -> None:
        if not isinstance(result, VoiceConversionResult):
            raise VoiceConversionOutputInvalidError(
                "Provider returned an invalid result type"
            )
        if not result.audio_bytes:
            raise VoiceConversionOutputInvalidError("Provider returned empty audio")
        if result.content_type not in {
            "audio/mpeg",
            "audio/wav",
            "audio/wave",
            "audio/x-wav",
        }:
            raise VoiceConversionOutputInvalidError(
                "Provider returned an unsupported content type"
            )
        if result.file_extension.lower() not in {".mp3", ".wav"}:
            raise VoiceConversionOutputInvalidError(
                "Provider returned an unsupported file extension"
            )
        if not result.provider_id.strip():
            raise VoiceConversionOutputInvalidError(
                "Provider returned no provider identifier"
            )
        if len(result.audio_bytes) > settings.VC_OUTPUT_MAX_SIZE_BYTES:
            raise VoiceConversionOutputInvalidError(
                "Provider output exceeds the configured limit"
            )

    async def convert_upload(
        self,
        upload: UploadFile,
        *,
        target_voice_id: str | None,
        language: str | None = None,
        output_format: str | None = "mp3",
        remove_background_noise: bool = False,
    ) -> VoiceConversionResult:
        if target_voice_id is None or not target_voice_id.strip():
            raise VoiceConversionTargetVoiceRequiredError
        normalized_target_voice_id = target_voice_id.strip()
        configured_language = _validate_language(language)
        configured_output_format = _normalize_output_format(output_format)

        safe_name, extension = _safe_filename(upload.filename)
        content_type = _normalize_content_type(upload.content_type)
        if content_type not in SUPPORTED_AUDIO_MIME_TYPES[extension]:
            raise VoiceConversionMimeMismatchError(
                "Audio MIME does not match extension"
            )

        temp_path: Path | None = None
        try:
            temp_path, size_bytes = await self._write_temp_audio(
                upload,
                extension=extension,
            )
            probe_audio_file(
                temp_path,
                extension=extension,
                content_type=content_type,
            )
            options = VoiceConversionOptions(
                output_format=configured_output_format,  # type: ignore[arg-type]
                remove_background_noise=remove_background_noise,
            )
            try:
                result = await asyncio.wait_for(
                    self.provider.convert(
                        temp_path,
                        source_content_type=content_type,
                        target_voice_id=normalized_target_voice_id,
                        language=configured_language,
                        options=options,
                    ),
                    timeout=settings.VC_PROVIDER_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError as error:
                from app.services.voice_conversion.models import (
                    VoiceConversionProviderTimeoutError,
                )

                raise VoiceConversionProviderTimeoutError from error
            except VoiceConversionError:
                raise
            except Exception as error:
                raise VoiceConversionError from error

            self._validate_provider_result(result)
            result_metadata = self._safe_result_metadata(
                result,
                filename=safe_name,
                source_content_type=content_type,
                source_size_bytes=size_bytes,
            )
            return VoiceConversionResult(
                audio_bytes=result.audio_bytes,
                content_type=result.content_type,
                file_extension=result.file_extension,
                provider_id=result.provider_id,
                duration_seconds=result.duration_seconds,
                metadata=result_metadata,
            )
        finally:
            try:
                await upload.close()
            finally:
                if temp_path is not None:
                    temp_path.unlink(missing_ok=True)


voice_conversion_service = VoiceConversionService()

