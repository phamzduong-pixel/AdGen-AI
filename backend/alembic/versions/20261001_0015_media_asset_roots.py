"""Add explicit media lineage roots and protect version allocation.

This migration deliberately aborts when legacy lineage data is unsafe. It does
not repair missing parents, cycles, scope crossings, or duplicate versions.
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261001_0015"
down_revision: str | None = "20261001_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT_NAME = "uq_media_assets_lineage_version"


def _resolve_roots(rows):
    by_id = {row["id"]: row for row in rows}
    roots = {}
    for row in rows:
        current_id = row["id"]
        seen = set()
        while True:
            if current_id in seen:
                raise RuntimeError("Cannot backfill media asset roots: lineage cycle")
            seen.add(current_id)
            current = by_id.get(current_id)
            if current is None:
                raise RuntimeError("Cannot backfill media asset roots: missing asset")
            parent_id = current["parent_asset_id"]
            if parent_id is None:
                roots[row["id"]] = current_id
                break
            parent = by_id.get(parent_id)
            if parent is None:
                raise RuntimeError("Cannot backfill media asset roots: missing parent")
            scope = (row["user_id"], row["conversation_id"], row["kind"])
            parent_scope = (parent["user_id"], parent["conversation_id"], parent["kind"])
            if scope != parent_scope:
                raise RuntimeError("Cannot backfill media asset roots: scope crossing")
            current_id = parent_id
    return roots


def upgrade() -> None:
    with op.batch_alter_table("media_assets") as batch:
        batch.add_column(sa.Column("root_asset_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_media_assets_root_asset_id",
            "media_assets",
            ["root_asset_id"],
            ["id"],
            ondelete="SET NULL",
        )

    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, user_id, conversation_id, kind, parent_asset_id, "
            "root_asset_id, version_number FROM media_assets"
        )
    ).mappings().all()
    roots = _resolve_roots(rows)

    for row in rows:
        existing_root = row["root_asset_id"]
        root_id = roots[row["id"]]
        if existing_root is not None and existing_root != root_id:
            raise RuntimeError("Cannot backfill media asset roots: inconsistent root")
        if existing_root is None:
            connection.execute(
                sa.text(
                    "UPDATE media_assets SET root_asset_id = :root_id "
                    "WHERE id = :asset_id"
                ),
                {"root_id": root_id, "asset_id": row["id"]},
            )

    seen = {}
    for row in rows:
        key = (
            row["user_id"],
            row["conversation_id"],
            row["kind"],
            roots[row["id"]],
            row["version_number"],
        )
        if key in seen:
            raise RuntimeError(
                "Cannot protect media asset versions: duplicate lineage version "
                f"for assets {seen[key]} and {row['id']}"
            )
        seen[key] = row["id"]

    with op.batch_alter_table("media_assets") as batch:
        batch.create_unique_constraint(
            CONSTRAINT_NAME,
            ["user_id", "conversation_id", "kind", "root_asset_id", "version_number"],
        )


def downgrade() -> None:
    with op.batch_alter_table("media_assets") as batch:
        batch.drop_constraint(CONSTRAINT_NAME, type_="unique")
        batch.drop_column("root_asset_id")