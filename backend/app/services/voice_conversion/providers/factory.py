from app.core.config import settings
from app.services.voice_conversion.providers.base import BaseVoiceConversionProvider
from app.services.voice_conversion.providers.unavailable import (
    UnavailableVoiceConversionProvider,
)


def build_voice_conversion_provider() -> BaseVoiceConversionProvider:
    """Build only an explicitly implemented provider; fail closed otherwise."""

    if settings.VC_PROVIDER == "disabled":
        return UnavailableVoiceConversionProvider(
            "VC_PROVIDER is disabled"
        )

    return UnavailableVoiceConversionProvider(
        "No Voice Conversion adapter is enabled in this foundation checkpoint"
    )

