from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.datetime_utils import utc_now
from app.database.database import Base

class TrendAlert(Base):
    __tablename__ = "trend_alerts"
    __table_args__ = (UniqueConstraint("active_key", name="uq_trend_alerts_active_key"), Index("ix_trend_alerts_user_created", "user_id", "created_at"))
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    monitor_id: Mapped[int] = mapped_column(ForeignKey("trend_monitors.id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("trend_snapshots.id", ondelete="SET NULL"), nullable=True, index=True)
    alert_key: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    active_key: Mapped[str | None] = mapped_column(String(180), nullable=True)
    alert_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="new")
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
