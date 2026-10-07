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
from app.models.trend_report import TrendReport


class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "advertising_brief_id", name="uq_campaigns_user_advertising_brief"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    brand_id: Mapped[int | None] = mapped_column(
        ForeignKey("brand_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    trend_report_id: Mapped[int | None] = mapped_column(
        ForeignKey("trend_reports.id", ondelete="SET NULL"), nullable=True, index=True
    )
    advertising_brief_id: Mapped[int | None] = mapped_column(
        ForeignKey("advertising_briefs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    target_audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    objective: Mapped[str | None] = mapped_column(String(500), nullable=True)
    platform: Mapped[str | None] = mapped_column(String(50), nullable=True)
    platform_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
        server_default="draft",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    content_links = relationship(
        "CampaignContent",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )
    brand = relationship("BrandProfile")


class CampaignContent(Base):
    __tablename__ = "campaign_contents"
    __table_args__ = (
        UniqueConstraint(
            "campaign_id",
            "saved_content_id",
            name="uq_campaign_saved_content",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    saved_content_id: Mapped[int] = mapped_column(
        ForeignKey("saved_contents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="0",
        nullable=False,
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
        nullable=False,
    )

    campaign = relationship("Campaign", back_populates="content_links")
    saved_content = relationship("SavedContent")
