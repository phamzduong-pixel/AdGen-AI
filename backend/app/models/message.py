from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.core.datetime_utils import utc_now
from app.database.database import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id"),
        nullable=False,
    )

    brand_id: Mapped[int | None] = mapped_column(
        ForeignKey("brand_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
    )

    conversation = relationship(
        "Conversation",
        back_populates="messages",
    )

    brand = relationship("BrandProfile")

    ad_brief_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    prompt_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    platform_name: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    attachments = relationship(
        "UploadedFile",
        back_populates="message",
    )
