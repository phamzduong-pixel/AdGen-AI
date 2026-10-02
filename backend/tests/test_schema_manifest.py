import unittest
from unittest.mock import patch

from sqlalchemy import DateTime, create_engine, inspect, text
from sqlalchemy.dialects.postgresql import JSONB

from app.database import database as database_module
from app.database.database import Base
from app.database.schema_validator import _normalize_sql, _type_signature, validate_schema
import app.models  # noqa: F401


class SchemaManifestTests(unittest.TestCase):
    def make_current_schema(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        return engine

    def test_current_sqlite_schema_has_22_tables_and_content_activities(self):
        engine = self.make_current_schema()
        tables = set(inspect(engine).get_table_names())

        self.assertEqual(len(tables), 22)
        self.assertIn("content_activities", tables)

    def test_current_sqlite_schema_passes_manifest_and_model_validation(self):
        report = validate_schema(self.make_current_schema())

        self.assertEqual(report.status, "PASS")
        self.assertEqual(report.findings, ())

    def test_missing_table_is_reported(self):
        engine = self.make_current_schema()
        with engine.begin() as connection:
            connection.exec_driver_sql("DROP TABLE content_activities")

        report = validate_schema(engine, compare_models=False)

        self.assertEqual(report.status, "MISMATCH")
        self.assertIn("MISSING_TABLE", {item.code for item in report.findings})

    def test_extra_table_is_reported(self):
        engine = self.make_current_schema()
        with engine.begin() as connection:
            connection.exec_driver_sql("CREATE TABLE unexpected_schema_table (id INTEGER PRIMARY KEY)")

        report = validate_schema(engine, compare_models=False)

        self.assertEqual(report.status, "MISMATCH")
        self.assertIn("EXTRA_TABLE", {item.code for item in report.findings})

    def test_missing_and_extra_columns_are_reported(self):
        engine = self.make_current_schema()
        with engine.begin() as connection:
            connection.exec_driver_sql("ALTER TABLE users DROP COLUMN avatar_url")
            connection.exec_driver_sql("ALTER TABLE users ADD COLUMN unexpected_column TEXT")

        report = validate_schema(engine, compare_models=False)
        codes = {item.code for item in report.findings}

        self.assertEqual(report.status, "MISMATCH")
        self.assertIn("MISSING_COLUMN", codes)
        self.assertIn("EXTRA_COLUMN", codes)

    def test_missing_partial_index_is_reported(self):
        engine = self.make_current_schema()
        with engine.begin() as connection:
            connection.exec_driver_sql("DROP INDEX uq_content_documents_campaign_primary")

        report = validate_schema(engine, compare_models=False)

        self.assertEqual(report.status, "MISMATCH")
        self.assertIn("MISSING_INDEX", {item.code for item in report.findings})

    def test_validator_does_not_change_schema_or_data(self):
        engine = self.make_current_schema()
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO users (username, email, hashed_password, created_at, "
                    "token_version, auth_provider, email_verified) "
                    "VALUES ('schema-user', 'schema@example.test', 'hash', "
                    "'2026-10-02 00:00:00', 0, 'local', 0)"
                )
            )
            before_count = connection.execute(text("SELECT COUNT(*) FROM users")).scalar_one()
            before_tables = tuple(inspect(connection).get_table_names())

        report = validate_schema(engine)

        with engine.connect() as connection:
            after_count = connection.execute(text("SELECT COUNT(*) FROM users")).scalar_one()
            after_tables = tuple(inspect(connection).get_table_names())

        self.assertEqual(report.status, "PASS")
        self.assertEqual(before_count, after_count)
        self.assertEqual(before_tables, after_tables)

    def test_dialect_type_normalization_keeps_jsonb_and_timezone_distinct(self):
        self.assertEqual(_type_signature(JSONB()), ("jsonb", None))
        self.assertEqual(_type_signature(DateTime(timezone=False)), ("datetime", False))
        self.assertEqual(_type_signature(DateTime(timezone=True)), ("datetime", True))

    def test_partial_predicate_normalization_removes_only_outer_parentheses(self):
        self.assertEqual(
            _normalize_sql("(is_campaign_primary AND campaign_id IS NOT NULL)"),
            "is_campaign_primary and campaign_id is not null",
        )

    def test_saved_contents_rebuild_preserves_brand_and_platform_name(self):
        engine = create_engine("sqlite:///:memory:")
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR NOT NULL, "
                "email VARCHAR NOT NULL, hashed_password VARCHAR NOT NULL)"
            )
            connection.exec_driver_sql(
                "CREATE TABLE conversations (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL)"
            )
            connection.exec_driver_sql(
                "CREATE TABLE brand_profiles (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL)"
            )
            connection.exec_driver_sql(
                "CREATE TABLE messages (id INTEGER PRIMARY KEY, conversation_id INTEGER NOT NULL)"
            )
            connection.exec_driver_sql(
                """
                CREATE TABLE saved_contents (
                    id INTEGER NOT NULL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    conversation_id INTEGER NOT NULL,
                    brand_id INTEGER,
                    message_id INTEGER NOT NULL,
                    title VARCHAR(160) NOT NULL,
                    content TEXT NOT NULL,
                    platform VARCHAR(50),
                    platform_name VARCHAR(80),
                    created_at DATETIME NOT NULL,
                    CONSTRAINT uq_saved_contents_user_message UNIQUE (user_id, message_id)
                )
                """
            )
            connection.execute(text("INSERT INTO users VALUES (1, 'u', 'u@example.test', 'h')"))
            connection.execute(text("INSERT INTO conversations VALUES (10, 1)"))
            connection.execute(text("INSERT INTO brand_profiles VALUES (5, 1)"))
            connection.execute(text("INSERT INTO messages VALUES (20, 10)"))
            connection.execute(
                text(
                    "INSERT INTO saved_contents VALUES "
                    "(30, 1, 10, 5, 20, 'Title', 'Body', 'facebook', 'Legacy Name', "
                    "'2026-10-02 00:00:00')"
                )
            )

        with patch.object(database_module, "engine", engine):
            database_module._make_saved_content_message_optional()

        inspector = inspect(engine)
        columns = {item["name"]: item for item in inspector.get_columns("saved_contents")}
        indexes = {item["name"] for item in inspector.get_indexes("saved_contents")}
        with engine.connect() as connection:
            row = connection.execute(
                text("SELECT brand_id, platform_name, message_id FROM saved_contents WHERE id = 30")
            ).one()

        self.assertIn("brand_id", columns)
        self.assertIn("platform_name", columns)
        self.assertTrue(columns["message_id"]["nullable"])
        self.assertEqual(tuple(row), (5, "Legacy Name", 20))
        self.assertTrue(
            {
                "ix_saved_contents_id",
                "ix_saved_contents_user_id",
                "ix_saved_contents_conversation_id",
                "ix_saved_contents_brand_id",
                "ix_saved_contents_message_id",
            }.issubset(indexes)
        )


if __name__ == "__main__":
    unittest.main()
