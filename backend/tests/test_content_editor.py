import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.content_document import router
from app.core.security import get_current_user
from app.database.database import Base, get_db
from app.models.brand import BrandProfile
from app.models.campaign import Campaign
from app.models.content_document import ContentDocument, ContentVersion
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.saved_content import SavedContent
from app.models.user import User


class ContentEditorApiTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
        self.db = self.Session()
        self.owner = User(
            username="editor-owner",
            email="editor-owner@example.com",
            hashed_password="unused",
            email_verified=True,
        )
        self.other = User(
            username="editor-other",
            email="editor-other@example.com",
            hashed_password="unused",
            email_verified=True,
        )
        self.db.add_all([self.owner, self.other])
        self.db.flush()
        self.conversation = Conversation(
            user_id=self.owner.id,
            title="Chiến dịch mùa hè",
        )
        self.other_conversation = Conversation(
            user_id=self.other.id,
            title="Private",
        )
        self.db.add_all([self.conversation, self.other_conversation])
        self.db.flush()
        self.user_message = Message(
            conversation_id=self.conversation.id,
            role="user",
            content="Viết quảng cáo Facebook",
            prompt_type="facebook",
        )
        self.ai_message = Message(
            conversation_id=self.conversation.id,
            role="assistant",
            content="# Ưu đãi mùa hè\n\nNội dung AI gốc.",
        )
        self.other_message = Message(
            conversation_id=self.other_conversation.id,
            role="assistant",
            content="Private AI",
        )
        self.db.add_all([self.user_message, self.ai_message, self.other_message])
        self.db.flush()
        self.saved = SavedContent(
            user_id=self.owner.id,
            conversation_id=self.conversation.id,
            message_id=None,
            title="Bản đã lưu",
            content="Nội dung trong thư viện",
            platform="facebook",
        )
        self.brand = BrandProfile(
            user_id=self.owner.id,
            name="DG Studio",
            default_tone="Thân thiện",
            preferred_cta="Đăng ký ngay",
            keywords_json="[]",
            forbidden_words_json='["rẻ nhất"]',
        )
        self.other_brand = BrandProfile(
            user_id=self.other.id,
            name="Private Brand",
            keywords_json="[]",
            forbidden_words_json="[]",
        )
        self.campaign = Campaign(user_id=self.owner.id, name="Summer")
        self.other_campaign = Campaign(user_id=self.other.id, name="Private")
        self.db.add_all(
            [self.saved, self.brand, self.other_brand, self.campaign, self.other_campaign]
        )
        self.db.commit()
        self.current_user = self.owner

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.current_user
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.db.close()
        self.engine.dispose()

    def create_from_message(self):
        return self.client.post(
            "/contents",
            json={"source_message_id": self.ai_message.id},
        )

    def test_create_document_keeps_source_and_initial_version(self):
        response = self.create_from_message()
        self.assertEqual(response.status_code, 201)
        document = response.json()
        self.assertEqual(document["content"], self.ai_message.content)
        self.assertEqual(document["platform"], "facebook")
        self.assertEqual(document["current_version"], 1)
        versions = self.client.get(f"/contents/{document['id']}/versions").json()
        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0]["created_by"], "ai")
        self.assertEqual(self.db.get(Message, self.ai_message.id).content, self.ai_message.content)
        duplicate = self.create_from_message()
        self.assertEqual(duplicate.json()["id"], document["id"])

    def test_autosave_and_new_version_only_when_changed(self):
        document = self.create_from_message().json()
        patched = self.client.patch(
            f"/contents/{document['id']}",
            json={
                "title": "Bản chỉnh sửa",
                "content": "Nội dung đang làm việc",
                "cta": "Đăng ký ngay",
            },
        )
        self.assertEqual(patched.status_code, 200)
        self.assertEqual(patched.json()["current_version"], 1)
        self.assertEqual(
            len(self.client.get(f"/contents/{document['id']}/versions").json()),
            1,
        )
        versioned = self.client.post(
            f"/contents/{document['id']}/versions",
            json={"change_summary": "Điều chỉnh CTA"},
        )
        self.assertTrue(versioned.json()["created"])
        self.assertEqual(versioned.json()["version"]["version_number"], 2)
        unchanged = self.client.post(
            f"/contents/{document['id']}/versions",
            json={"change_summary": "Không đổi"},
        )
        self.assertFalse(unchanged.json()["created"])
        self.assertEqual(
            self.db.query(ContentVersion)
            .filter(ContentVersion.content_id == document["id"])
            .count(),
            2,
        )

    def test_restore_creates_new_version_without_overwriting_history(self):
        document = self.create_from_message().json()
        first = self.client.get(f"/contents/{document['id']}/versions").json()[0]
        self.client.patch(
            f"/contents/{document['id']}",
            json={"content": "Nội dung phiên bản hai"},
        )
        self.client.post(
            f"/contents/{document['id']}/versions",
            json={"change_summary": "Phiên bản hai"},
        )
        restored = self.client.post(
            f"/contents/{document['id']}/versions/{first['id']}/restore"
        )
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.json()["document"]["content"], first["content"])
        self.assertEqual(restored.json()["version"]["version_number"], 3)
        self.assertIn("phiên bản 1", restored.json()["version"]["change_summary"])
        versions = self.client.get(f"/contents/{document['id']}/versions").json()
        self.assertEqual([item["version_number"] for item in versions], [3, 2, 1])
        self.assertEqual(
            self.client.patch(
                f"/contents/{document['id']}/versions/{first['id']}",
                json={"content": "overwrite"},
            ).status_code,
            405,
        )

    def test_owner_isolation_and_owned_relations(self):
        document = self.create_from_message().json()
        self.current_user = self.other
        self.assertEqual(self.client.get(f"/contents/{document['id']}").status_code, 404)
        self.assertEqual(
            self.client.post(
                "/contents", json={"source_message_id": self.ai_message.id}
            ).status_code,
            404,
        )
        self.current_user = self.owner
        foreign_brand = self.client.patch(
            f"/contents/{document['id']}",
            json={"brand_id": self.other_brand.id},
        )
        self.assertEqual(foreign_brand.status_code, 404)
        foreign_campaign = self.client.patch(
            f"/contents/{document['id']}",
            json={"campaign_id": self.other_campaign.id},
        )
        self.assertEqual(foreign_campaign.status_code, 404)

    def test_brand_campaign_primary_and_delete_preserve_sources(self):
        document = self.create_from_message().json()
        linked = self.client.patch(
            f"/contents/{document['id']}",
            json={
                "brand_id": self.brand.id,
                "campaign_id": self.campaign.id,
                "is_campaign_primary": True,
            },
        )
        self.assertEqual(linked.status_code, 200)
        self.assertEqual(linked.json()["brand_name"], "DG Studio")
        self.assertEqual(linked.json()["campaign_name"], "Summer")
        self.assertTrue(linked.json()["is_campaign_primary"])
        second = self.client.post(
            "/contents",
            json={"source_saved_content_id": self.saved.id},
        ).json()
        second_linked = self.client.patch(
            f"/contents/{second['id']}",
            json={
                "campaign_id": self.campaign.id,
                "is_campaign_primary": True,
            },
        )
        self.assertEqual(second_linked.status_code, 200)
        self.assertFalse(
            self.client.get(f"/contents/{document['id']}").json()[
                "is_campaign_primary"
            ]
        )
        related = self.client.get(
            f"/contents/{document['id']}/campaign-contents"
        ).json()
        self.assertEqual([item["id"] for item in related], [second["id"]])
        deleted = self.client.delete(f"/contents/{document['id']}")
        self.assertEqual(deleted.status_code, 200)
        self.assertIsNotNone(self.db.get(Message, self.ai_message.id))
        self.assertIsNotNone(self.db.get(SavedContent, self.saved.id))

    @patch(
        "app.services.content_document_service.generate_structured_content",
        return_value='{"suggestion":"Bản đề xuất thân thiện"}',
    )
    def test_ai_rewrite_is_suggestion_only(self, generate):
        document = self.create_from_message().json()
        rewritten = self.client.post(
            f"/contents/{document['id']}/ai-rewrite",
            json={"action": "friendly", "selected_text": "Nội dung AI gốc."},
        )
        self.assertEqual(rewritten.status_code, 200)
        self.assertEqual(rewritten.json()["scope"], "selection")
        self.assertEqual(rewritten.json()["suggestion"], "Bản đề xuất thân thiện")
        unchanged = self.client.get(f"/contents/{document['id']}").json()
        self.assertEqual(unchanged["content"], document["content"])
        self.assertEqual(generate.call_count, 1)


if __name__ == "__main__":
    unittest.main()
