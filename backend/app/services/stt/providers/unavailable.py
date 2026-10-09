from pathlib import Path

from app.services.stt.models import STTProviderNotConfiguredError, TranscriptionResult
from app.services.stt.providers.base import BaseSTTProvider


class UnavailableSTTProvider(BaseSTTProvider):
    """Explicit fail-closed provider used when no real adapter is ready."""

    def __init__(self, reason: str = "provider_not_configured"):
        self.reason = reason

    @property
    def provider_id(self) -> str:
        return "unavailable"

    async def transcribe(
        self,
        audio_path: Path,
        *,
        content_type: str,
        language: str | None,
    ) -> TranscriptionResult:
        raise STTProviderNotConfiguredError(self.reason)
