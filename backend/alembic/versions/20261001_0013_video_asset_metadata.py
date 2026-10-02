"""Add deterministic video operation metadata to media assets.

Revision ID: 20261001_0013
Revises: 20260727_0012
"""

from alembic import op
import sqlalchemy as sa


revision = "20261001_0013"
down_revision = "20260727_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("media_assets", sa.Column("operation_params", sa.JSON(), nullable=True))
    op.add_column("media_assets", sa.Column("duration_seconds", sa.Float(), nullable=True))
    op.add_column("media_assets", sa.Column("width", sa.Integer(), nullable=True))
    op.add_column("media_assets", sa.Column("height", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("media_assets", "height")
    op.drop_column("media_assets", "width")
    op.drop_column("media_assets", "duration_seconds")
    op.drop_column("media_assets", "operation_params")
