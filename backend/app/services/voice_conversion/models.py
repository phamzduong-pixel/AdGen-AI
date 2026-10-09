from dataclasses import dataclass, field
from typing import Literal, TypeAlias


SafeMetadataValue: TypeAlias = str | int | float | bool | None
VoiceConversionOutputFormat: TypeAlias = Literal["mp3", "wav"]


@dataclass(frozen=True)
class VoiceConversionOptions:
    """Provider-neutral options; providers may support only a subset."""

    output_format: VoiceConversionOutputFormat = "mp3"
    remove_background_noise: bool = False


@dataclass(frozen=True)
class VoiceConversionResult:
    """Converted audio and safe provider metadata."""

    audio_bytes: bytes
    content_type: str
    file_extension: str
    provider_id: str
    duration_seconds: float | None = None
    metadata: dict[str, SafeMetadataValue] = field(default_factory=dict)


class VoiceConversionError(RuntimeError):
    """Base error with a stable public code and HTTP status."""

    code = "VC_CONVERSION_FAILED"
    http_status = 502
    public_message = "Voice conversion failed."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.public_message)
        self.internal_message = message or self.public_message


class VoiceConversionValidationError(VoiceConversionError):
    code = "VC_INVALID_AUDIO"
    http_status = 400
    public_message = "Audio input is invalid."


class VoiceConversionUnsupportedFormatError(VoiceConversionValidationError):
    code = "VC_UNSUPPORTED_AUDIO_FORMAT"
    http_status = 415
    public_message = "Audio format is not supported."


class VoiceConversionMimeMismatchError(VoiceConversionValidationError):
    code = "VC_AUDIO_MIME_MISMATCH"
    public_message = "Audio content type does not match the supported format."


class VoiceConversionEmptyAudioError(VoiceConversionValidationError):
    code = "VC_EMPTY_AUDIO"
    public_message = "Audio file is empty."


class VoiceConversionTooLargeError(VoiceConversionError):
    code = "VC_AUDIO_TOO_LARGE"
    http_status = 413
    public_message = "Audio file exceeds the configured size limit."


class VoiceConversionTooLongError(VoiceConversionError):
    code = "VC_AUDIO_TOO_LONG"
    http_status = 413
    public_message = "Audio duration exceeds the configured limit."




class VoiceConversionAudioInvalidError(VoiceConversionValidationError):
    code = "VC_AUDIO_INVALID"
    public_message = "Audio file is invalid."


class VoiceConversionUnsupportedContainerError(VoiceConversionValidationError):
    code = "VC_UNSUPPORTED_AUDIO_CONTAINER"
    http_status = 415
    public_message = "Audio container is not supported."


class VoiceConversionProbeMetadataError(VoiceConversionValidationError):
    code = "VC_AUDIO_PROBE_FAILED"
    http_status = 422
    public_message = "Audio metadata could not be validated."


class VoiceConversionProbeNotConfiguredError(VoiceConversionError):
    code = "VC_AUDIO_PROBE_NOT_CONFIGURED"
    http_status = 503
    public_message = "Audio validation tool is not configured."


class VoiceConversionAudioProbeTimeoutError(VoiceConversionError):
    code = "VC_AUDIO_PROBE_TIMEOUT"
    http_status = 504
    public_message = "Audio validation timed out."


class VoiceConversionAudioProbeOutputTooLargeError(VoiceConversionError):
    code = "VC_AUDIO_PROBE_OUTPUT_TOO_LARGE"
    http_status = 502
    public_message = "Audio validation returned too much metadata."


class VoiceConversionAudioTooLongError(VoiceConversionTooLongError):
    pass


class VoiceConversionInvalidLanguageError(VoiceConversionValidationError):
    code = "VC_INVALID_LANGUAGE"
    http_status = 422
    public_message = "Language code is invalid."


class VoiceConversionUnsupportedOutputFormatError(VoiceConversionValidationError):
    code = "VC_UNSUPPORTED_OUTPUT_FORMAT"
    http_status = 422
    public_message = "Output format is not supported."


class VoiceConversionTargetVoiceRequiredError(VoiceConversionValidationError):
    code = "VC_TARGET_VOICE_REQUIRED"
    http_status = 422
    public_message = "A target voice ID is required."


class VoiceConversionReferenceRequiredError(VoiceConversionValidationError):
    code = "VC_REFERENCE_REQUIRED"
    http_status = 422
    public_message = "A reference audio file or preset voice is required."


class VoiceConversionReferenceNotFoundError(VoiceConversionValidationError):
    code = "VC_REFERENCE_NOT_FOUND"
    http_status = 422
    public_message = "The selected reference voice is unavailable."

class VoiceConversionProviderNotConfiguredError(VoiceConversionError):
    code = "VC_PROVIDER_NOT_CONFIGURED"
    http_status = 503
    public_message = "Voice conversion provider is not configured."


class VoiceConversionProviderTimeoutError(VoiceConversionError):
    code = "VC_PROVIDER_TIMEOUT"
    http_status = 504
    public_message = "Voice conversion provider timed out."


class VoiceConversionProviderRateLimitedError(VoiceConversionError):
    code = "VC_PROVIDER_RATE_LIMITED"
    http_status = 429
    public_message = "Voice conversion provider is rate limited."


class VoiceConversionProviderQuotaExceededError(VoiceConversionError):
    code = "VC_PROVIDER_QUOTA_EXCEEDED"
    http_status = 503
    public_message = "Voice conversion provider quota is unavailable."


class VoiceConversionOutputInvalidError(VoiceConversionError):
    code = "VC_OUTPUT_INVALID"
    http_status = 502
    public_message = "Voice conversion provider returned invalid audio."


