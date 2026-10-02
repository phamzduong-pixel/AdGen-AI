"""Store custom platform names without changing legacy values.

Revision ID: 20260727_0009
Revises: 20260727_0008
Create Date: 2026-09-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260727_0009"
down_revision: Union[str, None] = "20260727_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ("messages", "saved_contents", "ad_templates", "content_documents"):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(sa.Column("platform_name", sa.String(length=80), nullable=True))


def downgrade() -> None:
    for table in ("messages", "saved_contents", "ad_templates", "content_documents"):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_column("platform_name")