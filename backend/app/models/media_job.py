from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.datetime_utils import utc_now
from app.database.database import Base


class MediaJob(Base):
    """A provider-backed asynchronous media generation request."""

    __tablename__ = "media_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    aspect_ratio: Mapped[str] = mapped_column(String(10), nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_asset_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider_job_id: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )
