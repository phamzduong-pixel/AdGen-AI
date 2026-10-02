import asyncio
import unittest
from types import SimpleNamespace

from app.services.media.providers.gemini_video_provider import GeminiVideoProvider
from app.services.media.providers.video_generation import (
    GeneratedVideo,
    VideoGenerationInput,
    VideoGenerationProviderError,
)


VALID_MP4 = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00"


class FakeModels:
    def __init__(self, operation):
        self.operation = operation
        self.calls = []
        self.fail = None

    def generate_videos(self, **kwargs):
        if self.fail:
            raise self.fail
        self.calls.append(kwargs)
        return self.operation


class FakeOperations:
    def __init__(self, operation):
        self.operation = operation
        self.calls = []
        self.fail = None

    def get(self, operation):
        if self.fail:
            raise self.fail
        self.calls.append(operation)
        return self.operation


class FakeFiles:
    def __init__(self, output=VALID_MP4):
        self.output = output
        self.fail = None
        self.calls = []

    def download(self, **kwargs):
        if self.fail:
            raise self.fail
        self.calls.append(kwargs)
        return self.output


class FakeClient:
    def __init__(self, operation):
        self.models = FakeModels(operation)
        self.operations = FakeOperations(operation)
        self.files = FakeFiles()


class GeminiVideoProviderTest(unittest.TestCase):
    def test_submit_maps_veo_request_and_operation_id(self):
        operation = SimpleNamespace(name="operations/veo-1", done=False, error=None)
        client = FakeClient(operation)
        provider = GeminiVideoProvider(client=client, model_name="veo-test")

        result = asyncio.run(
            provider.submit(
                VideoGenerationInput(
                    prompt="A product commercial",
                    aspect_ratio="16:9",
                    duration_seconds=8,
                    references=((b"png", "image/png"),),
                )
            )
        )

        self.assertEqual(result.provider_job_id, "operations/veo-1")
        self.assertEqual(result.status, "processing")
        call = client.models.calls[0]
        self.assertEqual(call["model"], "veo-test")
        self.assertEqual(call["prompt"], "A product commercial")
        self.assertEqual(call["config"].aspect_ratio, "16:9")
        self.assertEqual(call["config"].duration_seconds, 8)
        self.assertEqual(len(call["config"].reference_images), 1)

    def test_status_maps_processing_completed_and_provider_failure(self):
        operation = SimpleNamespace(name="operations/veo-2", done=False, error=None)
        client = FakeClient(operation)
        provider = GeminiVideoProvider(client=client, model_name="veo-test")
        processing = asyncio.run(provider.get_status("operations/veo-2"))
        self.assertEqual(processing.status, "processing")

        operation.done = True
        operation.response = SimpleNamespace(
            generated_videos=[SimpleNamespace(video=SimpleNamespace(mime_type="video/mp4"))]
        )
        completed = asyncio.run(provider.get_status("operations/veo-2"))
        self.assertEqual(completed.status, "completed")

        operation.error = {"message": "quota exceeded"}
        failed = asyncio.run(provider.get_status("operations/veo-2"))
        self.assertEqual(failed.status, "failed")
        self.assertIn("quota", failed.error_message)

    def test_retrieve_downloads_completed_video(self):
        operation = SimpleNamespace(
            name="operations/veo-3",
            done=True,
            error=None,
            response=SimpleNamespace(
                generated_videos=[SimpleNamespace(video=SimpleNamespace(mime_type="video/mp4"))]
            ),
        )
        client = FakeClient(operation)
        provider = GeminiVideoProvider(client=client, model_name="veo-test")

        result = asyncio.run(provider.retrieve_result("operations/veo-3"))
        self.assertEqual(result, GeneratedVideo(VALID_MP4, "video/mp4"))
        self.assertEqual(client.files.calls[0]["file"].mime_type, "video/mp4")

    def test_rejects_unsupported_capability_and_malformed_result(self):
        operation = SimpleNamespace(name="operations/veo-4", done=False, error=None)
        client = FakeClient(operation)
        provider = GeminiVideoProvider(client=client, model_name="veo-test")

        with self.assertRaises(VideoGenerationProviderError):
            asyncio.run(
                provider.submit(
                    VideoGenerationInput(
                        prompt="unsupported",
                        aspect_ratio="1:1",
                        duration_seconds=8,
                    )
                )
            )

        operation.done = True
        operation.response = SimpleNamespace(generated_videos=[])
        with self.assertRaises(VideoGenerationProviderError):
            asyncio.run(provider.retrieve_result("operations/veo-4"))

    def test_maps_provider_timeout_to_provider_error(self):
        operation = SimpleNamespace(name="operations/veo-5", done=False, error=None)
        client = FakeClient(operation)
        client.models.fail = TimeoutError("timeout")
        provider = GeminiVideoProvider(client=client, model_name="veo-test")

        with self.assertRaises(VideoGenerationProviderError):
            asyncio.run(
                provider.submit(
                    VideoGenerationInput(
                        prompt="timeout",
                        aspect_ratio="9:16",
                        duration_seconds=8,
                    )
                )
            )

    def test_maps_http_429_resource_exhausted_without_exposing_secret(self):
        operation = SimpleNamespace(name="operations/veo-6", done=False, error=None)
        client = FakeClient(operation)
        error = RuntimeError("RESOURCE_EXHAUSTED; key=should-not-be-logged")
        error.status_code = 429
        client.models.fail = error
        provider = GeminiVideoProvider(client=client, model_name="veo-test")

        with self.assertRaises(VideoGenerationProviderError) as raised:
            asyncio.run(
                provider.submit(
                    VideoGenerationInput(
                        prompt="quota",
                        aspect_ratio="16:9",
                        duration_seconds=8,
                    )
                )
            )

        self.assertIn("429", str(raised.exception))
        self.assertNotIn("should-not-be-logged", str(raised.exception))

    def test_maps_download_failure_to_provider_error(self):
        operation = SimpleNamespace(
            name="operations/veo-7",
            done=True,
            error=None,
            response=SimpleNamespace(
                generated_videos=[SimpleNamespace(video=SimpleNamespace(mime_type="video/mp4"))]
            ),
        )
        client = FakeClient(operation)
        client.files.fail = RuntimeError("download failed")
        provider = GeminiVideoProvider(client=client, model_name="veo-test")

        with self.assertRaises(VideoGenerationProviderError) as raised:
            asyncio.run(provider.retrieve_result("operations/veo-7"))

        self.assertIn("tải", str(raised.exception))

if __name__ == "__main__":
    unittest.main()
