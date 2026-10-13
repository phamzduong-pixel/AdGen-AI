import asyncio
import base64
import re

from google import genai
from google.genai import types

from app.core.config import settings
from app.services.media.providers.base import GeneratedImage, ImageGenerationProvider


IMAGE_ERROR_CODES = {
    "QUOTA_EXCEEDED",
    "RESOURCE_EXHAUSTED",
    "INVALID_ARGUMENT",
    "MODEL_NOT_FOUND",
    "PERMISSION_DENIED",
    "UNAUTHENTICATED",
    "INVALID_API_KEY",
    "BILLING_REQUIRED",
    "RATE_LIMITED",
    "PROVIDER_TIMEOUT",
    "PROVIDER_ERROR",
    "IMAGE_OUTPUT_MISSING",
}


class ImageProviderError(RuntimeError):
    """Safe, stable classification for provider failures."""

    def __init__(
        self,
        code: str,
        *,
        provider_status: int | None = None,
        provider_message: str | None = None,
        request_id: str | None = None,
    ):
        if code not in IMAGE_ERROR_CODES:
            code = "PROVIDER_ERROR"
        self.code = code
        self.provider_status = provider_status
        self.provider_message = provider_message
        self.request_id = request_id
        super().__init__(code)


def _safe_provider_message(error: Exception) -> str:
    """Return a bounded provider message with credentials and auth data redacted."""
    message = str(getattr(error, "message", "") or error)
    message = re.sub(r"(?i)AIza[0-9a-z_-]{20,}", "[REDACTED]", message)
    message = re.sub(
        r"(?i)([\"']?authorization[\"']?\s*:\s*[\"']?)(?:bearer\s+)?[^\"'\s,;}]+[\"']?",
        r"\1=[REDACTED]",
        message,
    )
    message = re.sub(
        r"(?i)([\"']?(?:api[_ -]?key|bearer|token|secret|password)[\"']?\s*[:=]\s*[\"']?)[^\"'\s,;}]+[\"']?",
        r"\1[REDACTED]",
        message,
    )
    message = re.sub(r"(?i)([?&](?:key|token|access_token)=)[^&\s]+", r"\1[REDACTED]", message)
    return " ".join(message.split())[:500]


def _request_id(error: Exception) -> str | None:
    response = getattr(error, "response", None)
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    for name in ("x-goog-request-id", "x-request-id", "request-id", "x-correlation-id"):
        try:
            value = headers.get(name)
        except (AttributeError, TypeError):
            value = None
        if value:
            return re.sub(r"[^A-Za-z0-9._:-]", "", str(value))[:128] or None
    return None


def classify_image_provider_error(error: Exception) -> ImageProviderError:
    """Classify SDK/provider errors without exposing their raw contents."""

    if isinstance(error, ImageProviderError):
        return error

    response = getattr(error, "response", None)
    values = [
        getattr(error, "code", None),
        getattr(error, "status", None),
        getattr(error, "reason", None),
        getattr(error, "status_code", None),
        getattr(response, "code", None),
        getattr(response, "status", None),
        getattr(response, "status_code", None),
    ]
    structured = " ".join(str(value).lower() for value in values if value is not None)
    text = " ".join(str(value) for value in (error, getattr(error, "detail", ""))).lower()

    def http_status() -> int | None:
        for value in values:
            if isinstance(value, int) and 400 <= value < 600:
                return value
            if isinstance(value, str) and value.isdigit() and 400 <= int(value) < 600:
                return int(value)
        return None

    status_code = http_status()
    def classified(code: str, provider_status: int | None) -> ImageProviderError:
        return ImageProviderError(
            code,
            provider_status=provider_status,
            provider_message=_safe_provider_message(error),
            request_id=_request_id(error),
        )

    if "api_key_invalid" in structured or "invalid_api_key" in structured:
        return classified("INVALID_API_KEY", status_code or 401)
    if "rate_limited" in structured or "rate_limit_exceeded" in structured:
        return classified("RATE_LIMITED", status_code or 429)
    if "billing" in structured and any(marker in structured for marker in ("disabled", "not enabled", "required")):
        return classified("BILLING_REQUIRED", 403)
    if "billing" in text and any(marker in text for marker in ("disabled", "not enabled", "required", "account")):
        return classified("BILLING_REQUIRED", 403)
    if "api_key_invalid" in text or "invalid api key" in text or "api key not valid" in text:
        return classified("INVALID_API_KEY", status_code or 401)
    if "rate limit" in text or "rate_limit" in text or "requests per minute" in text:
        return classified("RATE_LIMITED", status_code or 429)
    if "quota" in text:
        return classified("QUOTA_EXCEEDED", status_code or 429)
    if "resource_exhausted" in text or "resource exhausted" in text:
        return classified("RESOURCE_EXHAUSTED", status_code or 429)
    if "resource_exhausted" in structured or "resource exhausted" in structured:
        return classified("RESOURCE_EXHAUSTED", 429)
    if "invalid_argument" in structured or "invalid argument" in structured:
        return classified("INVALID_ARGUMENT", 400)
    if "permission_denied" in structured or "permission denied" in structured:
        return classified("PERMISSION_DENIED", 403)
    if "unauthenticated" in structured:
        return classified("UNAUTHENTICATED", 401)
    if "model_not_found" in structured or "not_found" in structured:
        return classified("MODEL_NOT_FOUND", 404)
    if "invalid_argument" in text or "invalid argument" in text:
        return classified("INVALID_ARGUMENT", 400)
    if "permission_denied" in text or "permission denied" in text:
        return classified("PERMISSION_DENIED", 403)
    if "unauthenticated" in text or "authentication failed" in text or "invalid api key" in text:
        return classified("UNAUTHENTICATED", 401)
    if "model" in text and any(marker in text for marker in ("not found", "not supported", "does not exist", "unknown")):
        return classified("MODEL_NOT_FOUND", 404)
    if isinstance(error, TimeoutError) or "timeout" in text or "timed out" in text:
        return classified("PROVIDER_TIMEOUT", 504)

    if status_code == 429:
        # A bare HTTP 429 proves request limiting, not that quota was exhausted.
        return classified("PROVIDER_ERROR", 429)
    if status_code == 400:
        return classified("INVALID_ARGUMENT", 400)
    if status_code == 404:
        return classified("MODEL_NOT_FOUND", 404)
    if status_code == 403:
        return classified("PERMISSION_DENIED", 403)
    if status_code == 401:
        return classified("UNAUTHENTICATED", 401)
    return classified("PROVIDER_ERROR", status_code)


class GeminiImageProvider(ImageGenerationProvider):
    """Gemini native image generation/editing adapter."""

    def __init__(self, client=None, model_name: str | None = None):
        self.client = client or genai.Client(api_key=settings.GEMINI_API_KEY)
        self._model_name = model_name or settings.GEMINI_IMAGE_MODEL

    @property
    def provider_id(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate(
        self,
        *,
        prompt: str,
        aspect_ratio: str,
        reference_image: bytes | None = None,
        reference_content_type: str | None = None,
    ) -> GeneratedImage:
        contents: list = [types.Part.from_text(text=prompt)]
        if reference_image:
            contents.append(
                types.Part.from_bytes(
                    data=reference_image,
                    mime_type=reference_content_type or "image/png",
                )
            )

        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio=aspect_ratio),
                ),
            )
        except Exception as error:
            raise classify_image_provider_error(error) from error

        for part in response.parts or []:
            inline_data = getattr(part, "inline_data", None)
            data = getattr(inline_data, "data", None) if inline_data else None
            if not data:
                continue
            if isinstance(data, str):
                data = base64.b64decode(data)
            return GeneratedImage(
                data=data,
                content_type=getattr(inline_data, "mime_type", None)
                or "image/png",
            )

        raise ImageProviderError("IMAGE_OUTPUT_MISSING")
