from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.datetime_utils import utc_now
from app.database.database import Base


class TrendMonitor(Base):
    __tablename__ = "trend_monitors"
    __table_args__ = (
        UniqueConstraint("user_id", "monitor_key", name="uq_trend_monitors_user_key"),
        UniqueConstraint("user_id", "trend_report_id", name="uq_trend_monitors_user_report"),
        Index("ix_trend_monitors_user_due", "user_id", "enabled", "next_run_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    monitor_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    trend_report_id: Mapped[int | None] = mapped_column(ForeignKey("trend_reports.id", ondelete="SET NULL"), nullable=True, index=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    cadence_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=1440)
    timezone: Mapped[str] = mapped_column(String(80), nullable=False, default="UTC")
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    snapshots = relationship("TrendSnapshot", back_populates="monitor", cascade="all, delete-orphan", order_by="TrendSnapshot.captured_at")


class TrendSnapshot(Base):
    __tablename__ = "trend_snapshots"
    __table_args__ = (
        UniqueConstraint("monitor_id", "run_key", name="uq_trend_snapshots_monitor_run_key"),
        Index("ix_trend_snapshots_monitor_captured", "monitor_id", "captured_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    monitor_id: Mapped[int] = mapped_column(ForeignKey("trend_monitors.id", ondelete="CASCADE"), nullable=False, index=True)
    run_key: Mapped[str] = mapped_column(String(80), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="success")
    provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    freshness_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)

    monitor = relationship("TrendMonitor", back_populates="snapshots")
