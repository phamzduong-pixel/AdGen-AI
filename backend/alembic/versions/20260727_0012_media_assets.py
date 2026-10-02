"""Add generated media assets and version metadata."""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260727_0012"
down_revision: str | None = "20260727_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("parent_asset_id", sa.Integer(), nullable=True),
        sa.Column("source_uploaded_file_id", sa.Integer(), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="image"),
        sa.Column("operation", sa.String(length=20), nullable=False, server_default="generate"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="processing"),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("aspect_ratio", sa.String(length=10), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("filepath", sa.String(length=1000), nullable=True),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_asset_id"], ["media_assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_uploaded_file_id"], ["uploaded_files.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_media_assets_id", "media_assets", ["id"])
    op.create_index("ix_media_assets_user_id", "media_assets", ["user_id"])
    op.create_index("ix_media_assets_conversation_id", "media_assets", ["conversation_id"])
    op.create_index("ix_media_assets_parent_asset_id", "media_assets", ["parent_asset_id"])


def downgrade() -> None:
    op.drop_index("ix_media_assets_parent_asset_id", table_name="media_assets")
    op.drop_index("ix_media_assets_conversation_id", table_name="media_assets")
    op.drop_index("ix_media_assets_user_id", table_name="media_assets")
    op.drop_index("ix_media_assets_id", table_name="media_assets")
    op.drop_table("media_assets")
