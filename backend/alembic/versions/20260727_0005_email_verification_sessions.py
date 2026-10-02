"""Add email verification and revocable login sessions.

Revision ID: 20260727_0005
Revises: 20260727_0004
Create Date: 2026-07-27
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

from app.models.email_verification import EmailVerificationToken
from app.models.user_session import UserSession


revision: str = "20260727_0005"
down_revision: str | None = "20260727_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = inspector.get_table_names()

    # Accounts created before email verification existed must remain usable.
    if "users" in table_names:
        bind.execute(
            sa.text(
                "UPDATE users SET email_verified = 1 "
                "WHERE auth_provider = 'local' AND email_verified = 0"
            )
        )
    if "email_verification_tokens" not in table_names:
        EmailVerificationToken.__table__.create(bind=bind)
    if "user_sessions" not in table_names:
        UserSession.__table__.create(bind=bind)


def downgrade() -> None:
    # Security audit records and account verification state are retained.
    pass
