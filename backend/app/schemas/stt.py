from pydantic import BaseModel, Field


class TranscriptionResponse(BaseModel):
    success: bool = True
    transcript: str
    language: str | None = None
    provider: str
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
