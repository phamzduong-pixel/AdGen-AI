from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class GeneratedImage:
    data: bytes
    content_type: str = "image/png"


class ImageGenerationProvider(ABC):
    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Stable provider identifier stored with the asset."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier stored with the asset."""

    @abstractmethod
    async def generate(
        self,
        *,
        prompt: str,
        aspect_ratio: str,
        reference_image: bytes | None = None,
        reference_content_type: str | None = None,
    ) -> GeneratedImage:
        """Generate an image, optionally using one image as an edit reference."""
