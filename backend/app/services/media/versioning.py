"""Concurrency-safe MediaAsset version allocation."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.media_asset import MediaAsset


MAX_VERSION_ALLOCATION_RETRIES = 3


def resolve_root_asset_id(db: Session, source: MediaAsset) -> int:
    """Resolve the root without changing parent_asset_id semantics."""

    if source.root_asset_id:
        root = db.get(MediaAsset, source.root_asset_id)
        if root and (
            root.user_id,
            root.conversation_id,
            root.kind,
        ) == (source.user_id, source.conversation_id, source.kind):
            return root.id

    current = source
    seen: set[int] = set()
    while current.parent_asset_id is not None:
        if current.id in seen:
            raise RuntimeError("MediaAsset lineage contains a cycle")
        seen.add(current.id)
        parent = db.get(MediaAsset, current.parent_asset_id)
        if parent is None:
            raise RuntimeError("MediaAsset lineage contains a missing parent")
        if (
            parent.user_id,
            parent.conversation_id,
            parent.kind,
        ) != (source.user_id, source.conversation_id, source.kind):
            raise RuntimeError("MediaAsset lineage crosses ownership scope")
        current = parent
    return current.id


def next_media_version_number(db: Session, source: MediaAsset) -> int:
    """Return the next number in the source asset's root lineage."""

    root_id = resolve_root_asset_id(db, source)
    if source.root_asset_id:
        latest = (
            db.query(MediaAsset.version_number)
            .filter(
                MediaAsset.user_id == source.user_id,
                MediaAsset.conversation_id == source.conversation_id,
                MediaAsset.kind == source.kind,
                MediaAsset.root_asset_id == root_id,
            )
            .order_by(MediaAsset.version_number.desc())
            .first()
        )
        if latest:
            return latest[0] + 1

    # Compatibility fallback for legacy rows before the backfill migration.
    rows = (
        db.query(
            MediaAsset.id,
            MediaAsset.parent_asset_id,
            MediaAsset.version_number,
        )
        .filter(
            MediaAsset.user_id == source.user_id,
            MediaAsset.conversation_id == source.conversation_id,
            MediaAsset.kind == source.kind,
        )
        .all()
    )
    by_id = {row.id: (row.parent_asset_id, row.version_number) for row in rows}
    lineage_ids = {root_id}
    changed = True
    while changed:
        changed = False
        for asset_id, (parent_id, _) in by_id.items():
            if parent_id in lineage_ids and asset_id not in lineage_ids:
                lineage_ids.add(asset_id)
                changed = True
    numbers = [by_id[asset_id][1] for asset_id in lineage_ids if asset_id in by_id]
    return max(numbers or [source.version_number]) + 1


def is_version_conflict(error: IntegrityError) -> bool:
    """Only classify the media lineage unique constraint as retryable."""

    message = str(error).lower()
    return (
        "uq_media_assets_lineage_version" in message
        or (
            "media_assets" in message
            and "version_number" in message
            and ("unique" in message or "duplicate" in message)
        )
    )


def create_versioned_asset(
    db: Session,
    source: MediaAsset,
    build_asset: Callable[[int, int], MediaAsset],
) -> MediaAsset:
    """Insert a version and retry only a lineage unique conflict."""

    for attempt in range(MAX_VERSION_ALLOCATION_RETRIES):
        current_source = db.get(MediaAsset, source.id) or source
        root_id = resolve_root_asset_id(db, current_source)
        version_number = next_media_version_number(db, current_source)
        asset = build_asset(root_id, version_number)
        db.add(asset)
        try:
            db.commit()
            db.refresh(asset)
            return asset
        except IntegrityError as error:
            db.rollback()
            if not is_version_conflict(error) or attempt == MAX_VERSION_ALLOCATION_RETRIES - 1:
                raise

    raise RuntimeError("MediaAsset version allocation exhausted retries")