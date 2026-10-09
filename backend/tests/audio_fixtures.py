"""Small reproducible audio fixtures for backend validation tests."""

from __future__ import annotations

import io
import wave


def make_wav_bytes(duration_seconds: float = 0.1, sample_rate: int = 8000) -> bytes:
    frame_count = max(1, int(sample_rate * duration_seconds))
    with io.BytesIO() as buffer:
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b"\x00\x00" * frame_count)
        return buffer.getvalue()
