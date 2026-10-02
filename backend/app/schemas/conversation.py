from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import field_validator


class ConversationCreate(BaseModel):
    brand_id: int | None = None
    title: str = "Cuộc trò chuyện mới"

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        title = " ".join(value.split())
        if not title:
            raise ValueError("Conversation title cannot be empty")
        return title


class ConversationUpdate(BaseModel):
    title: str

    _normalize_title = field_validator("title")(ConversationCreate.normalize_title.__func__)


class ConversationPinUpdate(BaseModel):
    is_pinned: bool | None = None


class ConversationBrandUpdate(BaseModel):
    brand_id: int | None = None


class ConversationDeleteResponse(BaseModel):
    message: str
    conversation_id: int


class ConversationResponse(BaseModel):
    id: int
    title: str
    user_id: int
    brand_id: int | None = None
    is_pinned: bool
    is_title_custom: bool
    has_generated_title: bool

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )
