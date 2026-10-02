"""Add brand profiles and safe nullable links to generated content.

Revision ID: 20260727_0006
Revises: 20260727_0005
Create Date: 2026-07-27
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

from app.models.brand import BrandAsset, BrandContentCheck, BrandProfile


revision: str = "20260727_0006"
down_revision: str | None = "20260727_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _add_brand_link(table_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    if "brand_id" not in columns:
        with op.batch_alter_table(table_name) as batch:
            batch.add_column(sa.Column("brand_id", sa.Integer(), nullable=True))
            batch.create_foreign_key(
                f"fk_{table_name}_brand_id",
                "brand_profiles",
                ["brand_id"],
                ["id"],
                ondelete="SET NULL",
            )
            batch.create_index(
                f"ix_{table_name}_brand_id",
                ["brand_id"],
                unique=False,
            )


def upgrade() -> None:
    bind = op.get_bind()
    tables = sa.inspect(bind).get_table_names()
    if "brand_profiles" not in tables:
        BrandProfile.__table__.create(bind=bind)
    tables = sa.inspect(bind).get_table_names()
    if "brand_assets" not in tables:
        BrandAsset.__table__.create(bind=bind)
    if "brand_content_checks" not in tables:
        BrandContentCheck.__table__.create(bind=bind)

    for table_name in ("conversations", "messages", "saved_contents", "campaigns"):
        _add_brand_link(table_name)


def downgrade() -> None:
    # Preserve brand data and content associations during operational rollback.
    pass
