from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.datetime_utils import utc_now
from app.database.database import Base


class VoiceoverAudio(Base):
    """Ownership metadata for generated voiceover files.

    Files that predate this table are deliberately not recoverable through the
    protected audio endpoint because their owner cannot be established safely.
    """

    __tablename__ = "voiceover_audios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    audio_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_id: Mapped[int | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    duration_seconds: Mapped[float] = mapped_column(nullable=False, default=0.0, server_default="0")
    voice_id: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)

    user = relationship("User")
    message = relationship("Message")