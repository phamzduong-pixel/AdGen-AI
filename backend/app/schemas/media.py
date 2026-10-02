from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


AspectRatio = Literal["1:1", "4:5", "16:9", "9:16", "3:2", "2:3"]


class ImageGenerateRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=10_000)
    aspect_ratio: AspectRatio = "1:1"
    reference_file_id: int | None = Field(default=None, gt=0)
    source_asset_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def normalize_request(self):
        self.prompt = self.prompt.strip()
        if not self.prompt:
            raise ValueError("Prompt tạo ảnh không được để trống")
        if self.reference_file_id and self.source_asset_id:
            raise ValueError("Chỉ được chọn một ảnh tham chiếu hoặc một asset nguồn")
        return self


class VideoGenerationRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=10_000)
    aspect_ratio: Literal["16:9", "9:16"] = "16:9"
    duration_seconds: Annotated[int, Field(ge=8, le=8)] = 8
    reference_asset_ids: list[int] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def normalize_request(self):
        self.prompt = self.prompt.strip()
        if not self.prompt:
            raise ValueError("Prompt tạo video không được để trống")
        if any(asset_id <= 0 for asset_id in self.reference_asset_ids):
            raise ValueError("Reference asset ID không hợp lệ")
        if len(set(self.reference_asset_ids)) != len(self.reference_asset_ids):
            raise ValueError("Danh sách reference asset không được trùng")
        return self


class AspectCropOperation(BaseModel):
    operation: Literal["aspect_crop"]
    aspect_ratio: Literal["16:9", "9:16", "1:1", "4:5"]


class TextOverlayOperation(BaseModel):
    operation: Literal["text_overlay", "cta_overlay"]
    text: str = Field(min_length=1, max_length=500)
    start: Annotated[float, Field(ge=0, le=300)]
    end: Annotated[float, Field(gt=0, le=300)]
    position: Literal["top", "center", "bottom"] = "bottom"
    font_size: Annotated[int, Field(ge=12, le=160)] = 48
    text_color: Literal["white", "black", "yellow"] = "white"
    background: bool = True

    @model_validator(mode="after")
    def validate_timing(self):
        self.text = self.text.strip()
        if not self.text:
            raise ValueError("Text overlay không được để trống")
        if self.end <= self.start:
            raise ValueError("Thời điểm kết thúc phải lớn hơn thời điểm bắt đầu")
        return self


class SubtitleEntry(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    start: Annotated[float, Field(ge=0, le=300)]
    end: Annotated[float, Field(gt=0, le=300)]

    @model_validator(mode="after")
    def validate_timing(self):
        self.text = self.text.strip()
        if not self.text:
            raise ValueError("Subtitle không được để trống")
        if self.end <= self.start:
            raise ValueError("Thời điểm subtitle không hợp lệ")
        return self


class SubtitleOperation(BaseModel):
    operation: Literal["subtitle"]
    entries: list[SubtitleEntry] = Field(min_length=1, max_length=20)
    position: Literal["top", "center", "bottom"] = "bottom"


class AudioOperation(BaseModel):
    operation: Literal["volume", "mute"]
    volume: Annotated[float, Field(ge=0, le=4)] = 1.0

    @model_validator(mode="after")
    def validate_volume(self):
        if self.operation == "mute" and self.volume != 1.0:
            raise ValueError("Mute không nhận volume tùy chỉnh")
        return self


class MergeVideoOperation(BaseModel):
    operation: Literal["merge"]
    source_asset_ids: list[int] = Field(min_length=2, max_length=5)

    @model_validator(mode="after")
    def validate_sources(self):
        if len(set(self.source_asset_ids)) != len(self.source_asset_ids):
            raise ValueError("Danh sách video merge không được trùng asset")
        return self


class VideoSourceRequest(BaseModel):
    source_file_id: int = Field(gt=0)


class TrimVideoOperation(BaseModel):
    operation: Literal["trim"]
    start: Annotated[float, Field(ge=0, le=300)]
    end: Annotated[float, Field(gt=0, le=300)]

    @model_validator(mode="after")
    def validate_range(self):
        if self.end <= self.start:
            raise ValueError("Thời điểm kết thúc phải lớn hơn thời điểm bắt đầu")
        return self


VideoEditRequest = (
    TrimVideoOperation
    | AspectCropOperation
    | TextOverlayOperation
    | SubtitleOperation
    | AudioOperation
    | MergeVideoOperation
)


class ConversationalEditPlanRequest(BaseModel):
    instruction: str = Field(min_length=3, max_length=2_000)
    merge_source_asset_ids: list[int] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def normalize_request(self):
        self.instruction = self.instruction.strip()
        if not self.instruction:
            raise ValueError("Edit instruction must not be empty")
        if any(asset_id <= 0 for asset_id in self.merge_source_asset_ids):
            raise ValueError("Merge source asset ID is invalid")
        if len(set(self.merge_source_asset_ids)) != len(self.merge_source_asset_ids):
            raise ValueError("Merge source assets must be unique")
        return self


class ConversationalEditPlan(BaseModel):
    source_asset_id: int = Field(gt=0)
    operations: list[VideoEditRequest] = Field(min_length=1, max_length=8)


class ConversationalEditExecuteRequest(BaseModel):
    plan: ConversationalEditPlan
    confirm: bool = True


class MediaAssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    parent_asset_id: int | None
    source_uploaded_file_id: int | None
    version_number: int
    kind: str
    operation: str
    status: str
    prompt: str
    aspect_ratio: str | None
    provider: str | None
    model: str | None
    filename: str | None
    content_type: str | None
    size: int
    error_message: str | None
    operation_params: dict | None
    duration_seconds: float | None
    width: int | None
    height: int | None
    created_at: datetime
    url: str
    download_url: str


class ConversationalEditPlanResponse(BaseModel):
    source_asset_id: int
    instruction: str
    operations: list[VideoEditRequest]
    summary: list[str]


class ConversationalEditExecutionResponse(BaseModel):
    status: Literal["completed", "partial", "failed", "processing", "recovery_required"]
    source_asset_id: int
    output_asset: MediaAssetResponse | None = None
    created_assets: list[MediaAssetResponse] = Field(default_factory=list)
    failed_operation_index: int | None = None
    failed_operation: str | None = None
    error: str | None = None


class MediaJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    prompt: str
    aspect_ratio: str
    duration_seconds: float | None
    source_asset_ids: list[int] | None
    provider: str
    provider_model: str | None
    provider_job_id: str | None
    status: str
    error_message: str | None
    output_asset_id: int | None
    output_asset: MediaAssetResponse | None = None
    created_at: datetime
    updated_at: datetime
