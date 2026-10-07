from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.datetime_utils import utc_now
from app.database.database import Base


class AdvertisingBrief(Base):
    __tablename__ = "advertising_briefs"
    __table_args__ = (
        UniqueConstraint(
            "owner_user_id", "advertising_angle_id", name="uq_advertising_briefs_owner_angle"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    advertising_angle_id: Mapped[int] = mapped_column(
        ForeignKey("advertising_angles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    objective: Mapped[str | None] = mapped_column(String(500), nullable=True)
    target_audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    core_message: Mapped[str] = mapped_column(Text, nullable=False)
    copy_direction: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )


class CampaignMetricSnapshot(Base):
    __tablename__ = "campaign_metric_snapshots"
    __table_args__ = (
        Index("ix_campaign_metric_snapshots_owner_campaign_captured", "owner_user_id", "campaign_id", "captured_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    advertising_brief_id: Mapped[int | None] = mapped_column(
        ForeignKey("advertising_briefs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    metric_schema: Mapped[str] = mapped_column(String(80), nullable=False, default="campaign_metrics_v1")
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
