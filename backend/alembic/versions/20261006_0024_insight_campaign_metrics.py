"""Add Insight-to-Brief/Campaign provenance and metric snapshots."""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261006_0024"
down_revision: str | None = "20261006_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "advertising_briefs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("advertising_angle_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("objective", sa.String(length=500), nullable=True),
        sa.Column("target_audience", sa.Text(), nullable=True),
        sa.Column("core_message", sa.Text(), nullable=False),
        sa.Column("copy_direction", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["advertising_angle_id"], ["advertising_angles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_user_id", "advertising_angle_id", name="uq_advertising_briefs_owner_angle"),
    )
    op.create_index("ix_advertising_briefs_owner_user_id", "advertising_briefs", ["owner_user_id"])
    op.create_index("ix_advertising_briefs_advertising_angle_id", "advertising_briefs", ["advertising_angle_id"])

    with op.batch_alter_table("campaigns") as batch:
        batch.add_column(sa.Column("advertising_brief_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_campaigns_advertising_brief_id", "advertising_briefs", ["advertising_brief_id"], ["id"], ondelete="SET NULL")
        batch.create_unique_constraint("uq_campaigns_user_advertising_brief", ["user_id", "advertising_brief_id"])
        batch.create_index("ix_campaigns_advertising_brief_id", ["advertising_brief_id"])

    op.create_table(
        "campaign_metric_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("advertising_brief_id", sa.Integer(), nullable=True),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
        sa.Column("metric_schema", sa.String(length=80), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["advertising_brief_id"], ["advertising_briefs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, columns in (
        ("ix_campaign_metric_snapshots_owner_user_id", ["owner_user_id"]),
        ("ix_campaign_metric_snapshots_campaign_id", ["campaign_id"]),
        ("ix_campaign_metric_snapshots_advertising_brief_id", ["advertising_brief_id"]),
        ("ix_campaign_metric_snapshots_owner_campaign_captured", ["owner_user_id", "campaign_id", "captured_at"]),
    ):
        op.create_index(name, "campaign_metric_snapshots", columns)


def downgrade() -> None:
    op.drop_table("campaign_metric_snapshots")
    with op.batch_alter_table("campaigns") as batch:
        batch.drop_index("ix_campaigns_advertising_brief_id")
        batch.drop_constraint("uq_campaigns_user_advertising_brief", type_="unique")
        batch.drop_constraint("fk_campaigns_advertising_brief_id", type_="foreignkey")
        batch.drop_column("advertising_brief_id")
    op.drop_table("advertising_briefs")
