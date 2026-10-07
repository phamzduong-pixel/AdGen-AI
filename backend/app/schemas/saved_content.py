from datetime import datetime

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator


class SavedContentCreate(BaseModel):
    message_id: int | None = Field(default=None, gt=0)
    trend_report_id: int | None = Field(default=None, gt=0)
    conversation_id: int | None = Field(default=None, gt=0)
    title: str | None = Field(default=None, max_length=160)
    content: str | None = Field(default=None, max_length=20_000)
    platform: str | None = Field(default=None, max_length=50)
    platform_name: str | None = Field(default=None, min_length=2, max_length=80)
    brand_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_source(self):
        if self.trend_report_id is not None:
            if (
                self.message_id is not None
                or self.content is not None
                or self.conversation_id is not None
            ):
                raise ValueError("Không gửi nguồn khác khi lưu theo trend_report_id")
            return self

        if self.message_id is not None:
            if self.content is not None or self.conversation_id is not None:
                raise ValueError(
                    "Không gửi content hoặc conversation_id khi lưu theo message_id"
                )
            return self

        self.content = self.content.strip() if self.content else None
        if not self.content or self.conversation_id is None:
            raise ValueError(
                "Cần có message_id hoặc đầy đủ conversation_id và content"
            )
        return self


class SavedContentResponse(BaseModel):
    id: int
    user_id: int
    conversation_id: int
    message_id: int | None
    trend_report_id: int | None
    title: str
    content: str
    platform: str | None
    platform_name: str | None = None
    brand_id: int | None = None
    brand_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SavedContentDeleteResponse(BaseModel):
    message: str
    id: int
    message_id: int | None
