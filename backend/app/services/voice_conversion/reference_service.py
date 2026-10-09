"""Request-scoped Seed-VC conversion with a supplied or bundled voice prompt."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.services.voice_conversion.audio_probe import probe_audio_file
from app.services.voice_conversion.models import (
    VoiceConversionEmptyAudioError,
    VoiceConversionError,
    VoiceConversionOutputInvalidError,
    VoiceConversionReferenceRequiredError,
    VoiceConversionResult,
    VoiceConversionTooLargeError,
)
from app.services.voice_conversion.ref_audio_manager import ReferenceAudioManager
from app.services.voice_conversion.seed_vc_converter import SeedVCConverter
from app.services.voice_conversion.service import (
    SUPPORTED_AUDIO_MIME_TYPES,
    TEMP_CHUNK_SIZE,
    _normalize_content_type,
    _safe_filename,
)


class SeedVCReferenceService:
    """Validate uploads, run CPU Seed-VC, and delete every request artifact."""

    def __init__(
        self,
        *,
        converter: SeedVCConverter | None = None,
        reference_manager: ReferenceAudioManager | None = None,
    ) -> None:
        self.converter = converter or SeedVCConverter()
        self.reference_manager = reference_manager or ReferenceAudioManager()

    @staticmethod
    async def _write_upload(upload: UploadFile, extension: str, prefix: str) -> Path:
        total_size = 0
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix=prefix, suffix=extension, delete=False
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                while chunk := await upload.read(TEMP_CHUNK_SIZE):
                    total_size += len(chunk)
                    if total_size > settings.VC_AUDIO_MAX_SIZE_BYTES:
                        raise VoiceConversionTooLargeError
                    temporary_file.write(chunk)
            if total_size <= 0:
                raise VoiceConversionEmptyAudioError
            return temporary_path
        except Exception:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise

    @staticmethod
    async def _validated_upload(upload: UploadFile, prefix: str) -> tuple[Path, str]:
        _, extension = _safe_filename(upload.filename)
        content_type = _normalize_content_type(upload.content_type)
        if content_type not in SUPPORTED_AUDIO_MIME_TYPES[extension]:
            from app.services.voice_conversion.models import VoiceConversionMimeMismatchError
            raise VoiceConversionMimeMismatchError
        path = await SeedVCReferenceService._write_upload(upload, extension, prefix)
        try:
            probe_audio_file(path, extension=extension, content_type=content_type)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return path, content_type

    async def convert_upload(
        self,
        source_upload: UploadFile,
        *,
        reference_upload: UploadFile | None,
        preset_voice_id: str | None,
    ) -> VoiceConversionResult:
        if settings.VC_PROVIDER != "seed-vc":
            from app.services.voice_conversion.models import VoiceConversionProviderNotConfiguredError
            raise VoiceConversionProviderNotConfiguredError("VC_PROVIDER must be seed-vc")
        if reference_upload is None and not preset_voice_id:
            raise VoiceConversionReferenceRequiredError

        source_path: Path | None = None
        custom_reference_path: Path | None = None
        output_path: Path | None = None
        try:
            source_path, _ = await self._validated_upload(source_upload, "adgen-vc-source-")
            if reference_upload is not None:
                custom_reference_path, _ = await self._validated_upload(
                    reference_upload, "adgen-vc-reference-"
                )
            reference_path = self.reference_manager.resolve(
                preset_voice_id=preset_voice_id,
                custom_ref_path=custom_reference_path,
            )
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix="adgen-vc-output-", suffix=".wav", delete=False
            ) as temporary_file:
                output_path = Path(temporary_file.name)
            return await self.convert_paths(source_path, reference_path)
        except VoiceConversionError:
            raise
        except Exception as error:
            raise VoiceConversionError from error
        finally:
            for path in (source_path, custom_reference_path):
                if path is not None:
                    path.unlink(missing_ok=True)
            await source_upload.close()
            if reference_upload is not None:
                await reference_upload.close()

    async def convert_paths(
        self, source_path: Path, reference_path: Path
    ) -> VoiceConversionResult:
        """Convert validated local audio paths; the caller owns input cleanup."""
        output_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix="adgen-vc-output-", suffix=".wav", delete=False
            ) as temporary_file:
                output_path = Path(temporary_file.name)
            await asyncio.to_thread(
                self.converter.convert, str(source_path), str(reference_path), str(output_path)
            )
            if not output_path.is_file() or output_path.stat().st_size <= 0:
                raise VoiceConversionOutputInvalidError
            audio_bytes = output_path.read_bytes()
            if len(audio_bytes) > settings.VC_OUTPUT_MAX_SIZE_BYTES:
                raise VoiceConversionOutputInvalidError("Seed-VC output exceeds configured limit")
            return VoiceConversionResult(
                audio_bytes=audio_bytes,
                content_type="audio/wav",
                file_extension=".wav",
                provider_id="seed-vc-cpu",
            )
        except VoiceConversionError:
            raise
        except Exception as error:
            raise VoiceConversionError from error
        finally:
            if output_path is not None:
                output_path.unlink(missing_ok=True)


seed_vc_reference_service = SeedVCReferenceService()

