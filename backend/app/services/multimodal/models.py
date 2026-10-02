from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ModalityType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


class MultimodalTaskType(str, Enum):
    TEXT_TO_TEXT = "text_to_text"
    IMAGE_TO_TEXT = "image_to_text"
    VIDEO_TO_TEXT = "video_to_text"
    TEXT_TO_IMAGE = "text_to_image"
    TEXT_TO_VIDEO = "text_to_video"
    VIDEO_TO_EDITED_VIDEO = "video_to_edited_video"


class MultimodalEditCommand(str, Enum):
    REMOVE_ON_SCREEN_TEXT = "remove_on_screen_text"
    INJECT_CTA_OVERLAY = "inject_cta_overlay"
    TRIM_VIDEO = "trim_video"
    CHANGE_ASPECT_RATIO = "change_aspect_ratio"
    ADD_SUBTITLES = "add_subtitles"
    ENHANCE_AUDIO = "enhance_audio"
    INSERT_HOOK = "insert_hook"


@dataclass
class MediaEditInstruction:
    command: MultimodalEditCommand
    target_asset_id: str
    parameters: dict[str, Any] = field(default_factory=dict)
    timestamp_start: float | None = None
    timestamp_end: float | None = None
    target_aspect_ratio: str | None = None  # e.g. "9:16", "1:1", "16:9"
    cta_text: str | None = None
    subtitle_language: str = "vi"


@dataclass
class MediaAsset:
    asset_id: str
    modality: ModalityType
    file_path: str
    mime_type: str
    filename: str
    size_bytes: int = 0
    width: int | None = None
    height: int | None = None
    duration_seconds: float | None = None
    metadata: dict = field(default_factory=dict)

    def exists(self) -> bool:
        return Path(self.file_path).is_file()

    def read_bytes(self) -> bytes:
        return Path(self.file_path).read_bytes()


@dataclass
class MultimodalPayload:
    prompt_text: str
    task_type: MultimodalTaskType = MultimodalTaskType.TEXT_TO_TEXT
    media_assets: list[MediaAsset] = field(default_factory=list)
    edit_instructions: list[MediaEditInstruction] = field(default_factory=list)
    target_modality: ModalityType = ModalityType.TEXT
    generation_options: dict = field(default_factory=dict)
