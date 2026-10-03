"""Controlled local FFmpeg adapter for deterministic video operations.

This module never accepts a user-provided command.  The service supplies only
validated operation data and the adapter constructs an argument list itself.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


class VideoProcessorError(RuntimeError):
    """A controlled video-processing failure safe to return to the service."""


@dataclass(frozen=True)
class VideoMetadata:
    duration_seconds: float
    width: int
    height: int
    content_type: str
    has_audio: bool = False
    audio_codec: str | None = None
    video_codec: str | None = None
    container_format: str | None = None


class FFmpegVideoProcessor:
    """Run a small, explicit FFmpeg allowlist without invoking a shell."""

    def __init__(self, ffmpeg_binary: str, ffprobe_binary: str, timeout_seconds: int):
        self.ffmpeg_binary = ffmpeg_binary
        self.ffprobe_binary = ffprobe_binary
        self.timeout_seconds = timeout_seconds

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                args,
                check=True,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                shell=False,
            )
        except FileNotFoundError as error:
            raise VideoProcessorError("FFmpeg chưa được cài đặt hoặc không có trong PATH") from error
        except subprocess.TimeoutExpired as error:
            raise VideoProcessorError("Xử lý video vượt quá thời gian cho phép") from error
        except subprocess.CalledProcessError as error:
            message = (error.stderr or "FFmpeg không thể xử lý video").strip()
            raise VideoProcessorError(message[:2_000]) from error

    def probe(self, source: Path) -> VideoMetadata:
        result = self._run([
            self.ffprobe_binary, "-v", "error",
            "-show_entries", "format=duration,format_name:stream=codec_type,codec_name,width,height,channels",
            "-of", "json", str(source),
        ])
        try:
            payload = json.loads(result.stdout)
            streams = payload["streams"]
            video_stream = next(stream for stream in streams if stream.get("codec_type") == "video")
            audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
            duration = float(payload["format"]["duration"])
            width, height = int(video_stream["width"]), int(video_stream["height"])
            container = payload["format"].get("format_name")
        except (KeyError, ValueError, IndexError, TypeError, StopIteration, json.JSONDecodeError) as error:
            raise VideoProcessorError("Không thể đọc metadata video") from error
        if duration <= 0 or width <= 0 or height <= 0:
            raise VideoProcessorError("Metadata video không hợp lệ")
        return VideoMetadata(
            duration, width, height, "video/mp4", audio_stream is not None,
            audio_stream.get("codec_name") if audio_stream else None,
            video_stream.get("codec_name"), container,
        )

    def trim(self, source: Path, destination: Path, start: float, end: float) -> None:
        # Re-encode yields a precise cut and stable MP4 output. Parameters are
        # numbers validated by the service, never user-controlled FFmpeg syntax.
        self._run([
            self.ffmpeg_binary, "-y", "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
            "-i", str(source), "-map", "0:v:0", "-map", "0:a?",
            "-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart", str(destination),
        ])
    def aspect_crop(self, source: Path, destination: Path, width: int, height: int) -> None:
        video_filter = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height}"
        )
        self._run([
            self.ffmpeg_binary, "-y", "-i", str(source), "-map", "0:v:0", "-map", "0:a?",
            "-vf", video_filter, "-c:v", "libx264", "-c:a", "aac",
            "-movflags", "+faststart", str(destination),
        ])
    @staticmethod
    def _fontfile_filter() -> str:
        """Return a portable, explicit font file for FFmpeg drawtext."""
        configured = os.getenv("ADGEN_VIDEO_FONT_FILE", "").strip()
        candidates = [
            Path(configured) if configured else None,
            Path(os.getenv("WINDIR", "C:/Windows")) / "Fonts" / "arial.ttf",
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
        ]
        for candidate in candidates:
            if candidate and candidate.is_file():
                safe_path = str(candidate).replace("\\", "/").replace(":", "\\:")
                return f"fontfile='{safe_path}':"
        return ""
    def text_overlay(self, source: Path, destination: Path, text: str, start: float, end: float,
                     position: str, font_size: int, text_color: str, background: bool) -> None:
        text_path = destination.with_suffix(".txt")
        try:
            text_path.write_text(text, encoding="utf-8")
            safe_path = str(text_path).replace("\\", "/").replace(":", "\\:")
            y_position = {"top": "40", "center": "(h-text_h)/2", "bottom": "h-text_h-40"}[position]
            box = ":box=1:boxcolor=black@0.55:boxborderw=14" if background else ""
            draw = (
                f"drawtext={self._fontfile_filter()}textfile='{safe_path}':fontsize={font_size}:fontcolor={text_color}:"
                f"x=(w-text_w)/2:y={y_position}:enable='between(t,{start:.3f},{end:.3f})'{box}"
            )
            self._run([
                self.ffmpeg_binary, "-y", "-i", str(source), "-map", "0:v:0", "-map", "0:a?",
                "-vf", draw, "-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart", str(destination),
            ])
        finally:
            text_path.unlink(missing_ok=True)
    def subtitles(self, source: Path, destination: Path, entries: list[dict], position: str) -> None:
        subtitle_path = destination.with_suffix(".srt")
        lines = []
        for index, entry in enumerate(entries, 1):
            def timestamp(value: float) -> str:
                total_millis = int(round(value * 1000))
                hours, remainder = divmod(total_millis, 3_600_000)
                minutes, remainder = divmod(remainder, 60_000)
                seconds, millis = divmod(remainder, 1000)
                return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"
            lines.extend([str(index), f"{timestamp(entry['start'])} --> {timestamp(entry['end'])}", entry["text"], ""])
        try:
            subtitle_path.write_text("\n".join(lines), encoding="utf-8")
            safe_path = str(subtitle_path).replace("\\", "/").replace(":", "\\:")
            force_style = {"top": "Alignment=8", "center": "Alignment=5", "bottom": "Alignment=2"}[position]
            self._run([
                self.ffmpeg_binary, "-y", "-i", str(source), "-map", "0:v:0", "-map", "0:a?",
                "-vf", f"subtitles='{safe_path}':force_style='{force_style},FontName=Arial,FontSize=24'",
                "-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart", str(destination),
            ])
        finally:
            subtitle_path.unlink(missing_ok=True)
    def volume(self, source: Path, destination: Path, factor: float, mute: bool = False) -> None:
        audio_filter = "volume=0" if mute else f"volume={factor:.3f}"
        self._run([
            self.ffmpeg_binary, "-y", "-i", str(source), "-map", "0:v:0", "-map", "0:a?",
            "-c:v", "copy", "-af", audio_filter, "-c:a", "aac",
            "-movflags", "+faststart", str(destination),
        ])
    def merge(self, sources: list[Path], destination: Path) -> None:
        concat_path = destination.with_suffix(".concat.txt")
        lines = [f"file '{str(source).replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'" for source in sources]
        try:
            concat_path.write_text("\n".join(lines), encoding="utf-8")
            self._run([
                self.ffmpeg_binary, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_path),
                "-map", "0:v:0", "-map", "0:a?", "-c:v", "libx264", "-c:a", "aac",
                "-movflags", "+faststart", str(destination),
            ])
        finally:
            concat_path.unlink(missing_ok=True)
