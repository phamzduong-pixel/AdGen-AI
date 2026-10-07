"""Add Trend Alert persistence."""
from typing import Sequence
from alembic import op
import sqlalchemy as sa
revision: str = "20261006_0022"
down_revision: str | None = "20261006_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
def upgrade() -> None:
    op.create_table("trend_alerts", sa.Column("id", sa.Integer(), nullable=False), sa.Column("user_id", sa.Integer(), nullable=False), sa.Column("monitor_id", sa.Integer(), nullable=False), sa.Column("snapshot_id", sa.Integer(), nullable=True), sa.Column("alert_key", sa.String(length=180), nullable=False), sa.Column("active_key", sa.String(length=180), nullable=True), sa.Column("alert_type", sa.String(length=40), nullable=False), sa.Column("status", sa.String(length=20), nullable=False), sa.Column("severity", sa.String(length=20), nullable=False), sa.Column("title", sa.String(length=300), nullable=False), sa.Column("message", sa.Text(), nullable=False), sa.Column("payload_json", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False), sa.Column("resolved_at", sa.DateTime(), nullable=True), sa.ForeignKeyConstraint(["user_id"],["users.id"],ondelete="CASCADE"), sa.ForeignKeyConstraint(["monitor_id"],["trend_monitors.id"],ondelete="CASCADE"), sa.ForeignKeyConstraint(["snapshot_id"],["trend_snapshots.id"],ondelete="SET NULL"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("active_key", name="uq_trend_alerts_active_key"))
    for name, columns in (("ix_trend_alerts_user_id",["user_id"]),("ix_trend_alerts_monitor_id",["monitor_id"]),("ix_trend_alerts_snapshot_id",["snapshot_id"]),("ix_trend_alerts_alert_key",["alert_key"]),("ix_trend_alerts_user_created",["user_id","created_at"])): op.create_index(name,"trend_alerts",columns)
def downgrade() -> None: op.drop_table("trend_alerts")
