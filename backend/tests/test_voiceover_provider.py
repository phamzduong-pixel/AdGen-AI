import asyncio
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.schemas.voiceover import VoiceoverGenerateRequest
from app.services.voiceover.providers.edge_tts_provider import EdgeTTSProvider
from app.services.voiceover.providers.mock_provider import MockTTSProvider
from app.services.voiceover.voiceover_service import VoiceoverService


def fake_edge_tts(communicate_class):
    module = types.ModuleType("edge_tts")
    module.Communicate = communicate_class
    return module


class StreamingCommunicate:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def stream(self):
        yield {"type": "audio", "data": b"audio-part-1"}
        yield {"type": "WordBoundary", "data": b"ignored"}
        yield {"type": "audio", "data": b"audio-part-2"}


class SavingCommunicate:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def save(self, path):
        Path(path).write_bytes(b"saved-audio")


class FailingCommunicate:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def save(self, path):
        Path(path).write_bytes(b"partial")
        raise OSError("synthetic provider failure")


class EdgeTTSProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_streaming_success_returns_audio_parts_only(self):
        provider = EdgeTTSProvider()
        with patch.dict(
            "sys.modules",
            {"edge_tts": fake_edge_tts(StreamingCommunicate)},
        ):
            result = await provider.synthesize(
                "hello", voice_id="vi-VN-HoaiMyNeural", speed=1.1, pitch=-2
            )

        self.assertEqual(result, b"audio-part-1audio-part-2")

    async def test_file_output_returns_saved_bytes(self):
        provider = EdgeTTSProvider()
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "voice.mp3"
            with patch.dict(
                "sys.modules",
                {"edge_tts": fake_edge_tts(SavingCommunicate)},
            ):
                result = await provider.synthesize("hello", output_file_path=str(output_path))

            self.assertEqual(result, b"saved-audio")
            self.assertEqual(output_path.read_bytes(), b"saved-audio")

    async def test_provider_error_is_propagated(self):
        provider = EdgeTTSProvider()
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "voice.mp3"
            with patch.dict(
                "sys.modules",
                {"edge_tts": fake_edge_tts(FailingCommunicate)},
            ):
                with self.assertRaises(OSError):
                    await provider.synthesize("hello", output_file_path=str(output_path))

    async def test_empty_stream_returns_empty_bytes(self):
        class EmptyCommunicate:
            def __init__(self, **kwargs):
                pass

            async def stream(self):
                if False:
                    yield {"type": "audio", "data": b""}

        provider = EdgeTTSProvider()
        with patch.dict(
            "sys.modules",
            {"edge_tts": fake_edge_tts(EmptyCommunicate)},
        ):
            result = await provider.synthesize("hello")

        self.assertEqual(result, b"")


class VoiceoverServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_mock_provider_generates_persisted_audio(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            settings, "UPLOAD_DIR", directory
        ):
            service = VoiceoverService(provider=MockTTSProvider())
            response = await service.generate_voiceover(
                VoiceoverGenerateRequest(text="A short test script")
            )

            output_path = Path(directory) / "audio" / f"{response.audio_id}.mp3"
            self.assertTrue(output_path.is_file())
            self.assertGreater(response.file_size_bytes, 2000)

    async def test_failed_provider_output_is_removed(self):
        provider = EdgeTTSProvider()
        with tempfile.TemporaryDirectory() as directory, patch.object(
            settings, "UPLOAD_DIR", directory
        ), patch.object(asyncio, "sleep", new=AsyncMock()):
            with patch.dict(
                "sys.modules",
                {"edge_tts": fake_edge_tts(FailingCommunicate)},
            ):
                service = VoiceoverService(provider=provider)
                with self.assertRaises(RuntimeError):
                    await service.generate_voiceover(
                        VoiceoverGenerateRequest(text="A short test script")
                    )

            self.assertEqual(list((Path(directory) / "audio").glob("*.mp3")), [])

    async def test_short_output_is_rejected_and_removed(self):
        class ShortProvider(MockTTSProvider):
            async def synthesize(self, *args, output_file_path=None, **kwargs):
                data = b"short"
                if output_file_path:
                    Path(output_file_path).write_bytes(data)
                return data

        with tempfile.TemporaryDirectory() as directory, patch.object(
            settings, "UPLOAD_DIR", directory
        ), patch.object(asyncio, "sleep", new=AsyncMock()):
            service = VoiceoverService(provider=ShortProvider())
            with self.assertRaises(RuntimeError):
                await service.generate_voiceover(
                    VoiceoverGenerateRequest(text="A short test script")
                )

            self.assertEqual(list((Path(directory) / "audio").glob("*.mp3")), [])


if __name__ == "__main__":
    unittest.main()
