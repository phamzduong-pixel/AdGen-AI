from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.datetime_utils import utc_now
from app.database.database import Base


class MediaAsset(Base):
    """A generated media file kept independently from uploaded attachments."""

    __tablename__ = "media_assets"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "conversation_id",
            "kind",
            "root_asset_id",
            "version_number",
            name="uq_media_assets_lineage_version",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    parent_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    root_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    source_uploaded_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("uploaded_files.id", ondelete="SET NULL"), nullable=True
    )
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), default="image", nullable=False)
    operation: Mapped[str] = mapped_column(
        String(20), default="generate", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default="processing", nullable=False
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    aspect_ratio: Mapped[str | None] = mapped_column(String(10), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    filepath: Mapped[str | None] = mapped_column(String(1_000), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    operation_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )