"""Add independent content editor documents and immutable versions.

Revision ID: 20260727_0007
Revises: 20260727_0006
Create Date: 2026-07-27
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

from app.models.content_document import ContentDocument, ContentVersion


revision: str = "20260727_0007"
down_revision: str | None = "20260727_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "content_documents" not in tables:
        ContentDocument.__table__.create(bind=bind)
    tables = set(sa.inspect(bind).get_table_names())
    if "content_versions" not in tables:
        ContentVersion.__table__.create(bind=bind)


def downgrade() -> None:
    # Version history is user-authored data. Operational rollback keeps it intact.
    pass
