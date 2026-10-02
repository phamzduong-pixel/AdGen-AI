"""Read-only comparison of a database schema with the canonical manifest."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text, inspect
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.schema import CheckConstraint, ForeignKeyConstraint, PrimaryKeyConstraint, UniqueConstraint

from app.database.schema_manifest import CANONICAL_SCHEMA_MANIFEST


@dataclass(frozen=True)
class SchemaFinding:
    code: str
    severity: str
    object_type: str
    object_name: str
    expected: Any = None
    observed: Any = None
    message: str = ""


@dataclass(frozen=True)
class SchemaValidationReport:
    status: str
    dialect: str
    findings: tuple[SchemaFinding, ...]

    @property
    def is_pass(self) -> bool:
        return self.status == "PASS"

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "dialect": self.dialect,
            "findings": [asdict(item) for item in self.findings],
        }


def validate_schema(
    bind: Any,
    *,
    manifest: dict[str, Any] = CANONICAL_SCHEMA_MANIFEST,
    compare_models: bool = True,
) -> SchemaValidationReport:
    """Inspect *bind* without issuing any DDL or DML.

    ``bind`` may be a SQLAlchemy Engine or Connection.  The function only
    calls SQLAlchemy Inspector methods and, optionally, compares the manifest
    with the imported model metadata.  It never runs Alembic and never writes
    to the database.
    """

    inspector = inspect(bind)
    dialect = getattr(getattr(bind, "dialect", None), "name", None)
    if dialect is None:
        dialect = getattr(getattr(inspector, "bind", None), "dialect", None)
        dialect = getattr(dialect, "name", "unknown")
    dialect = _normalize_dialect(dialect)
    findings: list[SchemaFinding] = []

    expected_tables = set(manifest["tables"])
    allowed_tables = set(manifest.get("allowed_control_tables", []))
    actual_tables = set(inspector.get_table_names())

    for table_name in sorted(expected_tables - actual_tables):
        findings.append(_finding("MISSING_TABLE", "mismatch", "table", table_name))
    for table_name in sorted(actual_tables - expected_tables - allowed_tables):
        findings.append(_finding("EXTRA_TABLE", "mismatch", "table", table_name))

    for table_name in sorted(expected_tables & actual_tables):
        expected = manifest["tables"][table_name]
        _compare_columns(inspector, table_name, expected, findings)
        _compare_primary_key(inspector, table_name, expected, findings)
        _compare_foreign_keys(inspector, table_name, expected, findings)
        _compare_unique_constraints(inspector, table_name, expected, findings)
        _compare_indexes(inspector, table_name, expected, dialect, findings)
        _compare_checks(inspector, table_name, expected, findings)

    if compare_models:
        findings.extend(compare_manifest_to_models(manifest))

    if any(item.severity == "mismatch" for item in findings):
        status = "MISMATCH"
    elif any(item.severity == "unsupported" for item in findings):
        status = "UNSUPPORTED"
    else:
        status = "PASS"
    return SchemaValidationReport(status, dialect, tuple(findings))


def compare_manifest_to_models(
    manifest: dict[str, Any] = CANONICAL_SCHEMA_MANIFEST,
) -> list[SchemaFinding]:
    """Compare the independent manifest with current SQLAlchemy metadata."""

    from app.database.database import Base
    import app.models  # noqa: F401  # populate Base.metadata

    findings: list[SchemaFinding] = []
    expected_tables = set(manifest["tables"])
    model_tables = set(Base.metadata.tables)
    for table_name in sorted(expected_tables - model_tables):
        findings.append(_finding("MODEL_MISSING_TABLE", "mismatch", "model.table", table_name))
    for table_name in sorted(model_tables - expected_tables):
        findings.append(_finding("MODEL_EXTRA_TABLE", "mismatch", "model.table", table_name))

    for table_name in sorted(expected_tables & model_tables):
        expected = manifest["tables"][table_name]
        table = Base.metadata.tables[table_name]
        expected_columns = expected["columns"]
        model_columns = {column.name: column for column in table.columns}
        for column_name in sorted(set(expected_columns) - set(model_columns)):
            findings.append(_finding("MODEL_MISSING_COLUMN", "mismatch", "model.column", f"{table_name}.{column_name}"))
        for column_name in sorted(set(model_columns) - set(expected_columns)):
            findings.append(_finding("MODEL_EXTRA_COLUMN", "mismatch", "model.column", f"{table_name}.{column_name}"))
        for column_name in sorted(set(expected_columns) & set(model_columns)):
            expected_column = expected_columns[column_name]
            model_column = model_columns[column_name]
            _compare_model_column(table_name, column_name, expected_column, model_column, findings)
        _compare_model_foreign_keys(table_name, table, expected, findings)
        _compare_model_unique_constraints(table_name, table, expected, findings)
        _compare_model_indexes(table_name, table, expected, findings)
    return findings


def _compare_columns(inspector: Any, table_name: str, expected: dict[str, Any], findings: list[SchemaFinding]) -> None:
    actual_columns = {item["name"]: item for item in inspector.get_columns(table_name)}
    expected_columns = expected["columns"]
    for column_name in sorted(set(expected_columns) - set(actual_columns)):
        findings.append(_finding("MISSING_COLUMN", "mismatch", "column", f"{table_name}.{column_name}"))
    for column_name in sorted(set(actual_columns) - set(expected_columns)):
        findings.append(_finding("EXTRA_COLUMN", "mismatch", "column", f"{table_name}.{column_name}"))

    for column_name in sorted(set(expected_columns) & set(actual_columns)):
        wanted = expected_columns[column_name]
        observed = actual_columns[column_name]
        expected_type = _type_signature(wanted)
        actual_type = _type_signature(observed["type"])
        if expected_type != actual_type:
            findings.append(_finding("TYPE_MISMATCH", "mismatch", "column", f"{table_name}.{column_name}", expected_type, actual_type))
        if bool(wanted.get("nullable", True)) != bool(observed.get("nullable", True)):
            findings.append(_finding("NULLABILITY_MISMATCH", "mismatch", "column", f"{table_name}.{column_name}", wanted.get("nullable"), observed.get("nullable")))
        expected_server = wanted.get("server_default")
        if expected_server is not None:
            actual_server = observed.get("default")
            if _normalize_default(actual_server, wanted.get("type")) != _normalize_default(expected_server, wanted.get("type")):
                findings.append(_finding("DEFAULT_MISMATCH", "mismatch", "column", f"{table_name}.{column_name}", expected_server, actual_server))


def _compare_primary_key(inspector: Any, table_name: str, expected: dict[str, Any], findings: list[SchemaFinding]) -> None:
    actual = inspector.get_pk_constraint(table_name).get("constrained_columns") or []
    wanted = [name for name, column in expected["columns"].items() if column.get("primary_key")]
    if list(actual) != wanted:
        findings.append(_finding("PRIMARY_KEY_MISMATCH", "mismatch", "primary_key", table_name, wanted, actual))


def _compare_foreign_keys(inspector: Any, table_name: str, expected: dict[str, Any], findings: list[SchemaFinding]) -> None:
    wanted = {_foreign_key_signature(item) for item in expected.get("foreign_keys", [])}
    actual: set[tuple[Any, ...]] = set()
    for item in inspector.get_foreign_keys(table_name):
        options = item.get("options") or {}
        actual.add(
            (
                tuple(item.get("constrained_columns") or []),
                f"{item.get('referred_table')}.{','.join(item.get('referred_columns') or [])}",
                _normalize_action(options.get("ondelete")),
            )
        )
    if wanted != actual:
        findings.append(_finding("FOREIGN_KEY_MISMATCH", "mismatch", "foreign_key", table_name, sorted(wanted), sorted(actual)))


def _compare_unique_constraints(inspector: Any, table_name: str, expected: dict[str, Any], findings: list[SchemaFinding]) -> None:
    wanted = {_unique_signature(item) for item in expected.get("unique_constraints", [])}
    actual = set()
    for item in inspector.get_unique_constraints(table_name):
        actual.add((tuple(item.get("column_names") or []), item.get("name")))
    if not _unique_sets_equal(wanted, actual):
        findings.append(_finding("UNIQUE_CONSTRAINT_MISMATCH", "mismatch", "unique_constraint", table_name, sorted(wanted), sorted(actual)))


def _compare_indexes(inspector: Any, table_name: str, expected: dict[str, Any], dialect: str, findings: list[SchemaFinding]) -> None:
    wanted = {item["name"]: item for item in expected.get("indexes", [])}
    actual = {item.get("name"): item for item in inspector.get_indexes(table_name) if item.get("name")}
    for name in sorted(set(wanted) - set(actual)):
        findings.append(_finding("MISSING_INDEX", "mismatch", "index", f"{table_name}.{name}"))
    for name in sorted(set(actual) - set(wanted)):
        findings.append(_finding("EXTRA_INDEX", "mismatch", "index", f"{table_name}.{name}"))
    for name in sorted(set(wanted) & set(actual)):
        expected_index = wanted[name]
        actual_index = actual[name]
        expected_columns = tuple(expected_index.get("columns", []))
        actual_columns = tuple(actual_index.get("column_names") or [])
        if expected_columns != actual_columns or bool(expected_index.get("unique")) != bool(actual_index.get("unique")):
            findings.append(_finding("INDEX_MISMATCH", "mismatch", "index", f"{table_name}.{name}", expected_index, actual_index))
            continue
        predicates = expected_index.get("predicates", {})
        if dialect in predicates:
            observed_predicate = _index_predicate(actual_index, dialect)
            if observed_predicate is None:
                findings.append(_finding("INDEX_PREDICATE_UNAVAILABLE", "unsupported", "index", f"{table_name}.{name}", predicates[dialect], None, "Dialect inspector did not expose the partial-index predicate."))
            elif _normalize_sql(observed_predicate) != _normalize_sql(predicates[dialect]):
                findings.append(_finding("INDEX_PREDICATE_MISMATCH", "mismatch", "index", f"{table_name}.{name}", predicates[dialect], observed_predicate))


def _compare_checks(inspector: Any, table_name: str, expected: dict[str, Any], findings: list[SchemaFinding]) -> None:
    wanted = {str(item) for item in expected.get("check_constraints", [])}
    actual = {str(item.get("sqltext")) for item in inspector.get_check_constraints(table_name)}
    if wanted != actual:
        findings.append(_finding("CHECK_CONSTRAINT_MISMATCH", "mismatch", "check_constraint", table_name, sorted(wanted), sorted(actual)))


def _compare_model_column(table_name: str, column_name: str, expected: dict[str, Any], column: Any, findings: list[SchemaFinding]) -> None:
    expected_type = _type_signature(expected)
    model_type = _type_signature(column.type)
    if expected_type != model_type:
        findings.append(_finding("MODEL_TYPE_MISMATCH", "mismatch", "model.column", f"{table_name}.{column_name}", expected_type, model_type))
    if bool(expected.get("nullable", True)) != bool(column.nullable):
        findings.append(_finding("MODEL_NULLABILITY_MISMATCH", "mismatch", "model.column", f"{table_name}.{column_name}", expected.get("nullable"), column.nullable))
    if bool(expected.get("primary_key")) != bool(column.primary_key):
        findings.append(_finding("MODEL_PRIMARY_KEY_MISMATCH", "mismatch", "model.column", f"{table_name}.{column_name}", expected.get("primary_key"), column.primary_key))
    if "default" in expected and _normalize_default(expected["default"], expected.get("type")) != _normalize_default(getattr(column.default, "arg", None), expected.get("type")):
        findings.append(_finding("MODEL_DEFAULT_MISMATCH", "mismatch", "model.column", f"{table_name}.{column_name}", expected["default"], getattr(column.default, "arg", None)))
    if "server_default" in expected and _normalize_default(expected["server_default"], expected.get("type")) != _normalize_default(getattr(column.server_default, "arg", None), expected.get("type")):
        findings.append(_finding("MODEL_SERVER_DEFAULT_MISMATCH", "mismatch", "model.column", f"{table_name}.{column_name}", expected["server_default"], getattr(column.server_default, "arg", None)))


def _compare_model_foreign_keys(table_name: str, table: Any, expected: dict[str, Any], findings: list[SchemaFinding]) -> None:
    wanted = {_foreign_key_signature(item) for item in expected.get("foreign_keys", [])}
    actual = set()
    for column in table.columns:
        for fk in column.foreign_keys:
            actual.add(((column.name,), fk.target_fullname, _normalize_action(fk.ondelete)))
    if wanted != actual:
        findings.append(_finding("MODEL_FOREIGN_KEY_MISMATCH", "mismatch", "model.foreign_key", table_name, sorted(wanted), sorted(actual)))


def _compare_model_unique_constraints(table_name: str, table: Any, expected: dict[str, Any], findings: list[SchemaFinding]) -> None:
    wanted = {_unique_signature(item) for item in expected.get("unique_constraints", [])}
    actual = set()
    for constraint in table.constraints:
        if isinstance(constraint, UniqueConstraint) and not isinstance(constraint, PrimaryKeyConstraint):
            actual.add((tuple(column.name for column in constraint.columns), constraint.name))
    if not _unique_sets_equal(wanted, actual):
        findings.append(_finding("MODEL_UNIQUE_CONSTRAINT_MISMATCH", "mismatch", "model.unique_constraint", table_name, sorted(wanted), sorted(actual)))


def _compare_model_indexes(table_name: str, table: Any, expected: dict[str, Any], findings: list[SchemaFinding]) -> None:
    wanted = {item["name"]: item for item in expected.get("indexes", [])}
    actual = {item.name: item for item in table.indexes if item.name}
    for name in sorted(set(wanted) - set(actual)):
        findings.append(_finding("MODEL_MISSING_INDEX", "mismatch", "model.index", f"{table_name}.{name}"))
    for name in sorted(set(actual) - set(wanted)):
        findings.append(_finding("MODEL_EXTRA_INDEX", "mismatch", "model.index", f"{table_name}.{name}"))
    for name in sorted(set(wanted) & set(actual)):
        expected_index = wanted[name]
        model_index = actual[name]
        actual_columns = tuple(expression.name for expression in model_index.expressions)
        if tuple(expected_index.get("columns", [])) != actual_columns or bool(expected_index.get("unique")) != bool(model_index.unique):
            findings.append(_finding("MODEL_INDEX_MISMATCH", "mismatch", "model.index", f"{table_name}.{name}", expected_index, actual_columns))


def _type_signature(value: Any) -> tuple[Any, ...]:
    if isinstance(value, dict):
        kind = value.get("type")
        length = value.get("length")
        if kind == "datetime":
            return (kind, bool(value.get("timezone", False)))
        if kind in {"json", "jsonb"}:
            return (kind, None)
    else:
        kind = None
        length = getattr(value, "length", None)
        if isinstance(value, Integer):
            kind = "integer"
        elif isinstance(value, Text):
            kind = "text"
        elif isinstance(value, String):
            kind = "string"
        elif isinstance(value, Boolean):
            kind = "boolean"
        elif isinstance(value, DateTime):
            return ("datetime", bool(value.timezone))
        elif isinstance(value, Float):
            kind = "float"
        elif isinstance(value, JSONB):
            return ("jsonb", None)
        elif isinstance(value, JSON):
            return ("json", None)
        else:
            name = getattr(value, "__visit_name__", type(value).__name__).lower()
            kind = {"integer": "integer", "varchar": "string", "text": "text", "boolean": "boolean", "datetime": "datetime", "float": "float", "json": "json"}.get(name, name)
    return (kind, length if kind == "string" else None)


def _foreign_key_signature(value: dict[str, Any]) -> tuple[Any, ...]:
    return (tuple(value.get("columns", [])), value["target"], _normalize_action(value.get("on_delete")))


def _unique_signature(value: dict[str, Any]) -> tuple[Any, ...]:
    return (tuple(value.get("columns", [])), value.get("name"))


def _unique_sets_equal(expected: set[tuple[Any, ...]], actual: set[tuple[Any, ...]]) -> bool:
    if expected == actual:
        return True
    expected_columns = {item[0] for item in expected}
    actual_columns = {item[0] for item in actual}
    return expected_columns == actual_columns and all(name is None for _, name in expected)


def _index_predicate(index: dict[str, Any], dialect: str) -> str | None:
    options = index.get("dialect_options") or {}
    value = options.get(f"{dialect}_where")
    return None if value is None else str(value)


def _normalize_sql(value: Any) -> str:
    normalized = re.sub(r"\s+", " ", str(value).strip()).lower()
    while normalized.startswith("(") and normalized.endswith(")"):
        depth = 0
        balanced = True
        for index, character in enumerate(normalized):
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth == 0 and index != len(normalized) - 1:
                    balanced = False
                    break
        if not balanced or depth != 0:
            break
        normalized = normalized[1:-1].strip()
    return normalized


def _normalize_default(value: Any, type_name: str | None = None) -> Any:
    if value is None:
        return None
    if callable(value):
        return getattr(value, "__name__", repr(value))
    text = str(value).strip()
    if type_name == "boolean" and text.lower().strip("'") in {"0", "false"}:
        return "false"
    if type_name == "boolean" and text.lower().strip("'") in {"1", "true"}:
        return "true"
    text = re.sub(r'::[a-zA-Z0-9_\s\[\]"]+$', "", text)
    return text.strip("'").strip('"').lower() if isinstance(value, str) or not isinstance(value, (bool, int, float)) else value


def _normalize_action(value: Any) -> str | None:
    return None if value is None else str(value).upper()


def _normalize_dialect(value: Any) -> str:
    value = str(value or "unknown").lower()
    if value in {"postgres", "postgresql+psycopg", "postgresql+psycopg2"}:
        return "postgresql"
    return value


def _finding(code: str, severity: str, object_type: str, object_name: str, expected: Any = None, observed: Any = None, message: str = "") -> SchemaFinding:
    return SchemaFinding(code, severity, object_type, object_name, expected, observed, message)
