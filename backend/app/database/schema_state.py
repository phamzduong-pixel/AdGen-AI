"""Read-only database state inspection and migration reconciliation."""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from app.database.schema_manifest import CANONICAL_SCHEMA_MANIFEST
from app.database.schema_validator import SchemaFinding, validate_schema


REVISION_OBJECTS: dict[str, tuple[str, ...]] = {
    "20260727_0001": ("all current model tables and objects via Base.metadata.create_all",),
    "20260727_0002": ("table:ad_templates", "table:template_favorites"),
    "20260727_0003": (
        "column:users.auth_provider",
        "column:users.google_sub",
        "column:users.avatar_url",
        "column:users.email_verified",
        "index:users.ix_users_google_sub",
    ),
    "20260727_0004": ("table:password_reset_tokens",),
    "20260727_0005": (
        "table:email_verification_tokens",
        "table:user_sessions",
        "data:users.email_verified",
    ),
    "20260727_0006": (
        "table:brand_profiles",
        "table:brand_assets",
        "table:brand_content_checks",
        "column:*.brand_id",
        "foreign_key:*.brand_id",
        "index:*.brand_id",
    ),
    "20260727_0007": ("table:content_documents", "table:content_versions"),
    "20260727_0008": ("index:content_documents.uq_content_documents_campaign_primary",),
    "20260727_0009": (
        "column:messages.platform_name",
        "column:saved_contents.platform_name",
        "column:ad_templates.platform_name",
        "column:content_documents.platform_name",
    ),
    "20260727_0010": ("column:user_settings.default_platform_name",),
    "20260727_0011": ("column:campaigns.platform_name",),
    "20260727_0012": (
        "table:media_assets",
        "index:media_assets.*",
    ),
    "20261001_0013": (
        "column:media_assets.operation_params",
        "column:media_assets.duration_seconds",
        "column:media_assets.width",
        "column:media_assets.height",
    ),
    "20261001_0014": ("table:media_jobs", "index:media_jobs.*"),
    "20261001_0015": (
        "column:media_assets.root_asset_id",
        "foreign_key:media_assets.fk_media_assets_root_asset_id",
        "unique:media_assets.uq_media_assets_lineage_version",
        "data:media_assets.root_asset_id backfill",
    ),
    "20261001_0016": (
        "table:media_edit_requests",
        "unique:media_edit_requests.uq_media_edit_requests_scope_key",
        "index:media_edit_requests.*",
    ),
    "20261003_0017": ("table:voiceover_audios", "index:voiceover_audios.*"),
}


@dataclass(frozen=True)
class DatabaseStateReport:
    state: str
    decision: str
    bootstrap_candidate: bool
    current_revisions: tuple[str, ...]
    heads: tuple[str, ...]
    schema_status: str
    application_tables: tuple[str, ...]
    future_revision_objects: dict[str, tuple[str, ...]]
    findings: tuple[SchemaFinding, ...]
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def inspect_database_state(
    bind: Any,
    *,
    manifest: dict[str, Any] = CANONICAL_SCHEMA_MANIFEST,
    script_location: str | Path | None = None,
) -> DatabaseStateReport:
    """Inspect schema and Alembic state without changing the database.

    This function is deliberately not a bootstrap operation.  It only reads
    ``alembic_version``, Alembic script metadata and SQLAlchemy Inspector
    output.  It never runs a migration, writes a marker, creates a table or
    repairs drift.
    """

    inspector = inspect(bind)
    all_tables = set(inspector.get_table_names())
    control_tables = set(manifest.get("allowed_control_tables", []))
    application_tables = tuple(sorted(all_tables - control_tables))
    current_revisions, marker_findings = _read_current_revisions(bind, all_tables)
    heads, graph_findings, revision_nodes = _read_revision_graph(script_location)
    schema_report = validate_schema(bind, manifest=manifest, compare_models=False)
    findings = list(schema_report.findings)
    findings.extend(marker_findings)
    findings.extend(graph_findings)

    expected_tables = set(manifest["tables"])
    future_objects = _future_revision_objects(current_revisions, heads, revision_nodes)
    has_unknown_tables = bool(set(application_tables) - expected_tables)
    has_application_schema = bool(set(application_tables) & expected_tables)
    marker_present = bool(current_revisions)
    marker_known = all(revision in revision_nodes for revision in current_revisions)
    head_match = bool(current_revisions) and set(current_revisions) == set(heads)

    if graph_findings:
        state = "REVISION_GRAPH_UNAVAILABLE"
        decision = "BLOCKED"
        bootstrap_candidate = False
        reason = "Revision graph could not be read safely."
    elif has_unknown_tables:
        state = "UNKNOWN_DATABASE_OBJECTS"
        decision = "BLOCKED"
        bootstrap_candidate = False
        reason = "Database contains non-canonical application tables."
    elif not marker_present and not has_application_schema and not all_tables:
        state = "EMPTY_UNMANAGED"
        decision = "SAFE_TO_REVIEW"
        bootstrap_candidate = True
        reason = "No application tables, no Alembic marker and no other tables were found."
    elif not marker_present and not has_application_schema:
        state = "EMPTY_WITH_UNEXPECTED_OBJECTS"
        decision = "BLOCKED"
        bootstrap_candidate = False
        reason = "No application tables exist, but unexpected database objects are present."
    elif not marker_present and schema_report.status == "PASS":
        state = "UNMANAGED_CANONICAL_SCHEMA"
        decision = "SAFE_TO_REVIEW"
        bootstrap_candidate = False
        reason = "Physical schema is canonical but no Alembic marker exists; this is not a new database."
    elif not marker_present:
        state = "UNMANAGED_SCHEMA_DRIFT"
        decision = "MISMATCH"
        bootstrap_candidate = False
        reason = "Application tables exist without an Alembic marker and do not match the manifest."
    elif not marker_known:
        state = "UNKNOWN_ALEMBIC_REVISION"
        decision = "BLOCKED"
        bootstrap_candidate = False
        reason = "The Alembic marker is not present in the repository revision graph."
    elif not has_application_schema:
        state = "MARKER_WITHOUT_APPLICATION_SCHEMA"
        decision = "BLOCKED"
        bootstrap_candidate = False
        reason = "An Alembic marker exists but no canonical application tables exist."
    elif schema_report.status == "UNSUPPORTED":
        state = "SCHEMA_UNVERIFIABLE"
        decision = "BLOCKED"
        bootstrap_candidate = False
        reason = "The available dialect inspector could not verify required schema objects."
    elif schema_report.status != "PASS":
        state = "MANAGED_SCHEMA_MISMATCH"
        decision = "MISMATCH"
        bootstrap_candidate = False
        reason = "The Alembic marker exists but the physical schema does not match the manifest."
    elif head_match:
        state = "MANAGED_CANONICAL_SCHEMA"
        decision = "SAFE_TO_REVIEW"
        bootstrap_candidate = False
        reason = "The physical schema matches the manifest and the marker is at an Alembic head."
    else:
        state = "STALE_MARKER_CANONICAL_SCHEMA"
        decision = "BLOCKED"
        bootstrap_candidate = False
        reason = "The physical schema matches the manifest but the Alembic marker is behind head; no stamp or upgrade is authorized."

    return DatabaseStateReport(
        state=state,
        decision=decision,
        bootstrap_candidate=bootstrap_candidate,
        current_revisions=current_revisions,
        heads=heads,
        schema_status=schema_report.status,
        application_tables=application_tables,
        future_revision_objects=future_objects,
        findings=tuple(findings),
        reason=reason,
    )


def _read_current_revisions(bind: Any, tables: set[str]) -> tuple[tuple[str, ...], list[SchemaFinding]]:
    if "alembic_version" not in tables:
        return (), []
    try:
        context = bind.connect() if hasattr(bind, "connect") else nullcontext(bind)
        with context as connection:
            rows = connection.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
        return tuple(str(value) for value in rows), []
    except Exception as exc:  # pragma: no cover - defensive dialect boundary
        return (), [
            SchemaFinding(
                "ALEMBIC_MARKER_UNREADABLE",
                "unsupported",
                "alembic_version",
                "alembic_version",
                message=f"Could not read the migration marker: {type(exc).__name__}",
            )
        ]


def _read_revision_graph(script_location: str | Path | None) -> tuple[tuple[str, ...], list[SchemaFinding], dict[str, Any]]:
    location = Path(script_location) if script_location else Path(__file__).resolve().parents[2] / "alembic"
    try:
        config = Config()
        config.set_main_option("script_location", str(location))
        script = ScriptDirectory.from_config(config)
        nodes = {revision.revision: revision for revision in script.walk_revisions()}
        return tuple(script.get_heads()), [], nodes
    except Exception as exc:  # pragma: no cover - defensive filesystem boundary
        return (), [
            SchemaFinding(
                "REVISION_GRAPH_UNAVAILABLE",
                "unsupported",
                "alembic_graph",
                str(location),
                message=f"Could not read Alembic revisions: {type(exc).__name__}",
            )
        ], {}


def _future_revision_objects(
    current_revisions: tuple[str, ...],
    heads: tuple[str, ...],
    nodes: dict[str, Any],
) -> dict[str, tuple[str, ...]]:
    if not current_revisions:
        return {}
    current_set = set(current_revisions)
    result: dict[str, tuple[str, ...]] = {}
    for head in heads:
        node = nodes.get(head)
        while node is not None and node.revision not in current_set:
            result[node.revision] = REVISION_OBJECTS.get(node.revision, ())
            down_revision = node.down_revision
            if not down_revision or isinstance(down_revision, tuple):
                break
            node = nodes.get(down_revision)
    return dict(sorted(result.items()))

