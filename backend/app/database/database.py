from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy import inspect
from sqlalchemy import text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.database.schema_state import inspect_database_state

DATABASE_URL = settings.DATABASE_URL
if not DATABASE_URL:
    raise RuntimeError(
        "Thiếu biến môi trường bắt buộc DATABASE_URL"
    )

IS_SQLITE = DATABASE_URL.startswith("sqlite")
engine_options = {"pool_pre_ping": True}
if IS_SQLITE:
    engine_options["connect_args"] = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, **engine_options)


if IS_SQLITE:
    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


class DatabaseStartupBlocked(RuntimeError):
    """Raised when startup cannot prove that schema management is safe."""


def initialize_database():
    """Validate a managed canonical schema without changing it.

    Runtime startup is deliberately read-only.  Empty, unmanaged, drifted or
    stale-marker databases must go through an explicitly approved bootstrap or
    repair workflow before the application is allowed to start.
    """
    report = inspect_database_state(engine)
    if report.state != "MANAGED_CANONICAL_SCHEMA":
        current = ", ".join(report.current_revisions) or "none"
        heads = ", ".join(report.heads) or "unavailable"
        raise DatabaseStartupBlocked(
            "Database startup blocked: "
            f"state={report.state}; decision={report.decision}; "
            f"schema_status={report.schema_status}; current={current}; "
            f"heads={heads}. {report.reason} "
            "Run the approved schema bootstrap or legacy reconciliation workflow "
            "before starting the backend; no automatic migration or repair was run."
        )
    return report


def _initialize_database_unchecked():
    """Retired legacy mutation path.

    This compatibility hook must never mutate an unmanaged database.
    Bootstrap and legacy reconciliation are explicit workflows.
    """
    raise DatabaseStartupBlocked(
        "Legacy automatic schema repair is disabled. Use the explicit "
        "bootstrap or legacy reconciliation workflow."
    )

    # Kept unreachable only for source-history review.
    if not IS_SQLITE:
        return

    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    if "media_assets" in inspector.get_table_names():
        _upgrade_media_asset_versioning(inspector)
        inspector = inspect(engine)
    if "saved_contents" in inspector.get_table_names():
        saved_columns = {
            column["name"]: column
            for column in inspector.get_columns("saved_contents")
        }
        if saved_columns.get("message_id", {}).get("nullable") is False:
            _make_saved_content_message_optional()
            inspector = inspect(engine)
    if "conversations" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("conversations")}
    if "is_pinned" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE conversations "
                    "ADD COLUMN is_pinned BOOLEAN NOT NULL DEFAULT 0"
                )
            )

    title_columns_added = False

    if "is_title_custom" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE conversations "
                    "ADD COLUMN is_title_custom BOOLEAN NOT NULL DEFAULT 0"
                )
            )
        title_columns_added = True

    if "has_generated_title" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE conversations "
                    "ADD COLUMN has_generated_title BOOLEAN NOT NULL DEFAULT 0"
                )
            )
        title_columns_added = True

    if title_columns_added:
        # Preserve existing user-defined titles conservatively. Old databases do
        # not contain enough information to distinguish manual and generated
        # titles, so any non-default title must never be overwritten.
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE conversations "
                    "SET is_title_custom = 1 "
                    "WHERE TRIM(title) NOT IN "
                    "('New Chat', 'Cuộc trò chuyện mới')"
                )
            )

    if "uploaded_files" in inspector.get_table_names():
        upload_columns = {
            column["name"]
            for column in inspector.get_columns("uploaded_files")
        }
        upload_column_definitions = {
            "content_type": (
                "ALTER TABLE uploaded_files ADD COLUMN content_type "
                "VARCHAR NOT NULL DEFAULT 'application/octet-stream'"
            ),
            "size": (
                "ALTER TABLE uploaded_files ADD COLUMN size "
                "INTEGER NOT NULL DEFAULT 0"
            ),
            "message_id": (
                "ALTER TABLE uploaded_files ADD COLUMN message_id INTEGER "
                "REFERENCES messages(id)"
            ),
        }
        with engine.begin() as connection:
            for column_name, statement in upload_column_definitions.items():
                if column_name not in upload_columns:
                    connection.execute(text(statement))

    if "messages" in inspector.get_table_names():
        message_columns = {
            column["name"]
            for column in inspector.get_columns("messages")
        }
        if "ad_brief_json" not in message_columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE messages "
                        "ADD COLUMN ad_brief_json TEXT"
                    )
                )
        if "prompt_type" not in message_columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE messages "
                        "ADD COLUMN prompt_type VARCHAR(50)"
                    )
                )

    platform_name_columns = {
        "messages": "VARCHAR(80)",
        "saved_contents": "VARCHAR(80)",
        "ad_templates": "VARCHAR(80)",
        "content_documents": "VARCHAR(80)",
        "campaigns": "VARCHAR(80)",

    }
    with engine.begin() as connection:
        for table_name, column_type in platform_name_columns.items():
            if table_name not in inspector.get_table_names():
                continue
            columns = {
                column["name"]
                for column in inspect(engine).get_columns(table_name)
            }
            if "platform_name" not in columns:
                connection.execute(
                    text(
                        f"ALTER TABLE {table_name} "
                        f"ADD COLUMN platform_name {column_type}"
                    )
                )

    if "user_settings" in inspector.get_table_names():
        settings_columns = {column["name"] for column in inspect(engine).get_columns("user_settings")}
        if "default_platform_name" not in settings_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE user_settings ADD COLUMN default_platform_name VARCHAR(80)"))

    if "users" in inspector.get_table_names():
        user_columns = {
            column["name"]
            for column in inspector.get_columns("users")
        }
        with engine.begin() as connection:
            if "created_at" not in user_columns:
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN created_at DATETIME")
                )
                connection.execute(
                    text(
                        "UPDATE users SET created_at = CURRENT_TIMESTAMP "
                        "WHERE created_at IS NULL"
                    )
                )
            if "token_version" not in user_columns:
                connection.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN token_version "
                        "INTEGER NOT NULL DEFAULT 0"
                    )
                )
            if "auth_provider" not in user_columns:
                connection.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN auth_provider "
                        "VARCHAR(20) NOT NULL DEFAULT 'local'"
                    )
                )
            if "google_sub" not in user_columns:
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN google_sub VARCHAR(255)")
                )
            if "avatar_url" not in user_columns:
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500)")
                )
            if "email_verified" not in user_columns:
                connection.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN email_verified "
                        "BOOLEAN NOT NULL DEFAULT 0"
                    )
                )
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS "
                    "ix_users_google_sub ON users (google_sub)"
                )
            )


def _make_saved_content_message_optional():
    """Safely rebuild the SQLite table so generated variants can be saved."""

    with engine.connect() as connection:
        source_columns = {
            column["name"]
            for column in inspect(connection).get_columns("saved_contents")
        }
        brand_id_expression = "brand_id" if "brand_id" in source_columns else "NULL"
        platform_name_expression = (
            "platform_name" if "platform_name" in source_columns else "NULL"
        )
        connection.execute(text("PRAGMA foreign_keys=OFF"))
        connection.commit()
        try:
            with connection.begin():
                connection.execute(
                    text("ALTER TABLE saved_contents RENAME TO saved_contents_legacy")
                )
                connection.execute(
                    text(
                        """
                        CREATE TABLE saved_contents (
                            id INTEGER NOT NULL PRIMARY KEY,
                            user_id INTEGER NOT NULL
                                REFERENCES users(id) ON DELETE CASCADE,
                            conversation_id INTEGER NOT NULL
                                REFERENCES conversations(id) ON DELETE CASCADE,
                            brand_id INTEGER
                                REFERENCES brand_profiles(id) ON DELETE SET NULL,
                            message_id INTEGER
                                REFERENCES messages(id) ON DELETE CASCADE,
                            title VARCHAR(160) NOT NULL,
                            content TEXT NOT NULL,
                            platform VARCHAR(50),
                            platform_name VARCHAR(80),
                            created_at DATETIME NOT NULL,
                            CONSTRAINT uq_saved_contents_user_message
                                UNIQUE (user_id, message_id)
                        )
                        """
                    )
                )
                connection.execute(
                    text(
                        f"""
                        INSERT INTO saved_contents (
                            id, user_id, conversation_id, brand_id, message_id,
                            title, content, platform, platform_name, created_at
                        )
                        SELECT
                            id, user_id, conversation_id, {brand_id_expression}, message_id,
                            title, content, platform, {platform_name_expression}, created_at
                        FROM saved_contents_legacy
                        """
                    )
                )
                connection.execute(text("DROP TABLE saved_contents_legacy"))
                connection.execute(
                    text(
                        "CREATE INDEX ix_saved_contents_id "
                        "ON saved_contents (id)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE INDEX ix_saved_contents_user_id "
                        "ON saved_contents (user_id)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE INDEX ix_saved_contents_conversation_id "
                        "ON saved_contents (conversation_id)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE INDEX ix_saved_contents_brand_id "
                        "ON saved_contents (brand_id)"
                    )
                )
                connection.execute(
                    text(
                        "CREATE INDEX ix_saved_contents_message_id "
                        "ON saved_contents (message_id)"
                    )
                )
        finally:
            connection.execute(text("PRAGMA foreign_keys=ON"))
            connection.commit()


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def _upgrade_media_asset_versioning(inspector) -> None:
    """Backfill old SQLite media rows before enabling the lineage unique index."""

    columns = {column["name"] for column in inspector.get_columns("media_assets")}
    if "root_asset_id" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE media_assets ADD COLUMN root_asset_id INTEGER")
            )

    with engine.begin() as connection:
        rows = connection.execute(
            text(
                "SELECT id, user_id, conversation_id, kind, parent_asset_id, "
                "root_asset_id, version_number FROM media_assets"
            )
        ).mappings().all()
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
                if (
                    row["user_id"], row["conversation_id"], row["kind"]
                ) != (
                    parent["user_id"], parent["conversation_id"], parent["kind"]
                ):
                    raise RuntimeError("Cannot backfill media asset roots: scope crossing")
                current_id = parent_id

        seen_versions = {}
        for row in rows:
            root_id = roots[row["id"]]
            if row["root_asset_id"] is not None and row["root_asset_id"] != root_id:
                raise RuntimeError("Cannot backfill media asset roots: inconsistent root")
            key = (
                row["user_id"],
                row["conversation_id"],
                row["kind"],
                root_id,
                row["version_number"],
            )
            if key in seen_versions:
                raise RuntimeError("Cannot protect media asset versions: duplicate lineage version")
            seen_versions[key] = row["id"]
            if row["root_asset_id"] is None:
                connection.execute(
                    text(
                        "UPDATE media_assets SET root_asset_id = :root_id "
                        "WHERE id = :asset_id"
                    ),
                    {"root_id": root_id, "asset_id": row["id"]},
                )

        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                "uq_media_assets_lineage_version "
                "ON media_assets (user_id, conversation_id, kind, "
                "root_asset_id, version_number)"
            )
        )
