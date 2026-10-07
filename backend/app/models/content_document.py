from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.datetime_utils import utc_now
from app.database.database import Base
from app.models.trend_report import TrendReport


class ContentDocument(Base):
    __tablename__ = "content_documents"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "source_message_id",
            name="uq_content_documents_user_message",
        ),
        UniqueConstraint(
            "user_id",
            "source_saved_content_id",
            name="uq_content_documents_user_saved_content",
        ),
        Index(
            "uq_content_documents_user_trend_report",
            "user_id",
            "trend_report_id",
            unique=True,
        ),
        Index(
            "uq_content_documents_campaign_primary",
            "campaign_id",
            unique=True,
            sqlite_where=text("is_campaign_primary = 1 AND campaign_id IS NOT NULL"),
            postgresql_where=text(
                "is_campaign_primary AND campaign_id IS NOT NULL"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_saved_content_id: Mapped[int | None] = mapped_column(
        ForeignKey("saved_contents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    trend_report_id: Mapped[int | None] = mapped_column(
        ForeignKey("trend_reports.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    brand_id: Mapped[int | None] = mapped_column(
        ForeignKey("brand_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    campaign_id: Mapped[int | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    cta: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    hashtags: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    platform: Mapped[str | None] = mapped_column(String(50), nullable=True)
    platform_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="draft", server_default="draft", nullable=False
    )
    current_version: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1", nullable=False
    )
    is_campaign_primary: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    brand = relationship("BrandProfile")
    campaign = relationship("Campaign")
    versions = relationship(
        "ContentVersion",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="ContentVersion.version_number.desc()",
    )


class ContentVersion(Base):
    __tablename__ = "content_versions"
    __table_args__ = (
        UniqueConstraint(
            "content_id",
            "version_number",
            name="uq_content_versions_number",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content_id: Mapped[int] = mapped_column(
        ForeignKey("content_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    cta: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    hashtags: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_summary: Mapped[str] = mapped_column(String(500), nullable=False)
    created_by: Mapped[str] = mapped_column(
        String(20), default="user", server_default="user", nullable=False
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )

    document = relationship("ContentDocument", back_populates="versions")
