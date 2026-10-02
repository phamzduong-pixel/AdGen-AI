from typing import Literal

from pydantic import BaseModel


class ContentActivityCreate(BaseModel):
    action_type: Literal["copy", "export", "regenerate"]


class ContentActivityResponse(BaseModel):
    message: str
    saved_content_id: int
    action_type: str
