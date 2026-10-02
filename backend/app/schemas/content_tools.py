from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator

from app.core.platforms import normalize_custom_platform_name


class ContentSourceRequest(BaseModel):
    message_id: int | None = Field(default=None, gt=0)
    saved_content_id: int | None = Field(default=None, gt=0)
    content: str | None = Field(default=None, max_length=20_000)
    platform: str | None = Field(default=None, max_length=50)
    platform_name: str | None = Field(default=None, min_length=2, max_length=80)
    target_audience: str | None = Field(default=None, max_length=1_000)
    tone: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_source(self):
        normalized_content = self.content.strip() if self.content else None
        source_count = sum(
            (
                self.message_id is not None,
                self.saved_content_id is not None,
                normalized_content is not None,
            )
        )
        if source_count != 1:
            raise ValueError(
                "Cần cung cấp đúng một nguồn: message_id, saved_content_id hoặc content"
            )
        self.content = normalized_content
        self.platform_name = normalize_custom_platform_name(self.platform_name)
        if self.platform == "other" and not self.platform_name:
            raise ValueError("Vui lòng nhập tên nền tảng hoặc nơi đăng nội dung")
        return self


class ContentEvaluationRequest(ContentSourceRequest):
    pass


class EvaluationCriterion(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    score: int = Field(ge=0, le=100)
    comment: str = Field(min_length=1, max_length=1_000)


class ContentEvaluationResponse(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    criteria: list[EvaluationCriterion] = Field(min_length=9, max_length=9)
    strengths: list[str] = Field(min_length=1, max_length=8)
    improvements: list[str] = Field(min_length=1, max_length=8)
    suggested_revision: str = Field(min_length=1, max_length=20_000)


class ContentVariantRequest(ContentSourceRequest):
    number_of_variants: int = Field(default=3, ge=3, le=3)


class ContentVariant(BaseModel):
    label: str = Field(pattern="^[A-C]$")
    strategy: str = Field(min_length=1, max_length=200)
    title: str = Field(default="", max_length=500)
    content: str = Field(min_length=1, max_length=20_000)
    cta: str = Field(min_length=1, max_length=1_000)


class ContentVariantResponse(BaseModel):
    variants: list[ContentVariant] = Field(min_length=3, max_length=3)
