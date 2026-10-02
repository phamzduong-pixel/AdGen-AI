from sqlalchemy import Boolean
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.database.database import Base


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    default_platform: Mapped[str] = mapped_column(
        String(50), default="facebook", nullable=False
    )
    default_platform_name: Mapped[str | None] = mapped_column(
        String(80), nullable=True
    )
    default_tone: Mapped[str] = mapped_column(
        String(100), default="professional", nullable=False
    )
    default_language: Mapped[str] = mapped_column(
        String(50), default="vi", nullable=False
    )
    default_length: Mapped[str] = mapped_column(
        String(30), default="medium", nullable=False
    )
    default_export_format: Mapped[str] = mapped_column(
        String(20), default="markdown", nullable=False
    )
    include_timestamps: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    user = relationship("User", back_populates="settings")
