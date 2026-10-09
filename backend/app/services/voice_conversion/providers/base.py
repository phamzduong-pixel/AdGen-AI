from abc import ABC, abstractmethod
from pathlib import Path

from app.services.voice_conversion.models import (
    VoiceConversionOptions,
    VoiceConversionResult,
)


class BaseVoiceConversionProvider(ABC):
    """Provider interface for audio-to-audio voice conversion."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Stable provider identifier used in safe response metadata."""

    @abstractmethod
    async def convert(
        self,
        source_audio_path: Path,
        *,
        source_content_type: str,
        target_voice_id: str,
        language: str | None,
        options: VoiceConversionOptions,
    ) -> VoiceConversionResult:
        """Convert source audio directly to the requested target voice."""

