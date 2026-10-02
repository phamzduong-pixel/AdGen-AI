import asyncio
import base64

from google import genai
from google.genai import types

from app.core.config import settings
from app.services.media.providers.base import GeneratedImage, ImageGenerationProvider


IMAGE_ERROR_CODES = {
    "RESOURCE_EXHAUSTED",
    "INVALID_ARGUMENT",
    "MODEL_NOT_FOUND",
    "PERMISSION_DENIED",
    "UNAUTHENTICATED",
    "PROVIDER_TIMEOUT",
    "PROVIDER_ERROR",
    "IMAGE_OUTPUT_MISSING",
}


class ImageProviderError(RuntimeError):
    """Safe, stable classification for provider failures."""

    def __init__(self, code: str, *, provider_status: int | None = None):
        if code not in IMAGE_ERROR_CODES:
            code = "PROVIDER_ERROR"
        self.code = code
        self.provider_status = provider_status
        super().__init__(code)


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
    if "resource_exhausted" in structured or "resource exhausted" in structured:
        return ImageProviderError("RESOURCE_EXHAUSTED", provider_status=429)
    if "invalid_argument" in structured or "invalid argument" in structured:
        return ImageProviderError("INVALID_ARGUMENT", provider_status=400)
    if "permission_denied" in structured or "permission denied" in structured:
        return ImageProviderError("PERMISSION_DENIED", provider_status=403)
    if "unauthenticated" in structured:
        return ImageProviderError("UNAUTHENTICATED", provider_status=401)
    if "model_not_found" in structured or "not_found" in structured:
        return ImageProviderError("MODEL_NOT_FOUND", provider_status=404)

    if "resource_exhausted" in text or "quota" in text or "rate limit" in text:
        return ImageProviderError("RESOURCE_EXHAUSTED", provider_status=429)
    if "invalid_argument" in text or "invalid argument" in text:
        return ImageProviderError("INVALID_ARGUMENT", provider_status=400)
    if "permission_denied" in text or "permission denied" in text:
        return ImageProviderError("PERMISSION_DENIED", provider_status=403)
    if "unauthenticated" in text or "authentication failed" in text or "invalid api key" in text:
        return ImageProviderError("UNAUTHENTICATED", provider_status=401)
    if "model" in text and any(marker in text for marker in ("not found", "not supported", "does not exist", "unknown")):
        return ImageProviderError("MODEL_NOT_FOUND", provider_status=404)
    if isinstance(error, TimeoutError) or "timeout" in text or "timed out" in text:
        return ImageProviderError("PROVIDER_TIMEOUT", provider_status=504)

    if status_code == 429:
        # A bare HTTP 429 proves request limiting, not that quota was exhausted.
        return ImageProviderError("PROVIDER_ERROR", provider_status=429)
    if status_code == 400:
        return ImageProviderError("INVALID_ARGUMENT", provider_status=400)
    if status_code == 404:
        return ImageProviderError("MODEL_NOT_FOUND", provider_status=404)
    if status_code == 403:
        return ImageProviderError("PERMISSION_DENIED", provider_status=403)
    if status_code == 401:
        return ImageProviderError("UNAUTHENTICATED", provider_status=401)
    return ImageProviderError("PROVIDER_ERROR", provider_status=status_code)


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
