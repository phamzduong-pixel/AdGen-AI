"""Safe resolution of Seed-VC target reference audio."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.services.voice_conversion.models import (
    VoiceConversionReferenceNotFoundError,
    VoiceConversionReferenceRequiredError,
)


@dataclass(frozen=True)
class PresetReferenceVoice:
    id: str
    filename: str
    name: str


class ReferenceAudioManager:
    """Resolve only bundled preset samples; custom uploads stay request-scoped."""

    PRESETS = {
        "ngoc-huyen": PresetReferenceVoice(
            id="ngoc-huyen",
            filename="ngoc_huyen_ref.wav",
            name="HN - Ngọc Huyền (Giải trí)",
        ),
        "manh-dung": PresetReferenceVoice(
            id="manh-dung",
            filename="manh_dung_ref.wav",
            name="HN - Mạnh Dũng (Quảng cáo)",
        ),
    }

    def __init__(self, assets_dir: Path | None = None) -> None:
        self.assets_dir = assets_dir or Path(__file__).resolve().parents[2] / "assets" / "ref_audios"

    def resolve(self, *, preset_voice_id: str | None, custom_ref_path: Path | None) -> Path:
        if custom_ref_path is not None:
            if custom_ref_path.is_file() and custom_ref_path.stat().st_size > 0:
                return custom_ref_path
            raise VoiceConversionReferenceNotFoundError("Custom reference audio is unavailable")

        if not preset_voice_id or not preset_voice_id.strip():
            raise VoiceConversionReferenceRequiredError
        preset = self.PRESETS.get(preset_voice_id.strip().lower())
        if preset is None:
            raise VoiceConversionReferenceNotFoundError("Unknown preset reference voice")
        reference_path = self.assets_dir / preset.filename
        if not reference_path.is_file() or reference_path.stat().st_size <= 0:
            raise VoiceConversionReferenceNotFoundError("Preset reference audio is not installed")
        return reference_path
