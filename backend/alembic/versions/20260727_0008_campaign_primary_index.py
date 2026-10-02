"""Add unique index for campaign primary content document.

Revision ID: 20260727_0008
Revises: 20260727_0007
Create Date: 2026-09-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260727_0008"
down_revision: Union[str, None] = "20260727_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("content_documents", schema=None) as batch_op:
        batch_op.create_index(
            "uq_content_documents_campaign_primary",
            ["campaign_id"],
            unique=True,
            sqlite_where=sa.text("is_campaign_primary = 1 AND campaign_id IS NOT NULL"),
            postgresql_where=sa.text("is_campaign_primary AND campaign_id IS NOT NULL"),
        )


def downgrade() -> None:
    with op.batch_alter_table("content_documents", schema=None) as batch_op:
        batch_op.drop_index(
            "uq_content_documents_campaign_primary",
            sqlite_where=sa.text("is_campaign_primary = 1 AND campaign_id IS NOT NULL"),
            postgresql_where=sa.text("is_campaign_primary AND campaign_id IS NOT NULL"),
        )
