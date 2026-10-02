from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal


VideoJobStatus = Literal["queued", "processing", "completed", "failed", "cancelled"]
MAX_REFERENCE_IMAGES = 3


@dataclass(frozen=True)
class VideoGenerationInput:
    prompt: str
    aspect_ratio: str
    duration_seconds: float | None
    references: tuple[tuple[bytes, str], ...] = ()


@dataclass(frozen=True)
class VideoGenerationSubmission:
    provider_job_id: str
    status: VideoJobStatus = "queued"


@dataclass(frozen=True)
class VideoGenerationStatus:
    provider_job_id: str
    status: VideoJobStatus
    error_message: str | None = None


@dataclass(frozen=True)
class GeneratedVideo:
    data: bytes
    content_type: str = "video/mp4"


class VideoGenerationProviderError(RuntimeError):
    """A provider submission, polling, or retrieval failure."""


class VideoGenerationProviderUnavailable(VideoGenerationProviderError):
    """Raised when no real video generation provider is configured."""


class VideoGenerationProvider(ABC):
    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Stable provider identifier stored on the media job."""

    @property
    @abstractmethod
    def model_name(self) -> str | None:
        """Provider model identifier, when configured."""

    @abstractmethod
    async def submit(
        self, request: VideoGenerationInput
    ) -> VideoGenerationSubmission:
        """Submit an asynchronous generation request."""

    @abstractmethod
    async def get_status(self, provider_job_id: str) -> VideoGenerationStatus:
        """Read provider job state without exposing provider details to the API."""

    @abstractmethod
    async def retrieve_result(self, provider_job_id: str) -> GeneratedVideo:
        """Download the completed provider result."""


class UnavailableVideoGenerationProvider(VideoGenerationProvider):
    """Explicit no-op adapter until a real video provider is configured."""

    @property
    def provider_id(self) -> str:
        return "unavailable"

    @property
    def model_name(self) -> str | None:
        return None

    async def submit(self, request: VideoGenerationInput) -> VideoGenerationSubmission:
        raise VideoGenerationProviderUnavailable(
            "AI video generation provider chưa được cấu hình"
        )

    async def get_status(self, provider_job_id: str) -> VideoGenerationStatus:
        raise VideoGenerationProviderUnavailable(
            "AI video generation provider chưa được cấu hình"
        )

    async def retrieve_result(self, provider_job_id: str) -> GeneratedVideo:
        raise VideoGenerationProviderUnavailable(
            "AI video generation provider chưa được cấu hình"
        )
