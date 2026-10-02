import asyncio
import base64
import binascii
from io import BytesIO

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - exercised only before dependency install
    OpenAI = None

from app.core.config import settings
from app.services.media.providers.base import GeneratedImage, ImageGenerationProvider
from app.services.media.providers.gemini_provider import ImageProviderError


ASPECT_RATIO_TO_SIZE = {
    "1:1": "1024x1024",
    "4:5": "1024x1536",
    "9:16": "1024x1536",
    "3:2": "1536x1024",
    "16:9": "1536x1024",
}

SUPPORTED_OUTPUT_TYPES = {
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/webp": (b"RIFF",),
}


def _field(value, name):
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


def _status_code(error: Exception) -> int | None:
    values = [
        getattr(error, "status_code", None),
        getattr(error, "status", None),
        getattr(getattr(error, "response", None), "status_code", None),
        getattr(getattr(error, "response", None), "status", None),
    ]
    for value in values:
        if isinstance(value, int) and 400 <= value < 600:
            return value
        if isinstance(value, str) and value.isdigit():
            parsed = int(value)
            if 400 <= parsed < 600:
                return parsed
    return None


def _structured_codes(error: Exception) -> set[str]:
    values = {
        getattr(error, "code", None),
        getattr(error, "type", None),
        getattr(getattr(error, "response", None), "code", None),
    }
    body = getattr(error, "body", None)
    if isinstance(body, dict):
        nested = body.get("error")
        if isinstance(nested, dict):
            values.update({nested.get("code"), nested.get("type")})
    return {
        str(value).strip().lower()
        for value in values
        if value is not None
    }


def classify_openai_image_error(error: Exception) -> ImageProviderError:
    """Map OpenAI SDK errors without exposing raw messages or request data."""

    if isinstance(error, ImageProviderError):
        return error

    status_code = _status_code(error)
    error_type = type(error).__name__.lower()
    codes = _structured_codes(error)

    if (
        "timeout" in error_type
        or isinstance(error, TimeoutError)
        or status_code in {408, 504}
    ):
        return ImageProviderError("PROVIDER_TIMEOUT", provider_status=504)
    if (
        "ratelimit" in error_type
        or "rate_limit_exceeded" in codes
        or "insufficient_quota" in codes
    ):
        return ImageProviderError("RESOURCE_EXHAUSTED", provider_status=429)
    if "authentication" in error_type or status_code == 401:
        return ImageProviderError("UNAUTHENTICATED", provider_status=401)
    if "permission" in error_type or status_code == 403:
        return ImageProviderError("PERMISSION_DENIED", provider_status=403)
    if (
        "model" in " ".join(codes)
        and any(marker in " ".join(codes) for marker in ("not_found", "not found", "invalid"))
    ) or status_code in {404, 410}:
        return ImageProviderError("MODEL_NOT_FOUND", provider_status=404)
    if status_code == 400 or "badrequest" in error_type:
        return ImageProviderError("INVALID_ARGUMENT", provider_status=400)
    if status_code == 429:
        # A generic 429 is not enough evidence to label the failure as quota.
        return ImageProviderError("PROVIDER_ERROR", provider_status=429)
    return ImageProviderError("PROVIDER_ERROR", provider_status=status_code)


def _image_signature_matches(data: bytes, content_type: str) -> bool:
    if content_type == "image/webp":
        return len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    return data.startswith(SUPPORTED_OUTPUT_TYPES[content_type][0])


class OpenAIImageProvider(ImageGenerationProvider):
    """OpenAI Images API adapter for generation and single-image edits."""

    def __init__(self, client=None, model_name: str | None = None):
        if client is None and not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        if client is None and OpenAI is None:
            raise RuntimeError("The openai package is not installed")
        self.client = client or OpenAI(api_key=settings.OPENAI_API_KEY)
        self._model_name = model_name or settings.OPENAI_IMAGE_MODEL
        if not self._model_name:
            raise RuntimeError("OPENAI_IMAGE_MODEL is not configured")

    @property
    def provider_id(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model_name

    @staticmethod
    def size_for_aspect_ratio(aspect_ratio: str) -> str:
        return ASPECT_RATIO_TO_SIZE.get(aspect_ratio, "1024x1024")

    @staticmethod
    def _reference_upload(
        reference_image: bytes,
        reference_content_type: str | None,
    ) -> BytesIO:
        content_type = (reference_content_type or "image/png").lower()
        extension = {
            "image/png": "png",
            "image/jpeg": "jpg",
            "image/webp": "webp",
        }.get(content_type)
        if not extension:
            raise ImageProviderError("INVALID_ARGUMENT", provider_status=400)
        upload = BytesIO(reference_image)
        upload.name = f"reference.{extension}"
        return upload

    @staticmethod
    def _extract_image(response) -> GeneratedImage:
        response_data = _field(response, "data")
        if not response_data:
            raise ImageProviderError("IMAGE_OUTPUT_MISSING")
        item = response_data[0]
        encoded = _field(item, "b64_json")
        if not isinstance(encoded, str) or not encoded.strip():
            raise ImageProviderError("IMAGE_OUTPUT_MISSING")
        try:
            data = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError, TypeError) as error:
            raise ImageProviderError("PROVIDER_ERROR") from error
        if not data:
            raise ImageProviderError("IMAGE_OUTPUT_MISSING")

        content_type = (_field(item, "mime_type") or "image/png").lower()
        if content_type not in SUPPORTED_OUTPUT_TYPES:
            raise ImageProviderError("IMAGE_OUTPUT_MISSING")
        if not _image_signature_matches(data, content_type):
            raise ImageProviderError("PROVIDER_ERROR")
        return GeneratedImage(data=data, content_type=content_type)

    async def generate(
        self,
        *,
        prompt: str,
        aspect_ratio: str,
        reference_image: bytes | None = None,
        reference_content_type: str | None = None,
    ) -> GeneratedImage:
        request = {
            "model": self.model_name,
            "prompt": prompt,
            "size": self.size_for_aspect_ratio(aspect_ratio),
            "output_format": "png",
        }
        upload = None
        try:
            if reference_image is not None:
                upload = self._reference_upload(
                    reference_image, reference_content_type
                )
                response = await asyncio.to_thread(
                    self.client.images.edit,
                    image=[upload],
                    **request,
                )
            else:
                response = await asyncio.to_thread(
                    self.client.images.generate,
                    **request,
                )
        except ImageProviderError:
            raise
        except Exception as error:
            raise classify_openai_image_error(error) from error
        finally:
            if upload is not None:
                upload.close()
        return self._extract_image(response)
