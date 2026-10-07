from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator
from app.core.platforms import normalize_custom_platform_name


class AdBrief(BaseModel):
    product_name: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=4000)
    target_audience: str = Field(default="", max_length=1000)
    objective: str = Field(default="", max_length=500)
    platform: str = Field(default="", max_length=50)
    platform_name: str | None = Field(default=None, min_length=2, max_length=80)
    tone: str = Field(default="", max_length=100)
    length: str = Field(default="", max_length=50)
    keywords: str = Field(default="", max_length=1000)
    cta: str = Field(default="", max_length=500)
    language: str = Field(default="Tiếng Việt", max_length=100)

    @field_validator("platform_name", mode="before")
    @classmethod
    def normalize_platform_name(cls, value):
        return normalize_custom_platform_name(value)

    @model_validator(mode="after")
    def validate_required_content(self):
        if self.platform.strip().lower() == "other" and not self.platform_name:
            raise ValueError("Cần nhập tên nền tảng hoặc nơi đăng nội dung khi chọn Khác")
        if not self.product_name.strip() and not self.description.strip():
            raise ValueError(
                "Tên sản phẩm và mô tả không được đồng thời để trống"
            )
        return self


class MessageCreate(BaseModel):
    conversation_id: int
    brand_id: int | None = Field(default=None, gt=0)

    content: str = Field(
        ...,
        min_length=1,
        max_length=20_000,
    )

    prompt_type: str | None = Field(
        default=None,
        max_length=50,
    )
    platform_name: str | None = Field(default=None, min_length=2, max_length=80)

    attachment_ids: list[int] = Field(default_factory=list, max_length=5)
    ad_brief: AdBrief | None = None
    trend_report_key: str | None = Field(default=None, min_length=1, max_length=64)
    trend_trust_mode: Literal["all_evidence", "verified_only"] = "all_evidence"


class MessageUpdate(BaseModel):
    content: str = Field(
        ...,
        min_length=1,
        max_length=20_000,
    )

    prompt_type: str | None = Field(
        default=None,
        max_length=50,
    )
    platform_name: str | None = Field(default=None, min_length=2, max_length=80)
    trend_report_key: str | None = Field(default=None, min_length=1, max_length=64)
    trend_trust_mode: Literal["all_evidence", "verified_only"] = "all_evidence"


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    brand_id: int | None = None
    platform_name: str | None = None
    role: str
    content: str
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }
