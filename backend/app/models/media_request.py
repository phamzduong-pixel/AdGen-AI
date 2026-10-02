from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.datetime_utils import utc_now
from app.database.database import Base


class MediaEditRequest(Base):
    """Durable idempotency record for a conversational media edit request."""

    __tablename__ = "media_edit_requests"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "conversation_id",
            "idempotency_key",
            name="uq_media_edit_requests_scope_key",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="processing", nullable=False)
    created_asset_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    failed_operation_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failed_operation: Mapped[str | None] = mapped_column(String(50), nullable=True)
    output_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )