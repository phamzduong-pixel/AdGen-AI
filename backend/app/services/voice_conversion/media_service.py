"""Video source support for Seed-VC: extract, convert, then remux."""

from __future__ import annotations

import asyncio
import subprocess
import tempfile
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.services.voice_conversion.models import VoiceConversionError, VoiceConversionOutputInvalidError
from app.services.voice_conversion.reference_service import SeedVCReferenceService, seed_vc_reference_service
from app.services.voice_conversion.ref_audio_manager import ReferenceAudioManager
from app.services.voice_studio.video_input import (
    VideoInputError,
    VideoNoAudioStreamError,
    VoiceStudioVideoInputService,
)


class VideoVoiceConversionError(VoiceConversionError):
    code = "VC_VIDEO_PROCESSING_FAILED"
    public_message = "Video voice conversion failed."


class VideoVoiceConversionTimeoutError(VideoVoiceConversionError):
    code = "VC_VIDEO_PROCESSING_TIMEOUT"
    http_status = 504
    public_message = "Video voice conversion timed out."


class VideoVoiceConversionNotConfiguredError(VideoVoiceConversionError):
    code = "VC_VIDEO_TOOL_NOT_CONFIGURED"
    http_status = 503
    public_message = "Video processing tool is not configured."


class SeedVCMediaService:
    def __init__(
        self,
        *,
        reference_service: SeedVCReferenceService | None = None,
        video_input: VoiceStudioVideoInputService | None = None,
    ) -> None:
        self.reference_service = reference_service or seed_vc_reference_service
        self.video_input = video_input or VoiceStudioVideoInputService()

    @staticmethod
    def _run(args: list[str]) -> None:
        try:
            completed = subprocess.run(
                args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, shell=False,
                timeout=settings.VC_PROVIDER_TIMEOUT_SECONDS,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False,
            )
        except FileNotFoundError as error:
            raise VideoVoiceConversionNotConfiguredError from error
        except subprocess.TimeoutExpired as error:
            raise VideoVoiceConversionTimeoutError from error
        if completed.returncode != 0:
            raise VideoVoiceConversionError

    async def convert_video_upload(
        self,
        source_upload: UploadFile,
        *,
        reference_upload: UploadFile | None,
        preset_voice_id: str | None,
    ) -> tuple[bytes, str, str]:
        if settings.VC_PROVIDER != "seed-vc":
            from app.services.voice_conversion.models import VoiceConversionProviderNotConfiguredError
            raise VoiceConversionProviderNotConfiguredError("VC_PROVIDER must be seed-vc")
        reference_path: Path | None = None
        extracted_path: Path | None = None
        converted_path: Path | None = None
        remuxed_path: Path | None = None
        try:
            if reference_upload is not None:
                reference_path, _ = await self.reference_service._validated_upload(
                    reference_upload, "adgen-vc-reference-"
                )
            target_reference = ReferenceAudioManager().resolve(
                preset_voice_id=preset_voice_id, custom_ref_path=reference_path
            )
            async with self.video_input.validated_upload(source_upload) as validated:
                if not validated.metadata.has_audio:
                    raise VideoNoAudioStreamError
                extracted_path = Path(tempfile.NamedTemporaryFile(prefix="adgen-vc-video-", suffix=".wav", delete=False).name)
                await asyncio.to_thread(self._run, [
                    settings.FFMPEG_BINARY, "-v", "error", "-nostdin", "-y", "-i", str(validated.path),
                    "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "44100", "-c:a", "pcm_s16le", str(extracted_path),
                ])
                result = await self.reference_service.convert_paths(extracted_path, target_reference)
                converted_path = Path(tempfile.NamedTemporaryFile(prefix="adgen-vc-converted-", suffix=".wav", delete=False).name)
                converted_path.write_bytes(result.audio_bytes)
                extension = ".webm" if validated.extension == ".webm" else ".mp4"
                content_type = "video/webm" if extension == ".webm" else "video/mp4"
                remuxed_path = Path(tempfile.NamedTemporaryFile(prefix="adgen-vc-remuxed-", suffix=extension, delete=False).name)
                audio_codec = "libopus" if extension == ".webm" else "aac"
                await asyncio.to_thread(self._run, [
                    settings.FFMPEG_BINARY, "-v", "error", "-nostdin", "-y", "-i", str(validated.path),
                    "-i", str(converted_path), "-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "copy", "-c:a", audio_codec, "-shortest", str(remuxed_path),
                ])
                if not remuxed_path.is_file() or remuxed_path.stat().st_size <= 0:
                    raise VoiceConversionOutputInvalidError
                return remuxed_path.read_bytes(), content_type, extension
        except VideoInputError as error:
            raise VideoVoiceConversionError(error.public_message) from error
        finally:
            for path in (reference_path, extracted_path, converted_path, remuxed_path):
                if path is not None:
                    path.unlink(missing_ok=True)
            if reference_upload is not None:
                await reference_upload.close()


seed_vc_media_service = SeedVCMediaService()

