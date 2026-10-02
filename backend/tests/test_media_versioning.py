import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.database.database import Base
from app.models.conversation import Conversation
from app.models.media_asset import MediaAsset
from app.models.user import User
from app.services.media.versioning import (
    create_versioned_asset,
    next_media_version_number,
)


class MediaVersionConcurrencyTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "versioning.db"
        self.engine = create_engine(
            f"sqlite:///{database_path}",
            connect_args={"check_same_thread": False, "timeout": 5},
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        setup = self.Session()
        self.user = User(
            username="version-owner",
            email="version-owner@example.com",
            hashed_password="x",
        )
        setup.add(self.user)
        setup.commit()
        self.conversation = Conversation(title="Versioning", user_id=self.user.id)
        setup.add(self.conversation)
        setup.commit()
        self.root = MediaAsset(
            user_id=self.user.id,
            conversation_id=self.conversation.id,
            kind="video",
            operation="upload",
            status="completed",
            prompt="source",
            version_number=1,
            content_type="video/mp4",
            filepath="source.mp4",
            size=20,
        )
        setup.add(self.root)
        setup.flush()
        self.root.root_asset_id = self.root.id
        setup.commit()
        self.root_id = self.root.id
        self.user_id = self.user.id
        self.conversation_id = self.conversation.id
        setup.close()

    def tearDown(self):
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_independent_sessions_collision_is_rejected_and_retry_allocates_next_version(self):
        first = self.Session()
        second = self.Session()
        source_first = first.get(MediaAsset, self.root_id)
        source_second = second.get(MediaAsset, self.root_id)

        self.assertEqual(next_media_version_number(first, source_first), 2)
        self.assertEqual(next_media_version_number(second, source_second), 2)

        first_edit = MediaAsset(
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            parent_asset_id=self.root_id,
            root_asset_id=self.root_id,
            kind="video",
            operation="trim",
            status="processing",
            prompt="trim",
            version_number=2,
            content_type="video/mp4",
        )
        second_edit = MediaAsset(
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            parent_asset_id=self.root_id,
            root_asset_id=self.root_id,
            kind="video",
            operation="trim",
            status="processing",
            prompt="trim",
            version_number=2,
            content_type="video/mp4",
        )
        first.add(first_edit)
        first.commit()
        second.add(second_edit)
        with self.assertRaises(IntegrityError):
            second.commit()
        second.rollback()

        recovered = create_versioned_asset(
            second,
            source_second,
            lambda root_id, version_number: MediaAsset(
                user_id=self.user_id,
                conversation_id=self.conversation_id,
                parent_asset_id=self.root_id,
                root_asset_id=root_id,
                kind="video",
                operation="trim",
                status="processing",
                prompt="trim retry",
                version_number=version_number,
                content_type="video/mp4",
            ),
        )

        self.assertEqual(recovered.version_number, 3)
        self.assertEqual(recovered.parent_asset_id, self.root_id)
        self.assertEqual(recovered.root_asset_id, self.root_id)
        self.assertEqual(second.get(MediaAsset, self.root_id).version_number, 1)
        self.assertEqual(
            second.query(MediaAsset)
            .filter(MediaAsset.root_asset_id == self.root_id)
            .count(),
            3,
        )
        first.close()
        second.close()

    def test_legacy_parent_walk_resolves_root_before_backfill(self):
        session = self.Session()
        legacy_root = MediaAsset(
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            kind="image",
            operation="generate",
            status="completed",
            prompt="legacy root",
            version_number=1,
        )
        session.add(legacy_root)
        session.flush()
        legacy_child = MediaAsset(
            user_id=self.user_id,
            conversation_id=self.conversation_id,
            kind="image",
            operation="edit",
            status="completed",
            prompt="legacy child",
            parent_asset_id=legacy_root.id,
            version_number=2,
        )
        session.add(legacy_child)
        session.commit()
        self.assertEqual(next_media_version_number(session, legacy_child), 3)
        session.close()


if __name__ == "__main__":
    unittest.main()