from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


ContentStatus = Literal["draft", "ready", "archived"]
RewriteAction = Literal[
    "shorter",
    "longer",
    "professional",
    "friendly",
    "spelling",
    "improve_cta",
    "new_title",
    "add_hashtags",
    "align_brand",
    "alternative",
]


class ContentDocumentCreate(BaseModel):
    source_message_id: int | None = Field(default=None, gt=0)
    source_saved_content_id: int | None = Field(default=None, gt=0)
    title: str | None = Field(default=None, max_length=160)
    content: str | None = Field(default=None, max_length=50_000)
    cta: str | None = Field(default=None, max_length=1000)
    hashtags: str | None = Field(default=None, max_length=3000)
    internal_notes: str | None = Field(default=None, max_length=10_000)
    platform: str | None = Field(default=None, max_length=50)
    platform_name: str | None = Field(default=None, min_length=2, max_length=80)
    brand_id: int | None = Field(default=None, gt=0)
    campaign_id: int | None = Field(default=None, gt=0)
    status: ContentStatus = "draft"

    @model_validator(mode="after")
    def validate_source(self):
        sources = [
            self.source_message_id is not None,
            self.source_saved_content_id is not None,
            bool(self.content and self.content.strip()),
        ]
        if sum(sources) != 1:
            raise ValueError(
                "Chọn đúng một nguồn: message, nội dung đã lưu hoặc content trực tiếp."
            )
        return self


class ContentDocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    content: str | None = Field(default=None, min_length=1, max_length=50_000)
    cta: str | None = Field(default=None, max_length=1000)
    hashtags: str | None = Field(default=None, max_length=3000)
    internal_notes: str | None = Field(default=None, max_length=10_000)
    platform: str | None = Field(default=None, max_length=50)
    platform_name: str | None = Field(default=None, min_length=2, max_length=80)
    brand_id: int | None = Field(default=None, gt=0)
    campaign_id: int | None = Field(default=None, gt=0)
    status: ContentStatus | None = None
    is_campaign_primary: bool | None = None


class ContentVersionCreate(BaseModel):
    change_summary: str | None = Field(default=None, max_length=500)
    created_by: Literal["user", "ai"] = "user"


class ContentVersionResponse(BaseModel):
    id: int
    content_id: int
    version_number: int
    title: str
    content: str
    cta: str | None
    hashtags: str | None
    internal_notes: str | None
    change_summary: str
    created_by: str
    created_by_user_id: int | None
    created_at: datetime
    model_config = {"from_attributes": True}


class ContentDocumentResponse(BaseModel):
    id: int
    user_id: int
    source_message_id: int | None
    source_saved_content_id: int | None
    source_conversation_id: int | None
    title: str
    content: str
    cta: str | None
    hashtags: str | None
    internal_notes: str | None
    platform: str | None
    platform_name: str | None = None
    status: ContentStatus
    current_version: int
    brand_id: int | None
    brand_name: str | None = None
    campaign_id: int | None
    campaign_name: str | None = None
    is_campaign_primary: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class ContentVersionCreateResponse(BaseModel):
    created: bool
    version: ContentVersionResponse
    document: ContentDocumentResponse


class ContentRestoreResponse(BaseModel):
    document: ContentDocumentResponse
    version: ContentVersionResponse


class ContentRewriteRequest(BaseModel):
    action: RewriteAction
    selected_text: str | None = Field(default=None, max_length=20_000)


class ContentRewriteResponse(BaseModel):
    action: RewriteAction
    suggestion: str
    scope: Literal["selection", "document"]


class ContentDeleteResponse(BaseModel):
    message: str
    id: int
