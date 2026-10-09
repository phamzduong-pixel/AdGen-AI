"""Small process entry point executed by the isolated VieNeu environment."""

from __future__ import annotations

import contextlib
import json
import sys
import wave
from pathlib import Path


def main() -> int:
    raw = sys.stdin.read(64 * 1024 + 1)
    if len(raw.encode("utf-8")) > 64 * 1024:
        print(json.dumps({"ok": False}), flush=True)
        return 2
    try:
        payload = json.loads(raw)
        text = str(payload["text"]).strip()
        reference_audio_value = payload.get("reference_audio")
        reference_audio = Path(reference_audio_value) if reference_audio_value else None
        voice = str(payload.get("voice") or "").strip()
        output_audio = Path(payload["output_audio"])
        model_snapshot = Path(payload["model_snapshot"])
        codec_snapshot = Path(payload["codec_snapshot"])
        if not text or (reference_audio is None and not voice) or (reference_audio is not None and not reference_audio.is_file()):
            raise ValueError("invalid input")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        print(json.dumps({"ok": False}), flush=True)
        return 2

    try:
        from vieneu import Vieneu

        # Keep all SDK/logging output away from the machine-readable response.
        with contextlib.redirect_stdout(sys.stderr):
            tts = Vieneu(
                backbone_repo=str(model_snapshot),
                backend="onnx",
                onnx_dir=str(model_snapshot / "onnx_update"),
                codec_dir=str(codec_snapshot),
                precision="fp32",
                threads=1,
            )
            infer_options = {
                "apply_watermark": False,
                "max_chars": 256,
                "show_progress": False,
            }
            if voice:
                audio = tts.infer(text, voice=voice, **infer_options)
            else:
                audio = tts.infer(text, ref_audio=str(reference_audio), denoise=True, **infer_options)
            if getattr(audio, "size", 0) <= 0:
                raise ValueError("empty audio")
            tts.save(audio, str(output_audio))
            with wave.open(str(output_audio), "rb") as audio_file:
                if audio_file.getnframes() <= 0 or audio_file.getframerate() <= 0:
                    raise ValueError("invalid output")
    except Exception:
        print(json.dumps({"ok": False}), flush=True)
        return 1

    print(json.dumps({"ok": True}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
