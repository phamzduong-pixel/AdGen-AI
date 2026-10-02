import asyncio
import base64
import unittest
from unittest.mock import patch

from app.schemas.media import ImageGenerateRequest
from app.core.config import settings
from app.services.media.providers.factory import build_image_generation_provider
from app.services.media.providers.gemini_provider import (
    GeminiImageProvider,
    ImageProviderError,
)
from app.services.media.providers.mock_provider import MockImageProvider
from app.services.media.providers.openai_provider import (
    OpenAIImageProvider,
    classify_openai_image_error,
)


class _InlineData:
    data = b"generated-image"
    mime_type = "image/png"


class _Part:
    inline_data = _InlineData()


class _Response:
    parts = [_Part()]


class _Models:
    def __init__(self):
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return _Response()


class _Client:
    def __init__(self):
        self.models = _Models()


VALID_PNG = bytes([137, 80, 78, 71, 13, 10, 26, 10]) + b"test"


class _OpenAIImages:
    def __init__(self, response=None):
        self.response = response
        self.generate_calls = []
        self.edit_calls = []

    def generate(self, **kwargs):
        self.generate_calls.append(kwargs)
        return self.response

    def edit(self, **kwargs):
        image = kwargs["image"][0]
        self.edit_calls.append(
            {
                **kwargs,
                "image_bytes": image.read(),
                "image_name": image.name,
            }
        )
        return self.response


class _OpenAIClient:
    def __init__(self, response):
        self.images = _OpenAIImages(response)


class _OpenAIResponse:
    def __init__(self, encoded, mime_type=None):
        item = {"b64_json": encoded}
        if mime_type is not None:
            item["mime_type"] = mime_type
        self.data = [item]


class MediaGenerationTest(unittest.TestCase):
    def test_request_rejects_two_reference_sources(self):
        with self.assertRaises(ValueError):
            ImageGenerateRequest(
                prompt="Tạo banner cho sản phẩm",
                reference_file_id=1,
                source_asset_id=2,
            )

    def test_request_trims_prompt_and_accepts_supported_ratio(self):
        request = ImageGenerateRequest(
            prompt="  Ảnh quảng cáo tối giản  ", aspect_ratio="9:16"
        )
        self.assertEqual(request.prompt, "Ảnh quảng cáo tối giản")
        self.assertEqual(request.aspect_ratio, "9:16")

    def test_mock_provider_is_available_offline(self):
        result = asyncio.run(
            MockImageProvider().generate(
                prompt="test", aspect_ratio="1:1"
            )
        )
        self.assertTrue(result.data.startswith(b"\x89PNG"))
        self.assertEqual(result.content_type, "image/png")

    def test_gemini_provider_rejects_response_without_image_parts(self):
        client = _Client()
        client.models.generate_content = lambda **kwargs: type(
            "EmptyResponse", (), {"parts": []}
        )()
        provider = GeminiImageProvider(client=client, model_name="image-test")
        with self.assertRaises(ImageProviderError) as raised:
            asyncio.run(
                provider.generate(prompt="test", aspect_ratio="1:1")
            )
        self.assertEqual(raised.exception.code, "IMAGE_OUTPUT_MISSING")
    def test_gemini_provider_requests_image_modality(self):
        client = _Client()
        provider = GeminiImageProvider(client=client, model_name="image-test")
        result = asyncio.run(
            provider.generate(
                prompt="Tạo ảnh sản phẩm",
                aspect_ratio="4:5",
                reference_image=b"source",
                reference_content_type="image/jpeg",
            )
        )

        self.assertEqual(result.data, b"generated-image")
        self.assertEqual(client.models.calls[0]["model"], "image-test")
        config = client.models.calls[0]["config"]
        self.assertEqual(config.response_modalities, ["IMAGE"])
        self.assertEqual(config.image_config.aspect_ratio, "4:5")

    def test_openai_provider_generates_png_and_maps_aspect_ratio(self):
        response = _OpenAIResponse(base64.b64encode(VALID_PNG).decode())
        client = _OpenAIClient(response)
        provider = OpenAIImageProvider(client=client, model_name="gpt-image-test")

        result = asyncio.run(
            provider.generate(prompt="product image", aspect_ratio="16:9")
        )

        self.assertEqual(result.data, VALID_PNG)
        self.assertEqual(result.content_type, "image/png")
        call = client.images.generate_calls[0]
        self.assertEqual(call["model"], "gpt-image-test")
        self.assertEqual(call["size"], "1536x1024")
        self.assertEqual(call["output_format"], "png")

    def test_openai_provider_edits_with_reference_image(self):
        response = _OpenAIResponse(base64.b64encode(VALID_PNG).decode())
        client = _OpenAIClient(response)
        provider = OpenAIImageProvider(client=client)
        source = bytes([137, 80, 78, 71, 13, 10, 26, 10]) + b"reference"

        result = asyncio.run(
            provider.generate(
                prompt="change the background",
                aspect_ratio="4:5",
                reference_image=source,
                reference_content_type="image/png",
            )
        )

        self.assertEqual(result.data, VALID_PNG)
        call = client.images.edit_calls[0]
        self.assertEqual(call["image_bytes"], source)
        self.assertEqual(call["image_name"], "reference.png")
        self.assertEqual(call["size"], "1024x1536")

    def test_openai_provider_rejects_missing_or_invalid_output(self):
        empty = OpenAIImageProvider(client=_OpenAIClient(_OpenAIResponse("")))
        with self.assertRaises(ImageProviderError) as empty_error:
            asyncio.run(empty.generate(prompt="test", aspect_ratio="1:1"))
        self.assertEqual(empty_error.exception.code, "IMAGE_OUTPUT_MISSING")

        invalid = OpenAIImageProvider(
            client=_OpenAIClient(_OpenAIResponse("not-base64"))
        )
        with self.assertRaises(ImageProviderError) as invalid_error:
            asyncio.run(invalid.generate(prompt="test", aspect_ratio="1:1"))
        self.assertEqual(invalid_error.exception.code, "PROVIDER_ERROR")

    def test_openai_provider_maps_provider_errors_without_raw_details(self):
        cases = [
            ("AuthenticationError", 401, "UNAUTHENTICATED"),
            ("PermissionDeniedError", 403, "PERMISSION_DENIED"),
            ("RateLimitError", 429, "RESOURCE_EXHAUSTED"),
            ("BadRequestError", 400, "INVALID_ARGUMENT"),
            ("NotFoundError", 404, "MODEL_NOT_FOUND"),
            ("APIError", 500, "PROVIDER_ERROR"),
            ("APITimeoutError", None, "PROVIDER_TIMEOUT"),
        ]
        for error_name, status_code, expected_code in cases:
            error_type = type(error_name, (RuntimeError,), {})
            error = error_type("api_key=secret internal response")
            if status_code is not None:
                error.status_code = status_code
            classified = classify_openai_image_error(error)
            self.assertEqual(classified.code, expected_code)
            self.assertNotIn("secret", str(classified))

        generic_429 = RuntimeError("429 internal")
        generic_429.status_code = 429
        self.assertEqual(
            classify_openai_image_error(generic_429).code,
            "PROVIDER_ERROR",
        )

    def test_openai_factory_selection_and_safe_configuration_errors(self):
        with patch.object(settings, "IMAGE_PROVIDER", "gemini"):
            with patch(
                "app.services.media.providers.gemini_provider.GeminiImageProvider"
            ) as gemini:
                gemini.return_value = object()
                self.assertIs(build_image_generation_provider(), gemini.return_value)

        with patch.object(settings, "IMAGE_PROVIDER", "openai"):
            with patch(
                "app.services.media.providers.openai_provider.OpenAIImageProvider"
            ) as openai:
                openai.return_value = object()
                self.assertIs(build_image_generation_provider(), openai.return_value)

        with patch.object(settings, "IMAGE_PROVIDER", "other"):
            with self.assertRaisesRegex(RuntimeError, "IMAGE_PROVIDER"):
                build_image_generation_provider()

        with patch.object(settings, "OPENAI_API_KEY", ""):
            with self.assertRaisesRegex(RuntimeError, "OPENAI_API_KEY"):
                OpenAIImageProvider()

    def test_openai_selection_does_not_require_gemini_key_in_validation(self):
        with patch.object(settings, "IMAGE_PROVIDER", "openai"), patch.object(
            settings, "OPENAI_API_KEY", "configured-openai-key"
        ), patch.object(settings, "GEMINI_API_KEY", ""), patch.object(
            settings, "SECRET_KEY", "x" * 40
        ):
            try:
                settings.validate()
            except RuntimeError as error:
                self.assertNotIn("GEMINI_API_KEY", str(error))
                self.assertNotIn("OPENAI_API_KEY", str(error))


if __name__ == "__main__":
    unittest.main()
