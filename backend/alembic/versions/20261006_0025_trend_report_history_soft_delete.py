"""Preserve Trend Report provenance when users clean up history."""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261006_0025"
down_revision: str | None = "20261006_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("trend_reports", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.create_index("ix_trend_reports_deleted_at", "trend_reports", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_trend_reports_deleted_at", table_name="trend_reports")
    op.drop_column("trend_reports", "deleted_at")
