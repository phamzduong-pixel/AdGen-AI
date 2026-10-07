"""Add structured source statuses to Trend Reports."""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261005_0019"
down_revision: str | None = "20261005_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("trend_reports", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "source_statuses_json",
                sa.Text(),
                nullable=False,
                server_default=sa.text("'[]'"),
            )
        )
        batch_op.alter_column("source_statuses_json", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("trend_reports", schema=None) as batch_op:
        batch_op.drop_column("source_statuses_json")