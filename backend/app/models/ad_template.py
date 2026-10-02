from datetime import datetime

from sqlalchemy import Boolean
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


class AdTemplate(Base):
    __tablename__ = "ad_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    system_key: Mapped[str | None] = mapped_column(
        String(80),
        unique=True,
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    platform_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    default_tone: Mapped[str] = mapped_column(String(100), nullable=False)
    default_length: Mapped[str] = mapped_column(String(50), nullable=False)
    suggested_cta: Mapped[str] = mapped_column(String(300), nullable=False)
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="0",
        nullable=False,
        index=True,
    )
    is_popular: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="0",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False,
    )

    favorites = relationship(
        "TemplateFavorite",
        back_populates="template",
        cascade="all, delete-orphan",
    )


class TemplateFavorite(Base):
    __tablename__ = "template_favorites"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "template_id",
            name="uq_template_favorite_user_template",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    template_id: Mapped[int] = mapped_column(
        ForeignKey("ad_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False,
    )

    template = relationship("AdTemplate", back_populates="favorites")
