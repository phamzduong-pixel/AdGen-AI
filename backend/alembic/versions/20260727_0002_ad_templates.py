"""Add advertisement templates and per-user favorites.

Revision ID: 20260727_0002
Revises: 20260727_0001
Create Date: 2026-07-27
"""

from typing import Sequence

from alembic import op

from app.models.ad_template import AdTemplate
from app.models.ad_template import TemplateFavorite


revision: str = "20260727_0002"
down_revision: str | None = "20260727_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    AdTemplate.__table__.create(bind=bind, checkfirst=True)
    TemplateFavorite.__table__.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    # Keep user-created templates and favorites unless an operator explicitly
    # performs a reviewed data migration.
    pass
