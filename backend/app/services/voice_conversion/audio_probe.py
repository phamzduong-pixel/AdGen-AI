"""Bounded FFprobe validation for Voice Conversion audio inputs."""

from __future__ import annotations

import json
import math
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.services.voice_conversion.models import (
    VoiceConversionAudioInvalidError,
    VoiceConversionAudioProbeOutputTooLargeError,
    VoiceConversionAudioProbeTimeoutError,
    VoiceConversionAudioTooLongError,
    VoiceConversionProbeMetadataError,
    VoiceConversionProbeNotConfiguredError,
    VoiceConversionUnsupportedContainerError,
)


PROBE_HEADER_BYTES = 4096
PROBE_OUTPUT_MAX_BYTES = 64 * 1024
PROBE_SIZE_BYTES = 5 * 1024 * 1024
PROBE_ANALYZE_DURATION_MICROSECONDS = 5_000_000
PROBE_READ_CHUNK_BYTES = 4096


@dataclass(frozen=True)
class AudioProbeResult:
    container_format: str
    codec_name: str
    duration_seconds: float
    sample_rate: int | None = None
    channels: int | None = None


def _is_mp3_frame_header(header: bytes) -> bool:
    if len(header) < 4 or header[0] != 0xFF or (header[1] & 0xE0) != 0xE0:
        return False
    version = (header[1] >> 3) & 0x03
    layer = (header[1] >> 1) & 0x03
    bitrate_index = (header[2] >> 4) & 0x0F
    sample_rate_index = (header[2] >> 2) & 0x03
    return (
        version != 0x01
        and layer != 0
        and bitrate_index not in {0, 0x0F}
        and sample_rate_index != 0x03
    )


def _has_mp3_signature(header: bytes) -> bool:
    if header.startswith(b"ID3"):
        return True
    return any(_is_mp3_frame_header(header[index:]) for index in range(len(header) - 3))


def _signature_matches(extension: str, header: bytes) -> bool:
    if extension == ".wav":
        return (
            len(header) >= 12
            and header[:4] in {b"RIFF", b"RF64", b"RIFX"}
            and header[8:12] == b"WAVE"
        )
    if extension == ".flac":
        return header.startswith(b"fLaC")
    if extension == ".mp3":
        return _has_mp3_signature(header)
    if extension == ".m4a":
        return len(header) >= 12 and header[4:8] == b"ftyp"
    if extension in {".ogg", ".oga"}:
        return header.startswith(b"OggS")
    if extension == ".webm":
        return header.startswith(b"\x1a\x45\xdf\xa3")
    return False


def _parse_positive_finite(value: object, field_name: str) -> float:
    if isinstance(value, bool) or value is None:
        raise VoiceConversionProbeMetadataError(
            f"FFprobe metadata field {field_name} is missing"
        )
    try:
        parsed = float(value)
    except (TypeError, ValueError) as error:
        raise VoiceConversionProbeMetadataError(
            f"FFprobe metadata field {field_name} is invalid"
        ) from error
    if not math.isfinite(parsed) or parsed <= 0:
        raise VoiceConversionProbeMetadataError(
            f"FFprobe metadata field {field_name} is invalid"
        )
    return parsed


def _parse_optional_positive_int(value: object, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise VoiceConversionProbeMetadataError(
            f"FFprobe metadata field {field_name} is invalid"
        )
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise VoiceConversionProbeMetadataError(
            f"FFprobe metadata field {field_name} is invalid"
        ) from error
    if parsed <= 0:
        raise VoiceConversionProbeMetadataError(
            f"FFprobe metadata field {field_name} is invalid"
        )
    return parsed


class VoiceConversionAudioProbe:
    """Validate audio identity and read bounded metadata with FFprobe."""

    def __init__(
        self,
        *,
        ffprobe_binary: str | None = None,
        timeout_seconds: float | None = None,
    ):
        self.ffprobe_binary = (
            settings.FFPROBE_BINARY
            if ffprobe_binary is None
            else ffprobe_binary
        )
        self.timeout_seconds = (
            settings.VC_AUDIO_PROBE_TIMEOUT_SECONDS
            if timeout_seconds is None
            else timeout_seconds
        )

    def validate(
        self,
        source_path: Path,
        *,
        extension: str,
        content_type: str,
        max_duration_seconds: float | None = None,
    ) -> AudioProbeResult:
        try:
            with source_path.open("rb") as source_file:
                header = source_file.read(PROBE_HEADER_BYTES)
        except OSError as error:
            raise VoiceConversionAudioInvalidError("Audio file cannot be read") from error

        if not _signature_matches(extension, header):
            raise VoiceConversionAudioInvalidError(
                "Audio signature does not match the extension"
            )

        result = self._probe(source_path)
        self._validate_container(result.container_format, extension, content_type)
        duration_limit = (
            settings.VC_AUDIO_MAX_DURATION_SECONDS
            if max_duration_seconds is None
            else max_duration_seconds
        )
        if result.duration_seconds > duration_limit:
            raise VoiceConversionAudioTooLongError(
                "Audio duration exceeds the configured limit"
            )
        return result

    def _probe(self, source_path: Path) -> AudioProbeResult:
        args = [
            self.ffprobe_binary,
            "-v",
            "error",
            "-hide_banner",
            "-probesize",
            str(PROBE_SIZE_BYTES),
            "-analyzeduration",
            str(PROBE_ANALYZE_DURATION_MICROSECONDS),
            "-select_streams",
            "a:0",
            "-show_entries",
            "format=format_name,duration:stream=codec_type,codec_name,duration,sample_rate,channels",
            "-of",
            "json",
            str(source_path),
        ]
        output = self._run_bounded(args)
        try:
            payload = json.loads(output.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise VoiceConversionProbeMetadataError(
                "FFprobe returned invalid JSON metadata"
            ) from error

        if not isinstance(payload, dict):
            raise VoiceConversionProbeMetadataError("FFprobe metadata is not an object")
        streams = payload.get("streams")
        if not isinstance(streams, list) or not streams or not isinstance(streams[0], dict):
            raise VoiceConversionUnsupportedContainerError(
                "Audio stream was not found"
            )
        stream = streams[0]
        if stream.get("codec_type") != "audio":
            raise VoiceConversionUnsupportedContainerError(
                "Audio stream was not found"
            )
        codec_name = stream.get("codec_name")
        if not isinstance(codec_name, str) or not codec_name.strip():
            raise VoiceConversionProbeMetadataError("Audio codec metadata is missing")

        format_payload = payload.get("format")
        if not isinstance(format_payload, dict):
            raise VoiceConversionProbeMetadataError("Container metadata is missing")
        container_format = format_payload.get("format_name")
        if not isinstance(container_format, str) or not container_format.strip():
            raise VoiceConversionProbeMetadataError("Container format metadata is missing")

        duration_seconds: float | None = None
        for duration_value in (
            stream.get("duration"),
            format_payload.get("duration"),
        ):
            if duration_value is None:
                continue
            try:
                duration_seconds = _parse_positive_finite(duration_value, "duration")
                break
            except VoiceConversionProbeMetadataError:
                continue
        if duration_seconds is None:
            raise VoiceConversionProbeMetadataError("Audio duration metadata is invalid")
        return AudioProbeResult(
            container_format=container_format,
            codec_name=codec_name.strip(),
            duration_seconds=duration_seconds,
            sample_rate=_parse_optional_positive_int(stream.get("sample_rate"), "sample_rate"),
            channels=_parse_optional_positive_int(stream.get("channels"), "channels"),
        )

    def _run_bounded(self, args: list[str]) -> bytes:
        if not self.ffprobe_binary.strip():
            raise VoiceConversionProbeNotConfiguredError(
                "FFPROBE_BINARY is empty"
            )
        try:
            process = subprocess.Popen(
                args,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                shell=False,
            )
        except FileNotFoundError as error:
            raise VoiceConversionProbeNotConfiguredError(
                "FFprobe executable was not found"
            ) from error
        except OSError as error:
            raise VoiceConversionProbeNotConfiguredError(
                "FFprobe could not be started"
            ) from error

        output_chunks: list[bytes] = []
        output_size = 0
        output_too_large = threading.Event()

        def drain_stdout() -> None:
            nonlocal output_size
            if process.stdout is None:
                return
            while True:
                chunk = process.stdout.read(PROBE_READ_CHUNK_BYTES)
                if not chunk:
                    return
                output_size += len(chunk)
                if output_size > PROBE_OUTPUT_MAX_BYTES:
                    output_too_large.set()
                    continue
                output_chunks.append(chunk)

        reader = threading.Thread(target=drain_stdout, daemon=True)
        reader.start()
        deadline = time.monotonic() + self.timeout_seconds
        timed_out = False
        while process.poll() is None:
            if output_too_large.is_set():
                process.kill()
                break
            if time.monotonic() >= deadline:
                timed_out = True
                process.kill()
                break
            time.sleep(0.01)

        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired as error:
            process.kill()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
            reader.join(timeout=1)
            if process.stdout is not None:
                process.stdout.close()
            raise VoiceConversionAudioProbeTimeoutError from error
        reader.join(timeout=1)

        if process.stdout is not None:
            process.stdout.close()

        if timed_out:
            raise VoiceConversionAudioProbeTimeoutError
        if output_too_large.is_set():
            raise VoiceConversionAudioProbeOutputTooLargeError
        if process.returncode != 0:
            raise VoiceConversionAudioInvalidError("FFprobe rejected the audio file")
        return b"".join(output_chunks)

    @staticmethod
    def _validate_container(
        container_format: str,
        extension: str,
        content_type: str,
    ) -> None:
        formats = {value.strip().lower() for value in container_format.split(",")}
        expected_formats = {
            ".wav": {"wav"},
            ".flac": {"flac"},
            ".mp3": {"mp3"},
            ".m4a": {"mov", "mp4", "m4a", "3gp", "3g2", "mj2"},
            ".ogg": {"ogg"},
            ".oga": {"ogg"},
            ".webm": {"webm"},
        }.get(extension, set())
        if not formats.intersection(expected_formats):
            raise VoiceConversionUnsupportedContainerError(
                f"Audio container does not match {extension}"
            )
        if not content_type.startswith("audio/") and content_type != "application/ogg":
            raise VoiceConversionAudioInvalidError(
                "Audio content type is not an audio MIME type"
            )


def probe_audio_file(
    source_path: Path,
    *,
    extension: str,
    content_type: str,
    max_duration_seconds: float | None = None,
) -> AudioProbeResult:
    return VoiceConversionAudioProbe().validate(
        source_path,
        extension=extension,
        content_type=content_type,
        max_duration_seconds=max_duration_seconds,
    )
