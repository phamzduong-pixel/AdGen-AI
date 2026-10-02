from datetime import datetime

from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.core.datetime_utils import utc_now
from app.database.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String,
        default="Cuộc trò chuyện mới",
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    brand_id: Mapped[int | None] = mapped_column(
        ForeignKey("brand_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
    )

    is_pinned: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="0",
        nullable=False,
    )

    is_title_custom: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="0",
        nullable=False,
    )

    has_generated_title: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="0",
        nullable=False,
    )

    user = relationship(
        "User",
        back_populates="conversations",
    )

    brand = relationship("BrandProfile")

    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )

    uploaded_files = relationship(
        "UploadedFile",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
