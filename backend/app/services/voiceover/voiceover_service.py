import asyncio
import tempfile
import wave
import os
import subprocess
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.schemas.voiceover import (
    VoiceOption,
    CleanScriptResponse,
    VoiceoverGenerateRequest,
    VoiceoverGenerateResponse,
)
from app.services.voiceover.script_cleaner import ScriptCleaner
from app.services.voiceover.providers.base import BaseTTSProvider
from app.services.voiceover.providers.edge_tts_provider import EdgeTTSProvider
from app.services.voiceover.providers.mock_provider import MockTTSProvider
from fastapi import UploadFile
from app.services.voice_conversion.audio_probe import VoiceConversionAudioProbe
from app.services.voice_studio.video_input import (
    VideoDurationTooLongError,
    VideoInputError,
    VoiceStudioVideoProbe,
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
from app.services.voiceover.providers.vieneu_reference_provider import (
    ReferenceVoiceError,
    ReferenceVoiceFormatError,
    ReferenceVoiceInvalidError,
    ReferenceVoiceMimeMismatchError,
    ReferenceVoiceNoAudioError,
    ReferenceVoiceOutputInvalidError,
    ReferenceVoiceProviderTimeoutError,
    ReferenceVoiceTooLargeError,
    ReferenceVoiceTooLongError,
    VieNeuReferenceVoiceProvider,
)

logger = logging.getLogger(__name__)
REFERENCE_AUDIO_MIME_TYPES = {
    ".flac": {"audio/flac", "audio/x-flac"},
    ".m4a": {"audio/mp4", "audio/x-m4a"},
    ".mp3": {"audio/mpeg", "audio/mp3"},
    ".ogg": {"audio/ogg", "application/ogg"},
    ".wav": {"audio/wav", "audio/wave", "audio/x-wav"},
    ".webm": {"audio/webm"},
}
REFERENCE_VIDEO_MIME_TYPES = {
    ".mp4": {"video/mp4"},
    ".mov": {"video/quicktime", "video/mp4"},
    ".webm": {"video/webm"},
}
REFERENCE_TEMP_CHUNK_SIZE = 1024 * 1024

class VoiceoverService:
    """
    Central orchestration service for AdGen Voice Studio.
    Handles script cleaning, provider dispatch, audio persistence, and metadata calculation.
    """

    def __init__(self, provider: Optional[BaseTTSProvider] = None):
        self.audio_dir = Path(settings.UPLOAD_DIR) / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        # Default provider is EdgeTTSProvider with Mock fallback
        self.provider = provider or EdgeTTSProvider()
        self.mock_provider = MockTTSProvider()
        self.reference_provider = VieNeuReferenceVoiceProvider()

    async def get_available_voices(self) -> List[VoiceOption]:
        try:
            voices_data = await self.provider.get_available_voices()
            voices = [VoiceOption(**v) for v in voices_data]
            if self.reference_provider.is_configured():
                voices.extend(VoiceOption(**voice) for voice in self.reference_provider.PRESET_VOICES)
            return voices
        except Exception as e:
            logger.warning(f"Failed to fetch voices from primary provider: {e}. Falling back to mock.")
            fallback = await self.mock_provider.get_available_voices()
            return [VoiceOption(**v) for v in fallback]

    def clean_script(self, raw_script: str) -> CleanScriptResponse:
        extraction = ScriptCleaner.extract(raw_script)
        return CleanScriptResponse(
            cleaned_script=extraction.cleaned_script,
            original_length=extraction.original_length,
            cleaned_length=extraction.cleaned_length,
            removed_tags_count=extraction.dialogue_blocks_count,
            status=extraction.status,
            dialogue_blocks_count=extraction.dialogue_blocks_count,
            warning_message=extraction.warning_message
        )

    def _estimate_duration(self, text: str, speed: float) -> float:
        """
        Estimates audio duration in seconds.
        Standard Vietnamese reading speed is approx 150-180 words per minute (2.5 - 3 words/sec).
        """
        words = len(text.split())
        words_per_sec = 2.8 * (speed if speed > 0 else 1.0)
        estimated = max(1.0, words / words_per_sec)
        return round(estimated, 1)

    async def generate_voiceover(
        self,
        request: VoiceoverGenerateRequest,
        clean_first: bool = False
    ) -> VoiceoverGenerateResponse:
        text_to_read = request.text.strip()
        if not text_to_read:
            raise ValueError("Nội dung kịch bản để tạo audio không được để trống.")

        # If the input contains structured script labels (like VO:, Lời thoại:, Cảnh 1, etc.),
        # automatically extract the pure dialogue
        extraction = ScriptCleaner.extract(text_to_read)
        if extraction.status == "success" and extraction.cleaned_script:
            text_to_read = extraction.cleaned_script

        # Sanitize XML/SSML sensitive characters that break EdgeTTS
        text_to_read = text_to_read.replace('&', ' và ').replace('<', ' ').replace('>', ' ')

        if self.reference_provider.is_preset_voice(request.voice_id):
            return await self._generate_vieneu_preset_voiceover(request, text_to_read)

        audio_id = str(uuid.uuid4())
        filename = f"{audio_id}.mp3"
        file_path = self.audio_dir / filename

        # Synthesize via primary provider with retry and 60s timeout
        import asyncio
        audio_bytes = None
        last_error = None

        for attempt in range(2):
            try:
                audio_bytes = await asyncio.wait_for(
                    self.provider.synthesize(
                        text=text_to_read,
                        voice_id=request.voice_id,
                        speed=request.speed,
                        pitch=request.pitch or 0,
                        output_file_path=str(file_path)
                    ),
                    timeout=120.0
                )
                if audio_bytes and len(audio_bytes) > 2000:
                    break
            except Exception as e:
                last_error = e
                logger.warning(f"TTS synthesis attempt {attempt + 1} failed: {e}")
                if attempt == 0:
                    await asyncio.sleep(1.0)

        file_is_usable = False
        try:
            file_is_usable = file_path.is_file() and file_path.stat().st_size > 0
        except OSError:
            file_is_usable = False

        if not audio_bytes or len(audio_bytes) <= 2000 or not file_is_usable:
            try:
                file_path.unlink(missing_ok=True)
            except OSError:
                logger.warning("Could not clean up failed voiceover file %s", file_path)
            logger.error(f"TTS synthesis failed on primary provider: {last_error}")
            raise RuntimeError(
                f"Không thể tạo âm thanh lúc này từ dịch vụ TTS. Vui lòng thử lại sau vài giây."
            )

        file_size = file_path.stat().st_size
        duration_sec = self._estimate_duration(text_to_read, request.speed)

        # Get voice name for display
        voice_name = "Hoài My (Nữ)"
        try:
            voices = await self.get_available_voices()
            for v in voices:
                if v.id == request.voice_id:
                    voice_name = v.name
                    break
        except Exception:
            pass

        audio_url = f"/voiceover/audio/{filename}"
        download_url = f"/voiceover/audio/{filename}?download=true"

        return VoiceoverGenerateResponse(
            success=True,
            audio_id=audio_id,
            audio_url=audio_url,
            download_url=download_url,
            duration_seconds=duration_sec,
            file_size_bytes=file_size,
            voice_id=request.voice_id,
            voice_name=voice_name,
            speed=request.speed,
            cleaned_text=text_to_read
        )

    async def _generate_vieneu_preset_voiceover(self, request: VoiceoverGenerateRequest, text: str) -> VoiceoverGenerateResponse:
        audio_id = str(uuid.uuid4())
        output_path = self.audio_dir / f"{audio_id}.mp3"
        wav_path = self.audio_dir / f"{audio_id}.wav"
        try:
            _, duration_seconds = await self.reference_provider.synthesize_preset(text=text, voice_id=request.voice_id, output_audio_path=wav_path)
            try:
                await asyncio.to_thread(subprocess.run, [settings.FFMPEG_BINARY, "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav_path), "-vn", "-codec:a", "libmp3lame", "-q:a", "3", str(output_path)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False, check=True, timeout=settings.VIDEO_PROCESS_TIMEOUT_SECONDS)
            except (FileNotFoundError, OSError) as error:
                raise ReferenceVoiceError from error
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
                raise ReferenceVoiceOutputInvalidError from error
            if not output_path.is_file() or output_path.stat().st_size <= 0:
                raise ReferenceVoiceOutputInvalidError
            voice = next(voice for voice in self.reference_provider.PRESET_VOICES if voice["id"] == request.voice_id)
            return VoiceoverGenerateResponse(success=True, audio_id=audio_id, audio_url=f"/voiceover/audio/{audio_id}.mp3", download_url=f"/voiceover/audio/{audio_id}.mp3?download=true", duration_seconds=duration_seconds, file_size_bytes=output_path.stat().st_size, voice_id=request.voice_id, voice_name=voice["name"], speed=1.0, cleaned_text=text)
        except ReferenceVoiceError:
            output_path.unlink(missing_ok=True)
            raise
        finally:
            wav_path.unlink(missing_ok=True)
    async def generate_reference_voiceover(
        self,
        *,
        text: str,
        reference_audio: UploadFile,
    ) -> VoiceoverGenerateResponse:
        """Generate speech from reviewed text using a local reference voice."""

        request = VoiceoverGenerateRequest(text=text)
        text_to_read = request.text.strip()
        extraction = ScriptCleaner.extract(text_to_read)
        if extraction.status == "success" and extraction.cleaned_script:
            text_to_read = extraction.cleaned_script
        text_to_read = text_to_read.replace("&", " và ").replace("<", " ").replace(">", " ")

        safe_name = Path((reference_audio.filename or "").replace("\\", "/")).name.strip()
        extension = Path(safe_name).suffix.lower()
        content_type = (reference_audio.content_type or "").lower().split(";", 1)[0].strip()
        is_video_reference = extension in REFERENCE_VIDEO_MIME_TYPES
        if not safe_name or (
            extension not in REFERENCE_AUDIO_MIME_TYPES
            and extension not in REFERENCE_VIDEO_MIME_TYPES
        ):
            raise ReferenceVoiceFormatError
        allowed_mime_types = (
            REFERENCE_VIDEO_MIME_TYPES if is_video_reference else REFERENCE_AUDIO_MIME_TYPES
        )[extension]
        if content_type not in allowed_mime_types:
            raise ReferenceVoiceMimeMismatchError

        reference_path: Path | None = None
        reference_pcm_path: Path | None = None
        audio_id = str(uuid.uuid4())
        output_path = self.audio_dir / f"{audio_id}.mp3"
        generated_wav_path = self.audio_dir / f"{audio_id}.wav"
        try:
            total_size = 0
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix="adgen-reference-",
                suffix=extension,
                delete=False,
            ) as temporary_file:
                reference_path = Path(temporary_file.name)
                while chunk := await reference_audio.read(REFERENCE_TEMP_CHUNK_SIZE):
                    total_size += len(chunk)
                    max_size_bytes = (
                        settings.MAX_VIDEO_SIZE
                        if is_video_reference
                        else settings.VIENEU_REFERENCE_MAX_SIZE_BYTES
                    )
                    if total_size > max_size_bytes:
                        raise ReferenceVoiceTooLargeError
                    temporary_file.write(chunk)
            if total_size == 0:
                raise ReferenceVoiceInvalidError

            if is_video_reference:
                try:
                    video_metadata = VoiceStudioVideoProbe().validate_path(
                        reference_path,
                        extension=extension,
                        content_type=content_type,
                    )
                except VideoDurationTooLongError as error:
                    raise ReferenceVoiceTooLongError from error
                except VideoInputError as error:
                    raise ReferenceVoiceInvalidError from error
                if not video_metadata.has_audio:
                    raise ReferenceVoiceNoAudioError
                if (
                    video_metadata.duration_seconds
                    > settings.VIENEU_REFERENCE_MAX_DURATION_SECONDS
                ):
                    raise ReferenceVoiceTooLongError
            else:
                try:
                    VoiceConversionAudioProbe().validate(
                        reference_path,
                        extension=extension,
                        content_type=content_type,
                        max_duration_seconds=settings.VIENEU_REFERENCE_MAX_DURATION_SECONDS,
                    )
                except VoiceConversionAudioTooLongError as error:
                    raise ReferenceVoiceTooLongError from error
                except (
                    VoiceConversionAudioInvalidError,
                    VoiceConversionAudioProbeOutputTooLargeError,
                    VoiceConversionAudioProbeTimeoutError,
                    VoiceConversionProbeMetadataError,
                    VoiceConversionProbeNotConfiguredError,
                    VoiceConversionUnsupportedContainerError,
                ) as error:
                    raise ReferenceVoiceInvalidError from error

            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix="adgen-reference-pcm-",
                suffix=".wav",
                delete=False,
            ) as pcm_file:
                reference_pcm_path = Path(pcm_file.name)
            try:
                await asyncio.to_thread(
                    subprocess.run,
                    [
                        settings.FFMPEG_BINARY,
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-y",
                        "-i",
                        str(reference_path),
                        "-vn",
                        "-ac",
                        "1",
                        "-ar",
                        "16000",
                        "-c:a",
                        "pcm_s16le",
                        str(reference_pcm_path),
                    ],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    shell=False,
                    check=True,
                    timeout=settings.VIDEO_PROCESS_TIMEOUT_SECONDS,
                )
            except FileNotFoundError as error:
                raise ReferenceVoiceError from error
            except subprocess.TimeoutExpired as error:
                raise ReferenceVoiceProviderTimeoutError from error
            except (OSError, subprocess.CalledProcessError) as error:
                raise ReferenceVoiceInvalidError from error

            audio_bytes, duration_seconds = await asyncio.wait_for(
                self.reference_provider.synthesize(
                    text=text_to_read,
                    reference_audio_path=reference_pcm_path,
                    output_audio_path=generated_wav_path,
                ),
                timeout=settings.VIENEU_PROVIDER_TIMEOUT_SECONDS + 5,
            )
            try:
                await asyncio.to_thread(
                    subprocess.run,
                    [
                        settings.FFMPEG_BINARY,
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-y",
                        "-i",
                        str(generated_wav_path),
                        "-vn",
                        "-codec:a",
                        "libmp3lame",
                        "-q:a",
                        "3",
                        str(output_path),
                    ],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    shell=False,
                    check=True,
                    timeout=settings.VIDEO_PROCESS_TIMEOUT_SECONDS,
                )
            except (FileNotFoundError, OSError) as error:
                raise ReferenceVoiceError from error
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
                raise ReferenceVoiceOutputInvalidError from error
            try:
                VoiceConversionAudioProbe().validate(
                    reference_pcm_path,
                    extension=".wav",
                    content_type="audio/wav",
                    max_duration_seconds=settings.VIENEU_REFERENCE_MAX_DURATION_SECONDS,
                )
            except VoiceConversionAudioTooLongError as error:
                raise ReferenceVoiceTooLongError from error
            except (
                VoiceConversionAudioInvalidError,
                VoiceConversionAudioProbeOutputTooLargeError,
                VoiceConversionAudioProbeTimeoutError,
                VoiceConversionProbeMetadataError,
                VoiceConversionProbeNotConfiguredError,
                VoiceConversionUnsupportedContainerError,
            ) as error:
                raise ReferenceVoiceInvalidError from error
            if not audio_bytes or not output_path.is_file():
                raise ReferenceVoiceError

            file_size = output_path.stat().st_size
            return VoiceoverGenerateResponse(
                success=True,
                audio_id=audio_id,
                audio_url=f"/voiceover/audio/{audio_id}.mp3",
                download_url=f"/voiceover/audio/{audio_id}.mp3?download=true",
                duration_seconds=duration_seconds,
                file_size_bytes=file_size,
                voice_id=self.reference_provider.provider_id,
                voice_name="Giọng tham chiếu (VieNeu-TTS local)",
                speed=1.0,
                cleaned_text=text_to_read,
            )
        except ReferenceVoiceError:
            output_path.unlink(missing_ok=True)
            generated_wav_path.unlink(missing_ok=True)
            raise
        except asyncio.TimeoutError as error:
            output_path.unlink(missing_ok=True)
            generated_wav_path.unlink(missing_ok=True)
            raise ReferenceVoiceProviderTimeoutError from error
        except Exception as error:
            output_path.unlink(missing_ok=True)
            generated_wav_path.unlink(missing_ok=True)
            raise ReferenceVoiceError from error
        finally:
            try:
                await reference_audio.close()
            finally:
                generated_wav_path.unlink(missing_ok=True)
                if reference_path is not None:
                    reference_path.unlink(missing_ok=True)
                if reference_pcm_path is not None:
                    reference_pcm_path.unlink(missing_ok=True)

# Global singleton instance
voiceover_service = VoiceoverService()
