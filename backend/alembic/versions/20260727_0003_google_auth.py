"""Add Google authentication metadata without replacing existing users.

Revision ID: 20260727_0003
Revises: 20260727_0002
Create Date: 2026-07-27
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260727_0003"
down_revision: str | None = "20260727_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}

    if "auth_provider" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "auth_provider",
                sa.String(length=20),
                nullable=False,
                server_default="local",
            ),
        )
    if "google_sub" not in columns:
        op.add_column(
            "users",
            sa.Column("google_sub", sa.String(length=255), nullable=True),
        )
    if "avatar_url" not in columns:
        op.add_column(
            "users",
            sa.Column("avatar_url", sa.String(length=500), nullable=True),
        )
    if "email_verified" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "email_verified",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )

    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("users")}
    if "ix_users_google_sub" not in indexes:
        op.create_index(
            "ix_users_google_sub",
            "users",
            ["google_sub"],
            unique=True,
        )


def downgrade() -> None:
    # Authentication metadata is deliberately retained so account links cannot
    # be silently lost during an operational rollback.
    pass
