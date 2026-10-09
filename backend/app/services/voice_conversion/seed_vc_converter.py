"""Bounded CPU-only subprocess adapter for the isolated Seed-VC runtime."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from app.core.config import settings
from app.services.voice_conversion.models import (
    VoiceConversionOutputInvalidError,
    VoiceConversionProviderNotConfiguredError,
    VoiceConversionProviderTimeoutError,
)


class SeedVCConverter:
    """Run Seed-VC out-of-process so its ML dependencies never enter the API env."""

    def __init__(self, *, python_path: Path | None = None, project_dir: Path | None = None) -> None:
        self.python_path = python_path or Path(settings.SEED_VC_PYTHON)
        self.project_dir = project_dir or Path(settings.SEED_VC_DIR)

    def convert(self, source_audio_path: str, ref_audio_path: str, output_path: str) -> str:
        source_path = Path(source_audio_path)
        reference_path = Path(ref_audio_path)
        final_path = Path(output_path)
        inference_path = self.project_dir / "inference.py"
        if not self.python_path.is_file() or not inference_path.is_file():
            raise VoiceConversionProviderNotConfiguredError("Seed-VC runtime is not installed")
        if not source_path.is_file() or not reference_path.is_file():
            raise VoiceConversionOutputInvalidError("Seed-VC input file is unavailable")

        final_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="adgen-seed-vc-") as output_dir:
            args = [
                str(self.python_path), str(inference_path),
                "--source", str(source_path), "--target", str(reference_path),
                "--output", output_dir,
                "--diffusion-steps", str(settings.SEED_VC_DIFFUSION_STEPS),
                "--length-adjust", "1.0", "--fp16", "false",
            ]
            environment = {**os.environ, "CUDA_VISIBLE_DEVICES": "-1", "PYTORCH_ENABLE_MPS_FALLBACK": "0"}
            try:
                completed = subprocess.run(
                    args, cwd=str(self.project_dir), stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, shell=False,
                    env=environment, timeout=settings.VC_PROVIDER_TIMEOUT_SECONDS,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False,
                )
            except FileNotFoundError as error:
                raise VoiceConversionProviderNotConfiguredError("Seed-VC runtime cannot be started") from error
            except subprocess.TimeoutExpired as error:
                raise VoiceConversionProviderTimeoutError("Seed-VC timed out") from error
            if completed.returncode != 0:
                raise VoiceConversionOutputInvalidError("Seed-VC inference failed")
            candidates = sorted(Path(output_dir).glob("*.wav"), key=lambda item: item.stat().st_mtime)
            if not candidates or candidates[-1].stat().st_size <= 0:
                raise VoiceConversionOutputInvalidError("Seed-VC returned no audio")
            final_path.write_bytes(candidates[-1].read_bytes())
        return str(final_path)
