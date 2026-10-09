"""Local Vosk Speech-to-Text provider."""

from __future__ import annotations

import asyncio
import os
import subprocess
import tempfile
import threading
import wave
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.stt.models import (
    STTAudioConversionError,
    STTAudioConversionNotConfiguredError,
    STTAudioConversionTimeoutError,
    STTEmptyTranscriptError,
    STTProviderNotConfiguredError,
    TranscriptionResult,
)
from app.services.stt.providers.base import BaseSTTProvider


VOSK_SAMPLE_RATE = 16_000
VOSK_SUPPORTED_AUDIO_CODECS = {
    ".flac": frozenset({"flac"}),
    ".m4a": frozenset({"aac"}),
    ".mp3": frozenset({"mp3"}),
    ".ogg": frozenset({"opus"}),
    ".wav": frozenset({"pcm_s16le", "pcm_mulaw", "pcm_alaw"}),
    ".webm": frozenset({"opus"}),
}


def _load_vosk() -> tuple[Any, Any]:
    try:
        from vosk import KaldiRecognizer, Model
    except (ImportError, ModuleNotFoundError) as error:
        raise STTProviderNotConfiguredError(
            "Vosk dependency is not installed"
        ) from error
    return Model, KaldiRecognizer


class VoskSTTProvider(BaseSTTProvider):
    """Transcribe local audio with a CPU Vosk model."""

    provider_id = "vosk"
    supported_audio_codecs = VOSK_SUPPORTED_AUDIO_CODECS

    def __init__(self, *, model_path: Path | str | None = None):
        configured_path = model_path or settings.VOSK_MODEL_PATH
        if not configured_path:
            raise STTProviderNotConfiguredError("Vosk model path is not configured")
        self.model_path = Path(os.path.expandvars(str(configured_path))).expanduser()
        if not self.model_path.is_dir():
            raise STTProviderNotConfiguredError(
                "Vosk model path does not point to a directory"
            )
        self._model: Any | None = None
        self._model_lock = threading.Lock()
        self._transcription_lock = threading.Lock()

    def _get_model(self) -> Any:
        if self._model is not None:
            return self._model
        with self._model_lock:
            if self._model is None:
                Model, _ = _load_vosk()
                try:
                    self._model = Model(str(self.model_path))
                except Exception as error:
                    raise STTProviderNotConfiguredError(
                        "Vosk model could not be loaded"
                    ) from error
        return self._model

    @staticmethod
    def _convert_to_wav(audio_path: Path, output_path: Path) -> None:
        command = [
            settings.FFMPEG_BINARY,
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-y",
            "-i",
            str(audio_path),
            "-ac",
            "1",
            "-ar",
            str(VOSK_SAMPLE_RATE),
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False,
            )
        except (FileNotFoundError, OSError) as error:
            raise STTAudioConversionNotConfiguredError from error

        try:
            return_code = process.wait(
                timeout=settings.STT_PROVIDER_TIMEOUT_SECONDS
            )
        except subprocess.TimeoutExpired as error:
            process.kill()
            process.wait()
            raise STTAudioConversionTimeoutError from error
        if return_code != 0 or not output_path.is_file() or output_path.stat().st_size == 0:
            raise STTAudioConversionError

    @staticmethod
    def _recognize(model: Any, wav_path: Path) -> str:
        _, KaldiRecognizer = _load_vosk()
        try:
            with wave.open(str(wav_path), "rb") as wav_file:
                if (
                    wav_file.getnchannels() != 1
                    or wav_file.getsampwidth() != 2
                    or wav_file.getframerate() != VOSK_SAMPLE_RATE
                ):
                    raise STTAudioConversionError
                recognizer = KaldiRecognizer(model, VOSK_SAMPLE_RATE)
                parts: list[str] = []
                while data := wav_file.readframes(4000):
                    if recognizer.AcceptWaveform(data):
                        import json

                        parts.append(json.loads(recognizer.Result()).get("text", ""))
                import json

                parts.append(json.loads(recognizer.FinalResult()).get("text", ""))
        except STTAudioConversionError:
            raise
        except (OSError, EOFError, wave.Error) as error:
            raise STTAudioConversionError from error

        transcript = " ".join(part.strip() for part in parts if part.strip())
        if not transcript:
            raise STTEmptyTranscriptError
        return transcript

    def _transcribe_sync(self, audio_path: Path, language: str | None) -> str:
        with self._transcription_lock:
            model = self._get_model()
            with tempfile.TemporaryDirectory(prefix="adgen-vosk-") as directory:
                wav_path = Path(directory) / "audio.wav"
                self._convert_to_wav(audio_path, wav_path)
                return self._recognize(model, wav_path)

    async def transcribe(
        self,
        audio_path: Path,
        *,
        content_type: str,
        language: str | None,
    ) -> TranscriptionResult:
        del content_type
        transcript = await asyncio.to_thread(
            self._transcribe_sync,
            audio_path,
            language,
        )
        return TranscriptionResult(
            transcript=transcript,
            language=language or settings.STT_DEFAULT_LANGUAGE or "vi-VN",
            provider=self.provider_id,
            metadata={"model": self.model_path.name, "runtime": "local"},
        )
