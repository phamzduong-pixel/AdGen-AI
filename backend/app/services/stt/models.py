from dataclasses import dataclass, field
from typing import TypeAlias


SafeMetadataValue: TypeAlias = str | int | float | bool | None


@dataclass(frozen=True)
class TranscriptionResult:
    """Provider-neutral transcription output with only safe metadata."""

    transcript: str
    language: str | None
    provider: str
    metadata: dict[str, SafeMetadataValue] = field(default_factory=dict)


class STTError(RuntimeError):
    """Base error with a safe public code and HTTP status."""

    code = "STT_PROVIDER_ERROR"
    http_status = 502
    public_message = "Speech-to-text provider error."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.public_message)
        self.internal_message = message or self.public_message


class STTAudioValidationError(STTError):
    code = "STT_INVALID_AUDIO"
    http_status = 400
    public_message = "Audio input is invalid."


class STTUnsupportedFormatError(STTAudioValidationError):
    code = "STT_UNSUPPORTED_AUDIO_FORMAT"
    public_message = "Audio format is not supported."


class STTUnsupportedMimeTypeError(STTAudioValidationError):
    code = "STT_UNSUPPORTED_AUDIO_MIME"
    public_message = "Audio content type does not match a supported format."


class STTUnsupportedCodecError(STTAudioValidationError):
    code = "STT_UNSUPPORTED_AUDIO_CODEC"
    http_status = 415
    public_message = "Audio codec is not supported."


class STTEmptyAudioError(STTAudioValidationError):
    code = "STT_EMPTY_AUDIO"
    public_message = "Audio file is empty."


class STTAudioTooLargeError(STTError):
    code = "STT_AUDIO_TOO_LARGE"
    http_status = 413
    public_message = "Audio file exceeds the configured size limit."


class STTAudioTooLongError(STTError):
    code = "STT_AUDIO_TOO_LONG"
    http_status = 413
    public_message = "Audio duration exceeds the configured limit."


class STTAudioProbeNotConfiguredError(STTError):
    code = "STT_AUDIO_PROBE_NOT_CONFIGURED"
    http_status = 503
    public_message = "Audio validation tool is not configured."


class STTAudioProbeTimeoutError(STTError):
    code = "STT_AUDIO_PROBE_TIMEOUT"
    http_status = 504
    public_message = "Audio validation timed out."


class STTAudioConversionError(STTError):
    code = "STT_AUDIO_CONVERSION_FAILED"
    http_status = 422
    public_message = "Audio could not be converted for speech recognition."


class STTAudioConversionNotConfiguredError(STTError):
    code = "STT_AUDIO_CONVERSION_NOT_CONFIGURED"
    http_status = 503
    public_message = "Audio conversion tool is not configured."


class STTAudioConversionTimeoutError(STTError):
    code = "STT_AUDIO_CONVERSION_TIMEOUT"
    http_status = 504
    public_message = "Audio conversion timed out."

class STTInvalidLanguageError(STTAudioValidationError):
    code = "STT_INVALID_LANGUAGE"
    public_message = "Language code is invalid."


class STTProviderNotConfiguredError(STTError):
    code = "STT_PROVIDER_NOT_CONFIGURED"
    http_status = 503
    public_message = "Speech-to-text provider is not configured."


class STTProviderTimeoutError(STTError):
    code = "STT_PROVIDER_TIMEOUT"
    http_status = 504
    public_message = "Speech-to-text provider timed out."


class STTProviderAuthenticationError(STTError):
    code = "STT_PROVIDER_AUTHENTICATION_FAILED"
    http_status = 503
    public_message = "Speech-to-text provider authentication failed."


class STTProviderRateLimitedError(STTError):
    code = "STT_PROVIDER_RATE_LIMITED"
    http_status = 429
    public_message = "Speech-to-text provider is rate limited."


class STTProviderQuotaExceededError(STTError):
    code = "STT_PROVIDER_QUOTA_EXCEEDED"
    http_status = 503
    public_message = "Speech-to-text provider quota is unavailable."


class STTProviderInvalidResponseError(STTError):
    code = "STT_PROVIDER_INVALID_RESPONSE"
    http_status = 502
    public_message = "Speech-to-text provider returned an invalid response."


class STTEmptyTranscriptError(STTError):
    code = "STT_EMPTY_TRANSCRIPT"
    http_status = 502
    public_message = "Speech-to-text provider returned no transcript."
