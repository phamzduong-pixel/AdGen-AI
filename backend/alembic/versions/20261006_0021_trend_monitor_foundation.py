"""Add Trend Monitor and Snapshot data foundation."""
from typing import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "20261006_0021"
down_revision: str | None = "20261006_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.create_table("trend_monitors", sa.Column("id", sa.Integer(), nullable=False), sa.Column("monitor_key", sa.String(length=64), nullable=False), sa.Column("user_id", sa.Integer(), nullable=False), sa.Column("trend_report_id", sa.Integer(), nullable=True), sa.Column("query", sa.Text(), nullable=False), sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")), sa.Column("cadence_minutes", sa.Integer(), nullable=False, server_default=sa.text("1440")), sa.Column("timezone", sa.String(length=80), nullable=False, server_default=sa.text("'UTC'")), sa.Column("next_run_at", sa.DateTime(), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False), sa.ForeignKeyConstraint(["trend_report_id"], ["trend_reports.id"], ondelete="SET NULL"), sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("user_id", "monitor_key", name="uq_trend_monitors_user_key"), sa.UniqueConstraint("user_id", "trend_report_id", name="uq_trend_monitors_user_report"))
    for name, columns in (("ix_trend_monitors_monitor_key", ["monitor_key"]), ("ix_trend_monitors_user_id", ["user_id"]), ("ix_trend_monitors_trend_report_id", ["trend_report_id"]), ("ix_trend_monitors_next_run_at", ["next_run_at"]), ("ix_trend_monitors_user_due", ["user_id", "enabled", "next_run_at"])): op.create_index(name, "trend_monitors", columns)
    op.create_table("trend_snapshots", sa.Column("id", sa.Integer(), nullable=False), sa.Column("monitor_id", sa.Integer(), nullable=False), sa.Column("run_key", sa.String(length=80), nullable=False), sa.Column("captured_at", sa.DateTime(), nullable=False), sa.Column("status", sa.String(length=32), nullable=False), sa.Column("provider", sa.String(length=80), nullable=True), sa.Column("freshness_status", sa.String(length=40), nullable=True), sa.Column("payload_json", sa.Text(), nullable=False), sa.Column("error_message", sa.Text(), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False), sa.ForeignKeyConstraint(["monitor_id"], ["trend_monitors.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("monitor_id", "run_key", name="uq_trend_snapshots_monitor_run_key"))
    for name, columns in (("ix_trend_snapshots_monitor_id", ["monitor_id"]), ("ix_trend_snapshots_monitor_captured", ["monitor_id", "captured_at"])): op.create_index(name, "trend_snapshots", columns)

def downgrade() -> None:
    op.drop_table("trend_snapshots")
    op.drop_table("trend_monitors")
