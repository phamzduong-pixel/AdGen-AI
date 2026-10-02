from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.datetime_utils import utc_now
from app.database.database import Base


class BrandProfile(Base):
    __tablename__ = "brand_profiles"
    __table_args__ = (
        Index("ix_brand_profiles_user_name", "user_id", "name"),
        Index(
            "uq_brand_profiles_one_default",
            "user_id",
            unique=True,
            sqlite_where=text("is_default = 1"),
            postgresql_where=text("is_default"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    industry: Mapped[str | None] = mapped_column(String(160))
    website: Mapped[str | None] = mapped_column(String(500))
    slogan: Mapped[str | None] = mapped_column(String(500))
    mission: Mapped[str | None] = mapped_column(Text)
    target_audience: Mapped[str | None] = mapped_column(Text)
    brand_personality: Mapped[str | None] = mapped_column(String(500))
    default_tone: Mapped[str | None] = mapped_column(String(100))
    default_language: Mapped[str | None] = mapped_column(String(100))
    primary_color: Mapped[str | None] = mapped_column(String(7))
    secondary_color: Mapped[str | None] = mapped_column(String(7))
    keywords_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    forbidden_words_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    preferred_cta: Mapped[str | None] = mapped_column(String(500))
    writing_guidelines: Mapped[str | None] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )

    user = relationship("User", back_populates="brands")
    assets = relationship(
        "BrandAsset", back_populates="brand", cascade="all, delete-orphan"
    )
    checks = relationship(
        "BrandContentCheck", back_populates="brand", cascade="all, delete-orphan"
    )


class BrandAsset(Base):
    __tablename__ = "brand_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brand_id: Mapped[int] = mapped_column(
        ForeignKey("brand_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(120), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    brand = relationship("BrandProfile", back_populates="assets")


class BrandContentCheck(Base):
    __tablename__ = "brand_content_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brand_id: Mapped[int] = mapped_column(
        ForeignKey("brand_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    platform: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now
    )
    brand = relationship("BrandProfile", back_populates="checks")
