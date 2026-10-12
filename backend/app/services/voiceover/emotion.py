"""Provider-aware emotion cue helpers for VieNeu-TTS."""

from __future__ import annotations

from typing import Final


VIENEU_EMOTION_CUES: Final[dict[str, str]] = {
    "none": "",
    "laugh": "[c\u01b0\u1eddi]",
    "sigh": "[th\u1edf d\u00e0i]",
    "clear_throat": "[h\u1eafng gi\u1ecdng]",
}


def is_vieneu_voice(voice_id: str | None) -> bool:
    return bool(voice_id and voice_id.startswith("vieneu-v3-turbo:"))


def apply_vieneu_emotion_cue(text: str, emotion_cue: str | None) -> str:
    normalized_text = text.strip()
    token = VIENEU_EMOTION_CUES.get(str(emotion_cue or "none").strip().lower(), "")
    if not token or token in normalized_text:
        return normalized_text
    return f"{normalized_text} {token}" if normalized_text else token
