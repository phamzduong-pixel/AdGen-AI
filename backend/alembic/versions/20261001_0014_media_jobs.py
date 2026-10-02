"""Add asynchronous media generation jobs.

Revision ID: 20261001_0014
Revises: 20261001_0013
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261001_0014"
down_revision: str | None = "20261001_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "media_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("aspect_ratio", sa.String(length=10), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("source_asset_ids", sa.JSON(), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_model", sa.String(length=100), nullable=True),
        sa.Column("provider_job_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("output_asset_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["output_asset_id"], ["media_assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_media_jobs_id", "media_jobs", ["id"])
    op.create_index("ix_media_jobs_user_id", "media_jobs", ["user_id"])
    op.create_index("ix_media_jobs_conversation_id", "media_jobs", ["conversation_id"])
    op.create_index("ix_media_jobs_provider_job_id", "media_jobs", ["provider_job_id"])


def downgrade() -> None:
    op.drop_index("ix_media_jobs_provider_job_id", table_name="media_jobs")
    op.drop_index("ix_media_jobs_conversation_id", table_name="media_jobs")
    op.drop_index("ix_media_jobs_user_id", table_name="media_jobs")
    op.drop_index("ix_media_jobs_id", table_name="media_jobs")
    op.drop_table("media_jobs")
