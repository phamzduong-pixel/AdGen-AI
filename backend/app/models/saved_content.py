from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.core.datetime_utils import utc_now
from app.database.database import Base


class SavedContent(Base):
    __tablename__ = "saved_contents"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "message_id",
            name="uq_saved_contents_user_message",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    brand_id: Mapped[int | None] = mapped_column(
        ForeignKey("brand_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    message_id: Mapped[int | None] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    platform: Mapped[str | None] = mapped_column(String(50), nullable=True)
    platform_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False,
    )

    brand = relationship("BrandProfile")

    @property
    def brand_name(self) -> str | None:
        return self.brand.name if self.brand else None
