"""Add durable idempotency records for conversational media edits."""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261001_0016"
down_revision: str | None = "20261001_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "media_edit_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("source_asset_id", sa.Integer(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="processing"),
        sa.Column("created_asset_ids", sa.JSON(), nullable=True),
        sa.Column("failed_operation_index", sa.Integer(), nullable=True),
        sa.Column("failed_operation", sa.String(length=50), nullable=True),
        sa.Column("output_asset_id", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["output_asset_id"], ["media_assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_asset_id"], ["media_assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "conversation_id",
            "idempotency_key",
            name="uq_media_edit_requests_scope_key",
        ),
    )
    op.create_index("ix_media_edit_requests_id", "media_edit_requests", ["id"])
    op.create_index("ix_media_edit_requests_user_id", "media_edit_requests", ["user_id"])
    op.create_index(
        "ix_media_edit_requests_conversation_id",
        "media_edit_requests",
        ["conversation_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_media_edit_requests_conversation_id", table_name="media_edit_requests")
    op.drop_index("ix_media_edit_requests_user_id", table_name="media_edit_requests")
    op.drop_index("ix_media_edit_requests_id", table_name="media_edit_requests")
    op.drop_table("media_edit_requests")