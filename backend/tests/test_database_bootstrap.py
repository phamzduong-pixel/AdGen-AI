import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine, inspect

from app.database.bootstrap import DatabaseBootstrapRejected, bootstrap_database
from app.database.schema_state import inspect_database_state


class DatabaseBootstrapTest(unittest.TestCase):
    def test_empty_sqlite_bootstraps_current_schema_without_duplicate_indexes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "empty.sqlite"
            engine = create_engine(f"sqlite:///{db_path}")
            try:
                result = bootstrap_database(engine)
                self.assertEqual(result.state.state, "MANAGED_CANONICAL_SCHEMA")
                self.assertIn("voiceover_audios", inspect(engine).get_table_names())
                indexes = {
                    item["name"]
                    for item in inspect(engine).get_indexes("content_documents")
                }
                self.assertEqual(
                    indexes.intersection({"uq_content_documents_campaign_primary"}),
                    {"uq_content_documents_campaign_primary"},
                )
                self.assertEqual(inspect_database_state(engine).state, "MANAGED_CANONICAL_SCHEMA")
            finally:
                engine.dispose()

    def test_existing_database_is_not_bootstrapped_again(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "existing.sqlite"
            engine = create_engine(f"sqlite:///{db_path}")
            try:
                bootstrap_database(engine)
                with self.assertRaises(DatabaseBootstrapRejected):
                    bootstrap_database(engine)
                self.assertEqual(inspect_database_state(engine).state, "MANAGED_CANONICAL_SCHEMA")
            finally:
                engine.dispose()


if __name__ == "__main__":
    unittest.main()