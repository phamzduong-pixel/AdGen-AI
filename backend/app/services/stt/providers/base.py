from collections.abc import Mapping
from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from app.services.stt.models import TranscriptionResult


class BaseSTTProvider(ABC):
    """Provider-neutral interface for audio transcription."""

    supported_audio_codecs: ClassVar[Mapping[str, frozenset[str]]] = {}

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Stable identifier exposed in a successful response."""

    @abstractmethod
    async def transcribe(
        self,
        audio_path: Path,
        *,
        content_type: str,
        language: str | None,
    ) -> TranscriptionResult:
        """Transcribe one temporary audio file without owning its lifecycle."""
