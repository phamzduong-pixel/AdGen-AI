"""Read-only legacy database reconciliation reports.

This module deliberately has no write path. It classifies the state inspector
output and gives an operator a dry-run recommendation; it never migrates,
stamps, repairs, deletes, or changes data.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from app.database.schema_manifest import CANONICAL_SCHEMA_MANIFEST
from app.database.schema_state import DatabaseStateReport, inspect_database_state


@dataclass(frozen=True)
class LegacyReconciliationReport:
    status: str
    source_state: str
    decision: str
    current_revisions: tuple[str, ...]
    heads: tuple[str, ...]
    schema_status: str
    future_revision_objects: dict[str, tuple[str, ...]]
    findings: tuple[Any, ...]
    recommendation: str
    automatic_changes_allowed: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def inspect_legacy_database(
    bind: Any,
    *,
    manifest: dict[str, Any] = CANONICAL_SCHEMA_MANIFEST,
    script_location: str | Path | None = None,
) -> LegacyReconciliationReport:
    """Return a dry-run reconciliation report without changing the database."""

    state = inspect_database_state(
        bind,
        manifest=manifest,
        script_location=script_location,
    )

    if state.state == "UNMANAGED_CANONICAL_SCHEMA":
        status = "SAFE_TO_REVIEW"
        recommendation = (
            "Schema is canonical but has no Alembic marker. Review data and "
            "deployment history, obtain backup/restore evidence, and approve "
            "a separate reconciliation before changing the marker."
        )
    elif state.state == "MANAGED_CANONICAL_SCHEMA":
        status = "SAFE_TO_REVIEW"
        recommendation = (
            "Database is already managed at an Alembic head; no legacy "
            "reconciliation is required."
        )
    elif state.state in {"UNMANAGED_SCHEMA_DRIFT", "MANAGED_SCHEMA_MISMATCH"}:
        status = "MISMATCH"
        recommendation = (
            "Schema drift or revision mismatch requires a reviewed repair plan; "
            "do not stamp, migrate, or modify data automatically."
        )
    else:
        status = "BLOCKED"
        recommendation = (
            "Database origin or revision state is not safely classifiable; "
            "preserve it and require manual review with backup evidence."
        )

    return LegacyReconciliationReport(
        status=status,
        source_state=state.state,
        decision=state.decision,
        current_revisions=state.current_revisions,
        heads=state.heads,
        schema_status=state.schema_status,
        future_revision_objects=state.future_revision_objects,
        findings=state.findings,
        recommendation=recommendation,
    )


def main(argv: list[str] | None = None) -> int:
    """Print a read-only reconciliation report for the configured database."""

    parser = argparse.ArgumentParser(
        description=(
            "Inspect an AdGen AI database without migrating, stamping, "
            "repairing, or changing data."
        )
    )
    parser.parse_args(argv)

    from app.database.database import engine

    print(
        json.dumps(
            inspect_legacy_database(engine).as_dict(),
            default=str,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
