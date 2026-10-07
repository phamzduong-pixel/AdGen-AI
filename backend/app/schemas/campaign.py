from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from app.core.platforms import normalize_custom_platform_name
from app.schemas.saved_content import SavedContentResponse


CampaignStatus = Literal["draft", "active", "completed", "archived"]


class CampaignBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=5_000)
    notes: str | None = Field(default=None, max_length=5_000)
    product_name: str | None = Field(default=None, max_length=200)
    target_audience: str | None = Field(default=None, max_length=2_000)
    objective: str | None = Field(default=None, max_length=500)
    platform: str | None = Field(default=None, max_length=50)
    platform_name: str | None = Field(default=None, min_length=2, max_length=80)
    status: CampaignStatus = "draft"
    brand_id: int | None = Field(default=None, gt=0)
    trend_report_id: int | None = Field(default=None, gt=0)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Tên chiến dịch không được để trống")
        return normalized

    @field_validator(
        "description",
        "notes",
        "product_name",
        "target_audience",
        "objective",
        "platform",
        "platform_name",
    )
    @classmethod
    def normalize_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_custom_platform(self):
        self.platform_name = normalize_custom_platform_name(self.platform_name)
        if self.platform == "other" and not self.platform_name:
            raise ValueError("Vui lòng nhập tên nền tảng hoặc nơi đăng nội dung")
        return self


class CampaignCreate(CampaignBase):
    @field_validator("platform_name", mode="before")
    @classmethod
    def normalize_platform_name(cls, value):
        return normalize_custom_platform_name(value)


class CampaignUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=5_000)
    notes: str | None = Field(default=None, max_length=5_000)
    product_name: str | None = Field(default=None, max_length=200)
    target_audience: str | None = Field(default=None, max_length=2_000)
    objective: str | None = Field(default=None, max_length=500)
    platform: str | None = Field(default=None, max_length=50)
    platform_name: str | None = Field(default=None, min_length=2, max_length=80)
    status: CampaignStatus | None = None
    brand_id: int | None = Field(default=None, gt=0)
    trend_report_id: int | None = Field(default=None, gt=0)

    @field_validator("name")
    @classmethod
    def normalize_update_name(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Tên chiến dịch không được để trống")
        return CampaignBase.normalize_name(value)

    @field_validator(
        "description",
        "notes",
        "product_name",
        "target_audience",
        "objective",
        "platform",
        "platform_name",
    )
    @classmethod
    def normalize_update_optional(cls, value: str | None) -> str | None:
        return CampaignBase.normalize_optional(value)


    @model_validator(mode="after")
    def validate_update_custom_platform(self):
        self.platform_name = normalize_custom_platform_name(self.platform_name)
        if self.platform == "other" and not self.platform_name:
            raise ValueError("Vui lòng nhập tên nền tảng hoặc nơi đăng nội dung")
        return self


class CampaignContentAdd(BaseModel):
    saved_content_id: int = Field(gt=0)


class CampaignContentPrimaryUpdate(BaseModel):
    is_primary: bool = True


class ContentStatistics(BaseModel):
    copy_count: int = 0
    export_count: int = 0
    regenerate_count: int = 0
    evaluation_count: int = 0
    latest_score: float | None = None
    highest_score: float | None = None
    last_used_at: datetime | None = None


class CampaignContentResponse(BaseModel):
    id: int
    is_primary: bool
    added_at: datetime
    saved_content: SavedContentResponse
    statistics: ContentStatistics


class CampaignListResponse(CampaignBase):
    id: int
    user_id: int
    contents_count: int
    created_at: datetime
    updated_at: datetime
    brand_name: str | None = None
    advertising_brief_id: int | None = None


class CampaignDetailResponse(CampaignListResponse):
    contents: list[CampaignContentResponse]


class CampaignDeleteResponse(BaseModel):
    message: str
    campaign_id: int
