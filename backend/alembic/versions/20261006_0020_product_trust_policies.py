"""Add Product Trust source policies and persisted report snapshots."""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261006_0020"
down_revision: str | None = "20261005_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("trend_reports", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "product_trust_json",
                sa.Text(),
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )
        batch_op.alter_column("product_trust_json", server_default=None)

    op.create_table(
        "evidence_source_policies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "host",
            name="uq_evidence_source_policies_user_host",
        ),
    )
    op.create_index(
        "ix_evidence_source_policies_id",
        "evidence_source_policies",
        ["id"],
    )
    op.create_index(
        "ix_evidence_source_policies_user_id",
        "evidence_source_policies",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_evidence_source_policies_user_id",
        table_name="evidence_source_policies",
    )
    op.drop_index(
        "ix_evidence_source_policies_id",
        table_name="evidence_source_policies",
    )
    op.drop_table("evidence_source_policies")
    with op.batch_alter_table("trend_reports", schema=None) as batch_op:
        batch_op.drop_column("product_trust_json")
