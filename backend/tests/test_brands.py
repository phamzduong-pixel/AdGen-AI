import json
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.brand import router as brand_router
from app.api.campaign import router as campaign_router
from app.core.security import get_current_user
from app.database.database import Base, get_db
from app.models.brand import BrandProfile
from app.models.campaign import Campaign
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.saved_content import SavedContent
from app.models.user import User
from app.schemas.message import MessageCreate
from app.services.message_service import stream_message_service


class BrandApiTest(unittest.TestCase):
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
            username="brand-owner",
            email="brand-owner@example.com",
            hashed_password="unused",
            email_verified=True,
        )
        self.other = User(
            username="brand-other",
            email="brand-other@example.com",
            hashed_password="unused",
            email_verified=True,
        )
        self.db.add_all([self.owner, self.other])
        self.db.commit()
        self.current_user = self.owner

        app = FastAPI()
        app.include_router(brand_router)
        app.include_router(campaign_router)
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.current_user
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.db.close()
        self.engine.dispose()

    def create_brand(self, name="DG Studio", **extra):
        payload = {
            "name": name,
            "industry": "Marketing",
            "website": "https://example.com",
            "primary_color": "#4F46E5",
            "keywords": ["sáng tạo", "AI"],
            "forbidden_words": ["rẻ nhất"],
            **extra,
        }
        return self.client.post("/brands", json=payload)

    def test_crud_default_and_owner_isolation(self):
        first = self.create_brand()
        self.assertEqual(first.status_code, 201)
        self.assertTrue(first.json()["is_default"])
        second = self.create_brand("DG Commerce", is_default=True)
        self.assertEqual(second.status_code, 201)
        self.assertTrue(second.json()["is_default"])
        listed = self.client.get("/brands").json()
        self.assertEqual(sum(item["is_default"] for item in listed), 1)

        updated = self.client.patch(
            f"/brands/{first.json()['id']}",
            json={"slogan": "Sáng tạo khác biệt", "secondary_color": "#111827"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["slogan"], "Sáng tạo khác biệt")
        defaulted = self.client.patch(
            f"/brands/{first.json()['id']}/default"
        )
        self.assertTrue(defaulted.json()["is_default"])
        self.assertEqual(
            sum(item["is_default"] for item in self.client.get("/brands").json()),
            1,
        )

        self.current_user = self.other
        self.assertEqual(
            self.client.get(f"/brands/{first.json()['id']}").status_code,
            404,
        )
        self.assertEqual(
            self.client.patch(
                f"/brands/{first.json()['id']}", json={"name": "Stolen"}
            ).status_code,
            404,
        )

    @patch("app.services.message_service.stream_ai")
    def test_brand_context_reaches_ai_and_is_snapshotted(self, stream_ai):
        brand_response = self.create_brand(
            target_audience="Chủ doanh nghiệp nhỏ",
            default_tone="Chuyên nghiệp",
            preferred_cta="Dùng thử ngay",
            writing_guidelines="Viết rõ ràng, tránh phóng đại.",
        )
        brand_id = brand_response.json()["id"]
        conversation = Conversation(
            title="Brand content",
            user_id=self.owner.id,
        )
        self.db.add(conversation)
        self.db.commit()
        captured = {}

        def fake_stream(history, prompt_type, custom_platform_name=None, brand_context="", product_context="", **kwargs):
            captured["history"] = history
            captured["brand_context"] = brand_context
            yield "Nội dung đúng thương hiệu"

        stream_ai.side_effect = fake_stream
        output = "".join(
            stream_message_service(
                MessageCreate(
                    conversation_id=conversation.id,
                    brand_id=brand_id,
                    content="Viết quảng cáo",
                    prompt_type="facebook",
                ),
                self.db,
                self.owner,
            )
        )
        self.assertEqual(output, "Nội dung đúng thương hiệu")
        self.assertIn("<brand_data>", captured["brand_context"])
        self.assertIn("Chủ doanh nghiệp nhỏ", captured["brand_context"])
        self.db.expire_all()
        self.assertEqual(self.db.get(Conversation, conversation.id).brand_id, brand_id)
        messages = self.db.query(Message).order_by(Message.id).all()
        self.assertEqual({message.brand_id for message in messages}, {brand_id})

    @patch("app.services.brand_service.generate_structured_content")
    def test_check_content_campaign_and_safe_delete(self, generate):
        brand = self.create_brand().json()
        generate.return_value = json.dumps(
            {
                "score": 88,
                "is_consistent": True,
                "issues": [],
                "suggestions": ["Giữ CTA rõ hơn"],
                "matched_guidelines": ["Đúng giọng văn"],
            },
            ensure_ascii=False,
        )
        checked = self.client.post(
            f"/brands/{brand['id']}/check-content",
            json={"content": "Khám phá giải pháp sáng tạo", "platform": "facebook"},
        )
        self.assertEqual(checked.status_code, 200)
        self.assertEqual(checked.json()["score"], 88)

        campaign = self.client.post(
            "/campaigns",
            json={"name": "Launch", "brand_id": brand["id"]},
        )
        self.assertEqual(campaign.status_code, 201)
        self.assertEqual(campaign.json()["brand_id"], brand["id"])

        conversation = Conversation(
            title="Keep",
            user_id=self.owner.id,
            brand_id=brand["id"],
        )
        self.db.add(conversation)
        self.db.flush()
        saved = SavedContent(
            user_id=self.owner.id,
            conversation_id=conversation.id,
            brand_id=brand["id"],
            title="Keep content",
            content="Never delete",
        )
        self.db.add(saved)
        self.db.commit()
        saved_id = saved.id
        campaign_id = campaign.json()["id"]

        deleted = self.client.delete(f"/brands/{brand['id']}")
        self.assertEqual(deleted.status_code, 200)
        self.db.expire_all()
        self.assertIsNotNone(self.db.get(SavedContent, saved_id))
        self.assertIsNotNone(self.db.get(Campaign, campaign_id))
        self.assertIsNone(self.db.get(SavedContent, saved_id).brand_id)
        self.assertIsNone(self.db.get(Campaign, campaign_id).brand_id)

    def test_validation_and_foreign_brand_campaign_are_rejected(self):
        invalid_url = self.create_brand(website="javascript:alert(1)")
        self.assertEqual(invalid_url.status_code, 422)
        invalid_color = self.create_brand(primary_color="purple")
        self.assertEqual(invalid_color.status_code, 422)
        other_brand = BrandProfile(
            user_id=self.other.id,
            name="Private",
            keywords_json="[]",
            forbidden_words_json="[]",
        )
        self.db.add(other_brand)
        self.db.commit()
        response = self.client.post(
            "/campaigns",
            json={"name": "Invalid", "brand_id": other_brand.id},
        )
        self.assertEqual(response.status_code, 404)

    def test_asset_upload_download_delete_and_owner_isolation(self):
        brand = self.create_brand().json()
        uploaded = self.client.post(
            f"/brands/{brand['id']}/assets",
            files={"file": ("logo.png", b"\x89PNG\r\n\x1a\n", "image/png")},
        )
        self.assertEqual(uploaded.status_code, 201)
        asset = uploaded.json()
        downloaded = self.client.get(asset["file_url"])
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded.content, b"\x89PNG\r\n\x1a\n")

        rejected = self.client.post(
            f"/brands/{brand['id']}/assets",
            files={"file": ("unsafe.exe", b"MZ", "application/octet-stream")},
        )
        self.assertEqual(rejected.status_code, 400)

        self.current_user = self.other
        self.assertEqual(self.client.get(asset["file_url"]).status_code, 404)
        self.current_user = self.owner
        deleted = self.client.delete(
            f"/brands/{brand['id']}/assets/{asset['id']}"
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(self.client.get(asset["file_url"]).status_code, 404)


if __name__ == "__main__":
    unittest.main()
