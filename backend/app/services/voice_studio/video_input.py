"""Fail-closed validation for Voice Studio video uploads.

This module validates a temporary upload only. It does not persist files,
create database records, extract audio, or call STT/Voice Conversion.
"""

from __future__ import annotations

import json
import math
import subprocess
import tempfile
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings


SUPPORTED_VIDEO_MIME_TYPES = {
    ".mp4": {"video/mp4"},
    ".mov": {"video/quicktime", "video/mp4"},
    ".webm": {"video/webm"},
}
PROBE_HEADER_BYTES = 4096
PROBE_OUTPUT_MAX_BYTES = 64 * 1024
PROBE_SIZE_BYTES = 5 * 1024 * 1024
PROBE_ANALYZE_DURATION_MICROSECONDS = 5_000_000
PROBE_READ_CHUNK_BYTES = 4096
TEMP_CHUNK_SIZE = 1024 * 1024


class VideoInputError(RuntimeError):
    code = "VIDEO_INVALID"
    http_status = 400
    public_message = "Video input is invalid."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.public_message)
        self.internal_message = message or self.public_message


class VideoEmptyError(VideoInputError):
    code = "VIDEO_EMPTY"
    public_message = "Video file is empty."


class VideoUnsupportedFormatError(VideoInputError):
    code = "VIDEO_UNSUPPORTED_FORMAT"
    http_status = 415
    public_message = "Video format is not supported."


class VideoMimeMismatchError(VideoInputError):
    code = "VIDEO_MIME_MISMATCH"
    public_message = "Video MIME type does not match the supported format."


class VideoSignatureInvalidError(VideoInputError):
    code = "VIDEO_SIGNATURE_INVALID"
    public_message = "Video container signature is invalid."


class VideoNoVideoStreamError(VideoInputError):
    code = "VIDEO_NO_VIDEO_STREAM"
    http_status = 422
    public_message = "Video stream was not found."


class VideoDurationInvalidError(VideoInputError):
    code = "VIDEO_DURATION_INVALID"
    http_status = 422
    public_message = "Video duration metadata is invalid."


class VideoDurationTooLongError(VideoInputError):
    code = "VIDEO_DURATION_TOO_LONG"
    http_status = 413
    public_message = "Video duration exceeds the configured limit."


class VideoTooLargeError(VideoInputError):
    code = "VIDEO_TOO_LARGE"
    http_status = 413
    public_message = "Video file exceeds the configured size limit."


class VideoNoAudioStreamError(VideoInputError):
    code = "VIDEO_NO_AUDIO_STREAM"
    http_status = 422
    public_message = "Audio stream was not found in the video."

class FFProbeNotConfiguredError(VideoInputError):
    code = "FFPROBE_NOT_CONFIGURED"
    http_status = 503
    public_message = "Video validation tool is not configured."


class FFProbeTimeoutError(VideoInputError):
    code = "FFPROBE_TIMEOUT"
    http_status = 504
    public_message = "Video validation timed out."


class FFProbeFailedError(VideoInputError):
    code = "FFPROBE_FAILED"
    http_status = 502
    public_message = "Video metadata could not be validated."


@dataclass(frozen=True)
class VideoInputMetadata:
    container_format: str
    video_codec: str | None
    duration_seconds: float
    width: int | None
    height: int | None
    has_audio: bool
    audio_codec: str | None


@dataclass(frozen=True)
class ValidatedVideoUpload:
    """Internal validated upload handle; never returned by an API."""

    path: Path
    extension: str
    content_type: str
    size_bytes: int
    metadata: VideoInputMetadata

def _normalize_content_type(content_type: str | None) -> str:
    return (content_type or "").lower().split(";", 1)[0].strip()


def _safe_filename(filename: str | None) -> tuple[str, str]:
    if not filename:
        raise VideoUnsupportedFormatError("Video filename is missing")
    safe_name = Path(filename.replace("\\", "/")).name.strip()
    extension = Path(safe_name).suffix.lower()
    if not safe_name or extension not in SUPPORTED_VIDEO_MIME_TYPES:
        raise VideoUnsupportedFormatError("Video extension is not supported")
    return safe_name, extension


def _signature_matches(extension: str, header: bytes) -> bool:
    if extension in {".mp4", ".mov"}:
        return len(header) >= 8 and header[4:8] == b"ftyp"
    if extension == ".webm":
        return header.startswith(b"\x1a\x45\xdf\xa3")
    return False


def _parse_optional_positive_int(value: object, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise FFProbeFailedError(f"FFprobe field {field_name} is invalid")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise FFProbeFailedError(f"FFprobe field {field_name} is invalid") from error
    if parsed <= 0:
        raise FFProbeFailedError(f"FFprobe field {field_name} is invalid")
    return parsed


def _parse_duration(payload: dict, video_stream: dict) -> float:
    for value in (payload.get("duration"), video_stream.get("duration")):
        if value is None or value == "N/A":
            continue
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(parsed) and parsed > 0:
            return parsed
    raise VideoDurationInvalidError("Video duration metadata is invalid")


class VoiceStudioVideoProbe:
    """Read bounded FFprobe metadata without decoding video frames."""

    def __init__(
        self,
        *,
        ffprobe_binary: str | None = None,
        timeout_seconds: float | None = None,
    ):
        self.ffprobe_binary = (
            settings.FFPROBE_BINARY if ffprobe_binary is None else ffprobe_binary
        )
        self.timeout_seconds = (
            settings.VIDEO_PROBE_TIMEOUT_SECONDS
            if timeout_seconds is None
            else timeout_seconds
        )

    def validate_path(
        self,
        source_path: Path,
        *,
        extension: str,
        content_type: str,
    ) -> VideoInputMetadata:
        try:
            with source_path.open("rb") as source_file:
                header = source_file.read(PROBE_HEADER_BYTES)
        except OSError as error:
            raise VideoInputError("Video file cannot be read") from error

        if not _signature_matches(extension, header):
            raise VideoSignatureInvalidError

        metadata = self._probe(source_path)
        self._validate_container(metadata.container_format, extension, content_type)
        if metadata.duration_seconds > settings.MAX_VIDEO_DURATION_SECONDS:
            raise VideoDurationTooLongError
        return metadata

    def _probe(self, source_path: Path) -> VideoInputMetadata:
        args = [
            self.ffprobe_binary,
            "-v",
            "error",
            "-hide_banner",
            "-probesize",
            str(PROBE_SIZE_BYTES),
            "-analyzeduration",
            str(PROBE_ANALYZE_DURATION_MICROSECONDS),
            "-show_entries",
            "format=duration,format_name:stream=codec_type,codec_name,width,height,channels,duration",
            "-of",
            "json",
            str(source_path),
        ]
        output = self._run_bounded(args)
        try:
            payload = json.loads(output.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise FFProbeFailedError("FFprobe returned invalid JSON") from error

        if not isinstance(payload, dict):
            raise FFProbeFailedError("FFprobe metadata is not an object")
        streams = payload.get("streams")
        if not isinstance(streams, list):
            raise FFProbeFailedError("FFprobe streams metadata is invalid")
        video_stream = next(
            (stream for stream in streams if isinstance(stream, dict) and stream.get("codec_type") == "video"),
            None,
        )
        if video_stream is None:
            raise VideoNoVideoStreamError

        format_payload = payload.get("format")
        if not isinstance(format_payload, dict):
            raise FFProbeFailedError("FFprobe format metadata is missing")
        container_format = format_payload.get("format_name")
        if not isinstance(container_format, str) or not container_format.strip():
            raise FFProbeFailedError("FFprobe container metadata is missing")

        audio_stream = next(
            (stream for stream in streams if isinstance(stream, dict) and stream.get("codec_type") == "audio"),
            None,
        )
        video_codec = video_stream.get("codec_name")
        audio_codec = audio_stream.get("codec_name") if audio_stream else None
        return VideoInputMetadata(
            container_format=container_format.strip(),
            video_codec=video_codec.strip() if isinstance(video_codec, str) else None,
            duration_seconds=_parse_duration(format_payload, video_stream),
            width=_parse_optional_positive_int(video_stream.get("width"), "width"),
            height=_parse_optional_positive_int(video_stream.get("height"), "height"),
            has_audio=audio_stream is not None,
            audio_codec=audio_codec.strip() if isinstance(audio_codec, str) else None,
        )

    def _run_bounded(self, args: list[str]) -> bytes:
        if not isinstance(self.ffprobe_binary, str) or not self.ffprobe_binary.strip():
            raise FFProbeNotConfiguredError
        try:
            process = subprocess.Popen(
                args,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                shell=False,
            )
        except (FileNotFoundError, OSError) as error:
            raise FFProbeNotConfiguredError from error

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
            raise FFProbeTimeoutError from error
        reader.join(timeout=1)
        if process.stdout is not None:
            process.stdout.close()

        if timed_out:
            raise FFProbeTimeoutError
        if output_too_large.is_set() or process.returncode != 0:
            raise FFProbeFailedError("FFprobe rejected the video")
        return b"".join(output_chunks)

    @staticmethod
    def _validate_container(
        container_format: str,
        extension: str,
        content_type: str,
    ) -> None:
        formats = {item.strip().lower() for item in container_format.split(",")}
        expected = {
            ".mp4": {"mp4", "mov", "m4v", "3gp", "3g2", "mj2"},
            ".mov": {"mp4", "mov", "m4v", "3gp", "3g2", "mj2"},
            ".webm": {"webm", "matroska"},
        }[extension]
        if not formats.intersection(expected):
            raise VideoInputError("Video container does not match the extension")
        if content_type not in SUPPORTED_VIDEO_MIME_TYPES[extension]:
            raise VideoMimeMismatchError

class VoiceStudioVideoInputService:
    """Validate one upload and optionally keep its validated temp path scoped."""

    def __init__(
        self,
        probe: VoiceStudioVideoProbe | None = None,
        *,
        temp_dir: Path | None = None,
    ):
        self.probe = probe or VoiceStudioVideoProbe()
        self.temp_dir = temp_dir

    @asynccontextmanager
    async def validated_upload(self, upload: UploadFile):
        temp_path: Path | None = None
        total_size = 0
        try:
            _, extension = _safe_filename(upload.filename)
            content_type = _normalize_content_type(upload.content_type)
            if content_type not in SUPPORTED_VIDEO_MIME_TYPES[extension]:
                raise VideoMimeMismatchError

            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix="adgen-voice-studio-video-",
                suffix=extension,
                dir=str(self.temp_dir) if self.temp_dir else None,
                delete=False,
            ) as temporary_file:
                temp_path = Path(temporary_file.name)
                while chunk := await upload.read(TEMP_CHUNK_SIZE):
                    total_size += len(chunk)
                    if total_size > settings.MAX_VIDEO_SIZE:
                        raise VideoTooLargeError
                    temporary_file.write(chunk)

            if total_size == 0:
                raise VideoEmptyError
            if temp_path is None:
                raise VideoInputError("Video temporary file was not created")

            metadata = self.probe.validate_path(
                temp_path,
                extension=extension,
                content_type=content_type,
            )
            yield ValidatedVideoUpload(
                path=temp_path,
                extension=extension,
                content_type=content_type,
                size_bytes=total_size,
                metadata=metadata,
            )
        finally:
            try:
                await upload.close()
            finally:
                if temp_path is not None:
                    temp_path.unlink(missing_ok=True)
    async def validate_upload(self, upload: UploadFile) -> VideoInputMetadata:
        async with self.validated_upload(upload) as validated:
            return validated.metadata
