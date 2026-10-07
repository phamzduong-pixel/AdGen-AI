import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, inspect, text

from app.database import database as database_module
from app.database.database import Base, DatabaseStartupBlocked, initialize_database
from app.database.bootstrap import DatabaseBootstrapRejected, bootstrap_database
from app.database.legacy_reconciliation import inspect_legacy_database
from app.database.schema_state import inspect_database_state
import app.models  # noqa: F401


class SchemaStateTests(unittest.TestCase):
    def make_empty_database(self):
        return create_engine("sqlite:///:memory:")

    def make_current_schema(self):
        engine = self.make_empty_database()
        Base.metadata.create_all(engine)
        return engine

    def add_revision_marker(self, engine, revision):
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"
            )
            connection.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
                {"revision": revision},
            )

    def test_empty_database_is_only_a_bootstrap_candidate(self):
        report = inspect_database_state(self.make_empty_database())

        self.assertEqual(report.state, "EMPTY_UNMANAGED")
        self.assertEqual(report.decision, "SAFE_TO_REVIEW")
        self.assertTrue(report.bootstrap_candidate)
        self.assertEqual(report.current_revisions, ())
        self.assertEqual(report.application_tables, ())

    def test_create_all_schema_without_marker_is_not_new(self):
        report = inspect_database_state(self.make_current_schema())

        self.assertEqual(report.state, "UNMANAGED_CANONICAL_SCHEMA")
        self.assertEqual(report.decision, "SAFE_TO_REVIEW")
        self.assertFalse(report.bootstrap_candidate)
        self.assertEqual(report.schema_status, "PASS")

    def test_stale_revision_marker_with_canonical_schema_is_blocked(self):
        engine = self.make_current_schema()
        self.add_revision_marker(engine, "20260727_0007")

        before_tables = tuple(inspect(engine).get_table_names())
        with engine.connect() as connection:
            before_marker = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()

        report = inspect_database_state(engine)

        with engine.connect() as connection:
            after_marker = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        after_tables = tuple(inspect(engine).get_table_names())

        self.assertEqual(report.state, "STALE_MARKER_CANONICAL_SCHEMA")
        self.assertEqual(report.decision, "BLOCKED")
        self.assertEqual(report.schema_status, "PASS")
        self.assertEqual(before_marker, after_marker, "inspection must not change the Alembic marker")
        self.assertEqual(before_tables, after_tables, "inspection must not change tables")
        self.assertIn("20260727_0008", report.future_revision_objects)
        self.assertIn("20261001_0016", report.future_revision_objects)

    def test_stale_marker_with_schema_drift_is_mismatch(self):
        engine = self.make_current_schema()
        self.add_revision_marker(engine, "20260727_0007")
        with engine.begin() as connection:
            connection.exec_driver_sql("DROP INDEX uq_content_documents_campaign_primary")

        report = inspect_database_state(engine)

        self.assertEqual(report.state, "MANAGED_SCHEMA_MISMATCH")
        self.assertEqual(report.decision, "MISMATCH")
        self.assertEqual(report.schema_status, "MISMATCH")

    def test_marker_without_application_schema_is_blocked(self):
        engine = self.make_empty_database()
        self.add_revision_marker(engine, "20260727_0007")

        report = inspect_database_state(engine)

        self.assertEqual(report.state, "MARKER_WITHOUT_APPLICATION_SCHEMA")
        self.assertEqual(report.decision, "BLOCKED")
        self.assertFalse(report.bootstrap_candidate)

    def test_runtime_rejects_empty_database_without_ddl(self):
        engine = self.make_empty_database()
        with patch.object(database_module, "engine", engine), patch.object(
            Base.metadata, "create_all"
        ) as create_all:
            with self.assertRaises(DatabaseStartupBlocked):
                initialize_database()

        create_all.assert_not_called()
        self.assertEqual(inspect(engine).get_table_names(), [])

    def test_retired_legacy_mutation_path_never_performs_ddl(self):
        engine = self.make_empty_database()

        with patch.object(database_module, "engine", engine), patch.object(
            Base.metadata, "create_all"
        ) as create_all:
            with self.assertRaises(DatabaseStartupBlocked):
                database_module._initialize_database_unchecked()

        create_all.assert_not_called()
        self.assertEqual(inspect(engine).get_table_names(), [])

    def test_runtime_rejects_unmanaged_create_all_schema_without_ddl(self):
        engine = self.make_current_schema()
        before_tables = tuple(inspect(engine).get_table_names())
        with patch.object(database_module, "engine", engine), patch.object(
            Base.metadata, "create_all"
        ) as create_all:
            with self.assertRaises(DatabaseStartupBlocked):
                initialize_database()

        create_all.assert_not_called()
        self.assertEqual(tuple(inspect(engine).get_table_names()), before_tables)

    def test_runtime_rejects_stale_marker_without_ddl_or_marker_change(self):
        engine = self.make_current_schema()
        self.add_revision_marker(engine, "20260727_0007")
        with patch.object(database_module, "engine", engine), patch.object(
            Base.metadata, "create_all"
        ) as create_all:
            with self.assertRaises(DatabaseStartupBlocked):
                initialize_database()

        create_all.assert_not_called()
        with engine.connect() as connection:
            self.assertEqual(
                connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one(),
                "20260727_0007",
            )

    def test_runtime_allows_only_canonical_schema_at_current_head(self):
        engine = self.make_current_schema()
        self.add_revision_marker(engine, "20261006_0025")
        with patch.object(database_module, "engine", engine), patch.object(
            Base.metadata, "create_all"
        ) as create_all:
            report = initialize_database()

        self.assertEqual(report.state, "MANAGED_CANONICAL_SCHEMA")
        create_all.assert_not_called()

    def test_explicit_bootstrap_creates_and_marks_empty_database(self):
        engine = self.make_empty_database()

        result = bootstrap_database(engine)

        self.assertEqual(result.state.state, "MANAGED_CANONICAL_SCHEMA")
        self.assertEqual(result.state.current_revisions, ("20261006_0025",))
        self.assertEqual(result.state.schema_status, "PASS")

    def test_bootstrap_rejects_unmanaged_canonical_schema_without_changes(self):
        engine = self.make_current_schema()
        before_tables = tuple(inspect(engine).get_table_names())

        with self.assertRaises(DatabaseBootstrapRejected):
            bootstrap_database(engine)

        self.assertEqual(tuple(inspect(engine).get_table_names()), before_tables)
        self.assertNotIn("alembic_version", before_tables)

    def test_bootstrap_validation_failure_rolls_back_schema_and_marker(self):
        engine = self.make_empty_database()
        invalid_manifest = {
            "schema_id": "invalid-test",
            "manifest_version": "test",
            "supported_dialects": ["sqlite"],
            "allowed_control_tables": ["alembic_version"],
            "tables": {},
        }

        with self.assertRaises(DatabaseBootstrapRejected):
            bootstrap_database(engine, manifest=invalid_manifest)

        self.assertEqual(inspect(engine).get_table_names(), [])

    def test_bootstrap_runtime_failure_does_not_write_marker(self):
        engine = self.make_empty_database()
        with patch.object(Base.metadata, "create_all", side_effect=RuntimeError("synthetic")):
            with self.assertRaises(DatabaseBootstrapRejected):
                bootstrap_database(engine)

        self.assertEqual(inspect(engine).get_table_names(), [])

    def test_legacy_reconciliation_is_read_only_and_requires_review(self):
        engine = self.make_current_schema()
        before_tables = tuple(inspect(engine).get_table_names())

        report = inspect_legacy_database(engine)

        self.assertEqual(report.status, "SAFE_TO_REVIEW")
        self.assertEqual(report.source_state, "UNMANAGED_CANONICAL_SCHEMA")
        self.assertFalse(report.automatic_changes_allowed)
        self.assertEqual(tuple(inspect(engine).get_table_names()), before_tables)


if __name__ == "__main__":
    unittest.main()
