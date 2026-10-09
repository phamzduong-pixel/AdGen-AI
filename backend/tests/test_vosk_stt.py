import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.core.config import settings
from app.services.stt.models import (
    STTAudioConversionError,
    STTAudioConversionNotConfiguredError,
    STTEmptyTranscriptError,
    STTProviderNotConfiguredError,
)
from app.services.stt.providers.factory import build_stt_provider
from app.services.stt.providers.unavailable import UnavailableSTTProvider
from app.services.stt.providers.vosk import VoskSTTProvider
from tests.audio_fixtures import make_wav_bytes


class FakeProcess:
    def __init__(self, command, *, return_code=0, write_wav=True):
        self.command = command
        self.return_code = return_code
        self.killed = False
        if write_wav:
            Path(command[-1]).write_bytes(make_wav_bytes(0.1, sample_rate=16000))

    def wait(self, timeout):
        return self.return_code

    def kill(self):
        self.killed = True


class FakeRecognizer:
    def __init__(self, _model, _sample_rate):
        self.accepted = False

    def AcceptWaveform(self, _data):
        self.accepted = True
        return True

    def Result(self):
        return json.dumps({"text": "xin chao"})

    def FinalResult(self):
        return json.dumps({"text": ""})


class EmptyRecognizer(FakeRecognizer):
    def Result(self):
        return json.dumps({"text": ""})


class VoskProviderTests(unittest.TestCase):
    def _provider(self, temporary_directory, recognizer=FakeRecognizer):
        model_path = Path(temporary_directory) / "model"
        model_path.mkdir()
        provider = VoskSTTProvider(model_path=model_path)
        return provider, recognizer

    def test_valid_audio_returns_transcript_and_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            provider, recognizer = self._provider(directory)
            source = Path(directory) / "source.m4a"
            source.write_bytes(b"encoded audio")

            with patch(
                "app.services.stt.providers.vosk._load_vosk",
                return_value=(lambda _path: object(), recognizer),
            ), patch(
                "app.services.stt.providers.vosk.subprocess.Popen",
                side_effect=lambda command, **_kwargs: FakeProcess(command),
            ):
                result = asyncio.run(
                    provider.transcribe(
                        source,
                        content_type="audio/mp4",
                        language="vi-VN",
                    )
                )

        self.assertEqual(result.transcript, "xin chao")
        self.assertEqual(result.language, "vi-VN")
        self.assertEqual(result.provider, "vosk")
        self.assertEqual(result.metadata["runtime"], "local")

    def test_empty_transcript_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            provider, recognizer = self._provider(directory, EmptyRecognizer)
            source = Path(directory) / "source.wav"
            source.write_bytes(b"encoded audio")

            with patch(
                "app.services.stt.providers.vosk._load_vosk",
                return_value=(lambda _path: object(), recognizer),
            ), patch(
                "app.services.stt.providers.vosk.subprocess.Popen",
                side_effect=lambda command, **_kwargs: FakeProcess(command),
            ):
                with self.assertRaises(STTEmptyTranscriptError):
                    asyncio.run(
                        provider.transcribe(
                            source,
                            content_type="audio/wav",
                            language="vi-VN",
                        )
                    )

    def test_conversion_failure_is_safe(self):
        with tempfile.TemporaryDirectory() as directory:
            provider, _ = self._provider(directory)
            source = Path(directory) / "source.mp3"
            source.write_bytes(b"encoded audio")

            with patch(
                "app.services.stt.providers.vosk._load_vosk",
                return_value=(lambda _path: object(), FakeRecognizer),
            ), patch(
                "app.services.stt.providers.vosk.subprocess.Popen",
                side_effect=lambda command, **_kwargs: FakeProcess(
                    command, return_code=1, write_wav=False
                ),
            ):
                with self.assertRaises(STTAudioConversionError):
                    asyncio.run(
                        provider.transcribe(
                            source,
                            content_type="audio/mpeg",
                            language="vi-VN",
                        )
                    )

    def test_missing_ffmpeg_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            provider, _ = self._provider(directory)
            source = Path(directory) / "source.wav"
            source.write_bytes(b"encoded audio")

            with patch(
                "app.services.stt.providers.vosk._load_vosk",
                return_value=(lambda _path: object(), FakeRecognizer),
            ), patch(
                "app.services.stt.providers.vosk.subprocess.Popen",
                side_effect=FileNotFoundError,
            ):
                with self.assertRaises(STTAudioConversionNotConfiguredError):
                    asyncio.run(
                        provider.transcribe(
                            source,
                            content_type="audio/wav",
                            language="vi-VN",
                        )
                    )

    def test_missing_model_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(STTProviderNotConfiguredError):
                VoskSTTProvider(model_path=Path(directory) / "missing-model")


class VoskFactoryTests(unittest.TestCase):
    def setUp(self):
        self.original_provider = settings.STT_PROVIDER
        self.original_model_path = settings.VOSK_MODEL_PATH

    def tearDown(self):
        settings.STT_PROVIDER = self.original_provider
        settings.VOSK_MODEL_PATH = self.original_model_path

    def test_selects_vosk_only_when_explicitly_configured(self):
        with tempfile.TemporaryDirectory() as directory:
            settings.STT_PROVIDER = "vosk"
            settings.VOSK_MODEL_PATH = directory
            sentinel = object()
            with patch(
                "app.services.stt.providers.factory._vosk_sdk_available",
                return_value=True,
            ), patch(
                "app.services.stt.providers.factory.VoskSTTProvider",
                return_value=sentinel,
            ):
                self.assertIs(build_stt_provider(), sentinel)

    def test_missing_model_returns_unavailable_provider(self):
        settings.STT_PROVIDER = "vosk"
        settings.VOSK_MODEL_PATH = "C:/missing/vosk-model"
        with patch(
            "app.services.stt.providers.factory._vosk_sdk_available",
            return_value=True,
        ):
            provider = build_stt_provider()

        self.assertIsInstance(provider, UnavailableSTTProvider)
        self.assertEqual(provider.provider_id, "unavailable")

    def test_default_provider_remains_fail_closed(self):
        settings.STT_PROVIDER = ""
        provider = build_stt_provider()
        self.assertIsInstance(provider, UnavailableSTTProvider)


if __name__ == "__main__":
    unittest.main()
