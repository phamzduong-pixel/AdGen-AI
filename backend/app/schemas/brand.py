from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


HEX_PATTERN = r"^#[0-9A-Fa-f]{6}$"


class BrandBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=5000)
    industry: str | None = Field(default=None, max_length=160)
    website: str | None = Field(default=None, max_length=500)
    slogan: str | None = Field(default=None, max_length=500)
    mission: str | None = Field(default=None, max_length=5000)
    target_audience: str | None = Field(default=None, max_length=3000)
    brand_personality: str | None = Field(default=None, max_length=500)
    default_tone: str | None = Field(default=None, max_length=100)
    default_language: str | None = Field(default=None, max_length=100)
    primary_color: str | None = Field(default=None, pattern=HEX_PATTERN)
    secondary_color: str | None = Field(default=None, pattern=HEX_PATTERN)
    keywords: list[str] = Field(default_factory=list, max_length=30)
    forbidden_words: list[str] = Field(default_factory=list, max_length=30)
    preferred_cta: str | None = Field(default=None, max_length=500)
    writing_guidelines: str | None = Field(default=None, max_length=5000)
    is_default: bool = False

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Tên thương hiệu không được để trống")
        return normalized

    @field_validator(
        "description",
        "industry",
        "website",
        "slogan",
        "mission",
        "target_audience",
        "brand_personality",
        "default_tone",
        "default_language",
        "primary_color",
        "secondary_color",
        "preferred_cta",
        "writing_guidelines",
    )
    @classmethod
    def normalize_optional(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("website")
    @classmethod
    def validate_website(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Website phải là URL http/https hợp lệ")
        return value

    @field_validator("keywords", "forbidden_words")
    @classmethod
    def normalize_list(cls, values: list[str]) -> list[str]:
        normalized = []
        seen = set()
        for item in values:
            value = " ".join(item.split())[:100]
            key = value.lower()
            if value and key not in seen:
                normalized.append(value)
                seen.add(key)
        return normalized


class BrandCreate(BrandBase):
    pass


class BrandUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=5000)
    industry: str | None = Field(default=None, max_length=160)
    website: str | None = Field(default=None, max_length=500)
    slogan: str | None = Field(default=None, max_length=500)
    mission: str | None = Field(default=None, max_length=5000)
    target_audience: str | None = Field(default=None, max_length=3000)
    brand_personality: str | None = Field(default=None, max_length=500)
    default_tone: str | None = Field(default=None, max_length=100)
    default_language: str | None = Field(default=None, max_length=100)
    primary_color: str | None = Field(default=None, pattern=HEX_PATTERN)
    secondary_color: str | None = Field(default=None, pattern=HEX_PATTERN)
    keywords: list[str] | None = Field(default=None, max_length=30)
    forbidden_words: list[str] | None = Field(default=None, max_length=30)
    preferred_cta: str | None = Field(default=None, max_length=500)
    writing_guidelines: str | None = Field(default=None, max_length=5000)
    is_default: bool | None = None

    _normalize_name = field_validator("name")(BrandBase.normalize_name.__func__)
    _normalize_website = field_validator("website")(BrandBase.validate_website.__func__)
    _normalize_lists = field_validator("keywords", "forbidden_words")(
        BrandBase.normalize_list.__func__
    )


class BrandAssetResponse(BaseModel):
    id: int
    brand_id: int
    file_name: str
    file_type: str
    file_url: str
    size: int
    created_at: datetime
    model_config = {"from_attributes": True}


class BrandResponse(BrandBase):
    id: int
    user_id: int
    assets: list[BrandAssetResponse] = []
    created_at: datetime
    updated_at: datetime


class BrandDeleteResponse(BaseModel):
    message: str
    brand_id: int


class BrandContentCheckRequest(BaseModel):
    content: str = Field(min_length=1, max_length=20_000)
    platform: str | None = Field(default=None, max_length=50)

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Nội dung không được để trống")
        return normalized


class BrandContentCheckResponse(BaseModel):
    score: int = Field(ge=0, le=100)
    is_consistent: bool
    issues: list[str]
    suggestions: list[str]
    matched_guidelines: list[str]
    disclaimer: str = "Đây là đánh giá hỗ trợ của AI."


class BrandStatisticsResponse(BaseModel):
    saved_contents_count: int
    campaigns_count: int
    average_consistency_score: float | None
    top_platform: str | None
