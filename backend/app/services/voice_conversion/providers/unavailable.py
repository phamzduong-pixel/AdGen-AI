from pathlib import Path

from app.services.voice_conversion.models import (
    VoiceConversionOptions,
    VoiceConversionProviderNotConfiguredError,
    VoiceConversionResult,
)
from app.services.voice_conversion.providers.base import BaseVoiceConversionProvider


class UnavailableVoiceConversionProvider(BaseVoiceConversionProvider):
    """Explicit fail-closed provider used before a real adapter is approved."""

    def __init__(self, reason: str = "provider_not_configured"):
        self.reason = reason

    @property
    def provider_id(self) -> str:
        return "unavailable"

    async def convert(
        self,
        source_audio_path: Path,
        *,
        source_content_type: str,
        target_voice_id: str,
        language: str | None,
        options: VoiceConversionOptions,
    ) -> VoiceConversionResult:
        raise VoiceConversionProviderNotConfiguredError(self.reason)

