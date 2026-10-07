from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.datetime_utils import utc_now
from app.database.database import Base


class AdvertisingAngle(Base):
    """A deterministic, evidence-traceable advertising angle from a Trend Report."""

    __tablename__ = "advertising_angles"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "source_key", name="uq_advertising_angles_owner_source"),
        Index("ix_advertising_angles_owner_report", "owner_user_id", "trend_report_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    trend_report_id: Mapped[int] = mapped_column(
        ForeignKey("trend_reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_claim_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    source_evidence_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    trust_status: Mapped[str] = mapped_column(String(40), nullable=False)
    trust_risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    trust_action: Mapped[str] = mapped_column(String(20), nullable=False)
    angle_type: Mapped[str] = mapped_column(String(40), nullable=False, default="evidence_led")
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    wording: Mapped[str] = mapped_column(Text, nullable=False)
    source_key: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )
