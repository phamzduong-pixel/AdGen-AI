from typing import List, Optional, Union
from pydantic import BaseModel, Field, field_validator


class VoiceOption(BaseModel):
    id: str = Field(..., description="Unique voice identifier, e.g. vi-VN-HoaiMyNeural")
    name: str = Field(..., description="Display name, e.g. Hoai My (Nu)")
    gender: str = Field(..., description="male or female")
    language: str = Field(..., description="Language code, e.g. vi-VN")
    description: Optional[str] = Field(None, description="Tone/style description")
    sample_rate: int = Field(default=24000, description="Sample rate in Hz")


class CleanScriptRequest(BaseModel):
    raw_script: str = Field(..., min_length=1, max_length=10000, description="Raw ad script")


class CleanScriptResponse(BaseModel):
    cleaned_script: str = Field(..., description="Cleaned dialogue ready for TTS")
    original_length: int
    cleaned_length: int
    removed_tags_count: int
    status: str = Field(default="success", description="'success' | 'uncertain' | 'no_dialogue'")
    dialogue_blocks_count: int = Field(default=0, description="Number of detected spoken dialogue blocks")
    warning_message: Optional[str] = Field(None, description="Guidance or warning for user review")


class VoiceoverGenerateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000, description="Dialogue text to synthesize")
    voice_id: str = Field(default="vi-VN-HoaiMyNeural", description="Voice ID from available voices")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Playback speed multiplier (0.5x to 2.0x)")
    pitch: Optional[Union[int, float]] = Field(default=0, ge=-50, le=50, description="Pitch adjustment in Hz or percent")
    message_id: Optional[Union[str, int]] = Field(default=None, description="Optional associated message ID")

    @field_validator("message_id", mode="before")
    @classmethod
    def coerce_message_id(cls, v):
        if v is None:
            return None
        return str(v)

    @field_validator("pitch", mode="before")
    @classmethod
    def coerce_pitch(cls, v):
        if v is None:
            return 0
        try:
            return int(round(float(v)))
        except (ValueError, TypeError):
            return 0

    @field_validator("speed", mode="before")
    @classmethod
    def coerce_speed(cls, v):
        if v is None:
            return 1.0
        try:
            return float(v)
        except (ValueError, TypeError):
            return 1.0


class VoiceoverGenerateResponse(BaseModel):
    success: bool
    audio_id: str
    audio_url: str
    download_url: str
    duration_seconds: float
    file_size_bytes: int
    voice_id: str
    voice_name: str
    speed: float
    cleaned_text: str
