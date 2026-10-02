import os
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

logger = logging.getLogger(__name__)

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

    async def get_available_voices(self) -> List[VoiceOption]:
        try:
            voices_data = await self.provider.get_available_voices()
            return [VoiceOption(**v) for v in voices_data]
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
                    timeout=60.0
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

# Global singleton instance
voiceover_service = VoiceoverService()
