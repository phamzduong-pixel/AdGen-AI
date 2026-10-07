"""Add evidence-traceable Advertising Angle persistence."""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261006_0023"
down_revision: str | None = "20261006_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "advertising_angles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("trend_report_id", sa.Integer(), nullable=False),
        sa.Column("source_claim_key", sa.String(length=160), nullable=False),
        sa.Column("source_evidence_ids_json", sa.Text(), nullable=False),
        sa.Column("trust_status", sa.String(length=40), nullable=False),
        sa.Column("trust_risk_level", sa.String(length=20), nullable=False),
        sa.Column("trust_action", sa.String(length=20), nullable=False),
        sa.Column("angle_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("wording", sa.Text(), nullable=False),
        sa.Column("source_key", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trend_report_id"], ["trend_reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_user_id", "source_key", name="uq_advertising_angles_owner_source"),
    )
    for name, columns in (
        ("ix_advertising_angles_owner_user_id", ["owner_user_id"]),
        ("ix_advertising_angles_trend_report_id", ["trend_report_id"]),
        ("ix_advertising_angles_source_claim_key", ["source_claim_key"]),
        ("ix_advertising_angles_owner_report", ["owner_user_id", "trend_report_id"]),
    ):
        op.create_index(name, "advertising_angles", columns)


def downgrade() -> None:
    op.drop_table("advertising_angles")
