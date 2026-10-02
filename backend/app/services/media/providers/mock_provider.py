import base64

from app.services.media.providers.base import GeneratedImage, ImageGenerationProvider


class MockImageProvider(ImageGenerationProvider):
    """Offline provider used by tests and local UI smoke checks."""

    _PNG = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
        "YAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    )

    @property
    def provider_id(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-image-v1"

    async def generate(
        self,
        *,
        prompt: str,
        aspect_ratio: str,
        reference_image: bytes | None = None,
        reference_content_type: str | None = None,
    ) -> GeneratedImage:
        return GeneratedImage(data=self._PNG, content_type="image/png")
