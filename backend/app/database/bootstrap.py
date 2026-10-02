"""Explicit, validated bootstrap for a genuinely empty database.

This module is intentionally separate from application startup. It never
upgrades, stamps, repairs, or reclassifies an existing database. The caller
must invoke it explicitly against a database that the state inspector proves
is empty and unmanaged.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from typing import Any

from sqlalchemy import text

from app.database.database import Base
from app.database.schema_manifest import CANONICAL_SCHEMA_MANIFEST
from app.database.schema_state import DatabaseStateReport, inspect_database_state
from app.database.schema_validator import compare_manifest_to_models, validate_schema


class DatabaseBootstrapRejected(RuntimeError):
    """Raised when explicit bootstrap cannot prove the database is safe."""


@dataclass(frozen=True)
class BootstrapResult:
    """Evidence returned after a successful schema bootstrap."""

    state: DatabaseStateReport


def bootstrap_database(
    bind: Any,
    *,
    manifest: dict[str, Any] = CANONICAL_SCHEMA_MANIFEST,
) -> BootstrapResult:
    """Create and validate schema only on an empty, unmanaged database.

    ``bind`` must be a SQLAlchemy Engine so DDL and marker creation use one
    controlled connection. The marker is written only after validation. Some
    dialects do not roll back DDL after a mid-bootstrap failure; in that case
    the marker is still absent and the resulting partial database remains
    blocked for explicit reconciliation.
    """

    import app.models  # noqa: F401  # populate Base.metadata before create_all

    model_findings = compare_manifest_to_models(manifest)
    if model_findings:
        raise DatabaseBootstrapRejected(
            "Bootstrap manifest does not match the current model contract; "
            "no DDL was run."
        )

    initial = inspect_database_state(bind, manifest=manifest)
    if initial.state != "EMPTY_UNMANAGED":
        raise DatabaseBootstrapRejected(
            "Bootstrap requires EMPTY_UNMANAGED; "
            f"observed state={initial.state}, decision={initial.decision}."
        )
    if not hasattr(bind, "begin") or not hasattr(bind, "connect"):
        raise DatabaseBootstrapRejected(
            "Bootstrap requires a SQLAlchemy Engine so DDL and marker creation "
            "can be committed atomically."
        )

    try:
        with bind.begin() as connection:
            Base.metadata.create_all(bind=connection)

            schema_report = validate_schema(
                connection,
                manifest=manifest,
                compare_models=True,
            )
            if schema_report.status != "PASS":
                raise DatabaseBootstrapRejected(
                    "Bootstrap schema validation failed; the Alembic marker was not "
                    f"created (status={schema_report.status})."
                )

            verified = inspect_database_state(connection, manifest=manifest)
            if verified.state != "UNMANAGED_CANONICAL_SCHEMA":
                raise DatabaseBootstrapRejected(
                    "Bootstrap validation produced an unexpected state: "
                    f"{verified.state}."
                )
            if len(verified.heads) != 1:
                raise DatabaseBootstrapRejected(
                    "Bootstrap requires exactly one Alembic head; "
                    f"observed heads={verified.heads}."
                )

            connection.execute(
                text(
                    "CREATE TABLE alembic_version ("
                    "version_num VARCHAR(32) NOT NULL"
                    ")"
                )
            )
            connection.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
                {"revision": verified.heads[0]},
            )
    except DatabaseBootstrapRejected:
        raise
    except Exception as exc:
        raise DatabaseBootstrapRejected(
            "Bootstrap failed before a revision marker could be written; "
            f"database state must remain blocked ({type(exc).__name__})."
        ) from exc

    final = inspect_database_state(bind, manifest=manifest)
    if final.state != "MANAGED_CANONICAL_SCHEMA":
        raise DatabaseBootstrapRejected(
            "Bootstrap committed, but the final read-only state check failed: "
            f"{final.state}."
        )
    return BootstrapResult(state=final)


def main(argv: list[str] | None = None) -> int:
    """Run the deliberately explicit empty-database bootstrap workflow."""

    parser = argparse.ArgumentParser(
        description=(
            "Bootstrap only an EMPTY_UNMANAGED AdGen AI database. "
            "The command never repairs or stamps an existing database."
        )
    )
    parser.add_argument(
        "--confirm-empty",
        action="store_true",
        help="confirm that the configured database is disposable and empty",
    )
    args = parser.parse_args(argv)
    if not args.confirm_empty:
        parser.error(
            "--confirm-empty is required; inspect existing databases with "
            "app.database.legacy_reconciliation instead."
        )

    # Importing the configured engine here keeps library usage side-effect free
    # and avoids printing a connection URL (which can contain credentials).
    from app.database.database import engine

    result = bootstrap_database(engine)
    print(
        json.dumps(
            {
                "state": result.state.state,
                "revision": result.state.current_revisions,
                "schema_status": result.state.schema_status,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
