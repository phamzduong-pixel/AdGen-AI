from app.core.config import settings
from app.services.media.providers.gemini_video_provider import GeminiVideoProvider
from app.services.media.providers.video_generation import (
    UnavailableVideoGenerationProvider,
    VideoGenerationProvider,
    VideoGenerationProviderUnavailable,
)


def build_image_generation_provider():
    """Build exactly the configured image provider; never fall back silently."""

    if settings.IMAGE_PROVIDER == "gemini":
        from app.services.media.providers.gemini_provider import GeminiImageProvider

        return GeminiImageProvider()
    if settings.IMAGE_PROVIDER == "openai":
        from app.services.media.providers.openai_provider import OpenAIImageProvider

        return OpenAIImageProvider()
    raise RuntimeError("IMAGE_PROVIDER must be 'gemini' or 'openai'")


def build_video_generation_provider() -> VideoGenerationProvider:
    if settings.VIDEO_GENERATION_PROVIDER == "gemini":
        try:
            return GeminiVideoProvider()
        except VideoGenerationProviderUnavailable:
            return UnavailableVideoGenerationProvider()
    return UnavailableVideoGenerationProvider()
