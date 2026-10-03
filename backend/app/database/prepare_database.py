"""Prepare a database for runtime without repairing existing databases."""

from __future__ import annotations

import argparse
import json

from app.database.bootstrap import bootstrap_database
from app.database.database import DatabaseStartupBlocked, engine
from app.database.schema_state import inspect_database_state


def prepare_database() -> dict:
    """Bootstrap only a truly empty database; reject every other mismatch."""
    state = inspect_database_state(engine)
    if state.state == "EMPTY_UNMANAGED":
        result = bootstrap_database(engine)
        return {
            "action": "bootstrapped_empty_database",
            "state": result.state.state,
            "revision": result.state.current_revisions,
        }
    if state.state == "MANAGED_CANONICAL_SCHEMA":
        return {
            "action": "validated_existing_database",
            "state": state.state,
            "revision": state.current_revisions,
        }
    raise DatabaseStartupBlocked(
        "Database preparation refused to mutate this database: "
        f"state={state.state}; decision={state.decision}; reason={state.reason}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap only an empty database and validate existing managed schemas."
    )
    parser.parse_args(argv)
    print(json.dumps(prepare_database(), default=str, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())