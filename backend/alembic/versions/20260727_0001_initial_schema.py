"""Create the current AdGen AI schema without removing existing data.

Revision ID: 20260727_0001
Revises:
Create Date: 2026-07-27
"""

from typing import Sequence

from alembic import op

from app.database.database import Base
import app.models  # noqa: F401


revision: str = "20260727_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # checkfirst=True makes this safe for the existing local SQLite demo DB,
    # while creating the complete schema on a new PostgreSQL database.
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    # Downgrade is intentionally non-destructive for this baseline revision.
    # Public demo data must never be dropped implicitly.
    pass
