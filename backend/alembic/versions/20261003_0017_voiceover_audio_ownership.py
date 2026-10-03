"""Add ownership metadata for protected voiceover audio files."""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261003_0017"
down_revision: str | None = "20261001_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "voiceover_audios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("audio_id", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_seconds", sa.Float(), nullable=False, server_default="0"),
        sa.Column("voice_id", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("audio_id"),
        sa.UniqueConstraint("filename"),
    )
    op.create_index("ix_voiceover_audios_id", "voiceover_audios", ["id"])
    op.create_index("ix_voiceover_audios_user_id", "voiceover_audios", ["user_id"])
    op.create_index("ix_voiceover_audios_message_id", "voiceover_audios", ["message_id"])


def downgrade() -> None:
    op.drop_index("ix_voiceover_audios_message_id", table_name="voiceover_audios")
    op.drop_index("ix_voiceover_audios_user_id", table_name="voiceover_audios")
    op.drop_index("ix_voiceover_audios_id", table_name="voiceover_audios")
    op.drop_table("voiceover_audios")