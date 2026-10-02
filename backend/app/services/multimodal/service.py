from pathlib import Path
from typing import Any

from app.services.multimodal.interfaces import (
    IMediaAnalyzer,
    IMultimodalProcessor,
)
from app.services.multimodal.models import (
    MediaAsset,
    MediaEditInstruction,
    ModalityType,
    MultimodalPayload,
    MultimodalTaskType,
)


class StandardMultimodalProcessor(IMultimodalProcessor):
    """
    Bộ xử lý đa phương thức chuẩn cho Gemini AI Core:
    Hỗ trợ chuyển đổi MediaAsset (Image, Video, Audio, Document) thành parts.
    """

    def can_handle(self, task_type: MultimodalTaskType) -> bool:
        return task_type in [
            MultimodalTaskType.TEXT_TO_TEXT,
            MultimodalTaskType.IMAGE_TO_TEXT,
            MultimodalTaskType.VIDEO_TO_TEXT,
            MultimodalTaskType.TEXT_TO_IMAGE,
            MultimodalTaskType.TEXT_TO_VIDEO,
            MultimodalTaskType.VIDEO_TO_EDITED_VIDEO,
        ]

    def prepare_parts(self, payload: MultimodalPayload) -> list[dict]:
        parts: list[dict] = []

        # 1. Text prompt part
        if payload.prompt_text.strip():
            parts.append({
                "type": "text",
                "text": payload.prompt_text.strip(),
            })

        # 2. Media asset parts
        for asset in payload.media_assets:
            if not asset.exists():
                continue

            if asset.modality in [ModalityType.IMAGE, ModalityType.VIDEO, ModalityType.AUDIO]:
                parts.append({
                    "type": "binary",
                    "bytes": asset.read_bytes(),
                    "mime_type": asset.mime_type,
                    "filename": asset.filename,
                })
            else:
                # Text/document
                text_content = Path(asset.file_path).read_text(
                    encoding="utf-8",
                    errors="replace",
                )[:50_000]
                parts.append({
                    "type": "text",
                    "text": f"Nội dung tệp {asset.filename}:\n{text_content}",
                })

        return parts


class MultimodalService:
    """
    Dịch vụ điều phối đa phương thức (Multimodal Service).
    Đảm bảo hệ thống không chỉ phụ thuộc vào Text Input, mà sẵn sàng xử lý:
    - Image -> Text (Vision OCR & Visual product copy)
    - Video -> Text (Scene & Speech to short video script)
    - Text -> Image / Text -> Video / Video -> Edited Video contracts
    """

    def __init__(self, processor: IMultimodalProcessor | None = None):
        self.processor: IMultimodalProcessor = processor or StandardMultimodalProcessor()

    def create_media_asset(
        self,
        asset_id: str,
        file_path: str,
        filename: str,
        mime_type: str,
    ) -> MediaAsset:
        path = Path(file_path)
        modality = ModalityType.TEXT

        if mime_type.startswith("image/"):
            modality = ModalityType.IMAGE
        elif mime_type.startswith("video/"):
            modality = ModalityType.VIDEO
        elif mime_type.startswith("audio/"):
            modality = ModalityType.AUDIO

        size_bytes = path.stat().st_size if path.is_file() else 0

        return MediaAsset(
            asset_id=asset_id,
            modality=modality,
            file_path=file_path,
            mime_type=mime_type,
            filename=filename,
            size_bytes=size_bytes,
        )

    def prepare_multimodal_context(self, payload: MultimodalPayload) -> list[dict]:
        return self.processor.prepare_parts(payload)

    def format_edit_instructions(self, edit_instructions: list[MediaEditInstruction]) -> str:
        """Định dạng các chỉ dẫn biên tập đa phương thức cho prompt AI."""
        if not edit_instructions:
            return ""

        lines = ["### CHỈ DẪN BIÊN TẬP ĐA PHƯƠNG THỨC (MULTIMODAL EDITING INSTRUCTIONS):"]
        for idx, inst in enumerate(edit_instructions, start=1):
            cmd_name = inst.command.value
            target = inst.target_asset_id
            details = []
            if inst.timestamp_start is not None and inst.timestamp_end is not None:
                details.append(f"Mốc thời gian: {inst.timestamp_start}s - {inst.timestamp_end}s")
            if inst.target_aspect_ratio:
                details.append(f"Tỷ lệ khung hình: {inst.target_aspect_ratio}")
            if inst.cta_text:
                details.append(f"CTA chèn: '{inst.cta_text}'")
            detail_str = f" ({', '.join(details)})" if details else ""
            lines.append(f"{idx}. Lệnh `{cmd_name}` trên file `{target}`{detail_str}")

        return "\n".join(lines)


multimodal_service = MultimodalService()

