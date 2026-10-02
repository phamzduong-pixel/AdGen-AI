"""Add one-time password reset records without changing existing users.

Revision ID: 20260727_0004
Revises: 20260727_0003
Create Date: 2026-07-27
"""

from typing import Sequence

from alembic import op
from sqlalchemy import inspect

from app.models.password_reset import PasswordResetToken


revision: str = "20260727_0004"
down_revision: str | None = "20260727_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if "password_reset_tokens" not in inspect(bind).get_table_names():
        PasswordResetToken.__table__.create(bind=bind)


def downgrade() -> None:
    # Preserve audit/security records unless an operator explicitly removes them.
    pass
