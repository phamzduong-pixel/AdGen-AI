from datetime import datetime

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from app.core.platforms import normalize_custom_platform_name


class TemplateFields(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=500)
    platform: str = Field(default="facebook", min_length=1, max_length=50)
    platform_name: str | None = Field(default=None, min_length=2, max_length=80)
    category: str = Field(default="Mẫu cá nhân", min_length=1, max_length=80)
    prompt_template: str | None = Field(default=None, max_length=20_000)
    default_tone: str = Field(default="Chuyên nghiệp", max_length=100)
    default_length: str = Field(default="Trung bình", max_length=50)
    suggested_cta: str = Field(default="", max_length=300)

    @field_validator(
        "title",
        "description",
        "platform",
        "platform_name",
        "category",
        "prompt_template",
        "default_tone",
        "default_length",
        "suggested_cta",
        mode="before",
    )
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_platform_name(self):
        self.platform_name = normalize_custom_platform_name(self.platform_name)
        if self.platform == "other" and not self.platform_name:
            raise ValueError("Vui lòng nhập tên nền tảng hoặc nơi đăng nội dung")
        return self


class CustomTemplateCreate(TemplateFields):
    source_template_id: int | None = Field(default=None, gt=0)
    source_saved_content_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_source(self):
        if self.source_template_id and self.source_saved_content_id:
            raise ValueError("Chỉ được chọn một nguồn để tạo mẫu")
        if (
            not self.prompt_template
            and not self.source_template_id
            and not self.source_saved_content_id
        ):
            raise ValueError("Nội dung prompt_template không được để trống")
        return self


class CustomTemplateUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=500)
    platform: str | None = Field(default=None, min_length=1, max_length=50)
    platform_name: str | None = Field(default=None, min_length=2, max_length=80)
    category: str | None = Field(default=None, min_length=1, max_length=80)
    prompt_template: str | None = Field(
        default=None,
        min_length=1,
        max_length=20_000,
    )
    default_tone: str | None = Field(default=None, max_length=100)
    default_length: str | None = Field(default=None, max_length=50)
    suggested_cta: str | None = Field(default=None, max_length=300)

    @field_validator("*", mode="before")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("Cần có ít nhất một trường để cập nhật")
        return self


class TemplateResponse(BaseModel):
    id: int
    title: str
    description: str
    platform: str
    platform_name: str | None = None
    category: str
    prompt_template: str
    default_tone: str
    default_length: str
    suggested_cta: str
    is_system: bool
    is_popular: bool
    is_favorite: bool
    is_owner: bool
    created_at: datetime


class TemplateDeleteResponse(BaseModel):
    message: str
    id: int
