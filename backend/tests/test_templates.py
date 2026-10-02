import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.template import router as template_router
from app.core.security import get_current_user
from app.data.system_templates import SYSTEM_AD_TEMPLATES
from app.database.database import Base
from app.database.database import get_db
from app.models.conversation import Conversation
from app.models.saved_content import SavedContent
from app.models.user import User
from app.services.template_service import seed_system_templates


class TemplateApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.Session = sessionmaker(bind=cls.engine)
        Base.metadata.create_all(bind=cls.engine)

    def setUp(self):
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.Session()
        self.owner = User(
            username="template-owner",
            email="template-owner@example.com",
            hashed_password="unused",
        )
        self.other = User(
            username="template-other",
            email="template-other@example.com",
            hashed_password="unused",
        )
        self.db.add_all([self.owner, self.other])
        self.db.commit()
        seed_system_templates(self.db)
        self.current_user = self.owner

        app = FastAPI()
        app.include_router(template_router)

        def override_db():
            yield self.db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: self.current_user
        self.client = TestClient(app)

    def tearDown(self):
        self.db.close()

    def test_list_search_filter_and_favorites_are_user_scoped(self):
        templates = self.client.get("/templates")
        self.assertEqual(templates.status_code, 200)
        template_payloads = templates.json()
        required_fields = {
            "title",
            "description",
            "platform",
            "category",
            "prompt_template",
            "default_tone",
            "default_length",
            "suggested_cta",
        }
        system_keys = [item["system_key"] for item in SYSTEM_AD_TEMPLATES]
        self.assertGreater(len(SYSTEM_AD_TEMPLATES), 0)
        self.assertEqual(len(system_keys), len(set(system_keys)))
        self.assertEqual(len(template_payloads), len(SYSTEM_AD_TEMPLATES))
        self.assertEqual(
            len({template["id"] for template in template_payloads}),
            len(template_payloads),
        )
        for template in template_payloads:
            self.assertTrue(required_fields.issubset(template))
            for field in required_fields:
                self.assertTrue(template[field], f"{field} must not be empty")

        filtered = self.client.get(
            "/templates",
            params={
                "search": "khóa học",
                "platform": "google_ads",
                "category": "Thu hút khách hàng tiềm năng",
            },
        )
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(len(filtered.json()), 1)
        template_id = filtered.json()[0]["id"]

        first = self.client.post(f"/templates/{template_id}/favorite")
        second = self.client.post(f"/templates/{template_id}/favorite")
        self.assertTrue(first.json()["is_favorite"])
        self.assertTrue(second.json()["is_favorite"])
        self.assertEqual(len(self.client.get("/templates/favorites").json()), 1)

        self.current_user = self.other
        self.assertEqual(self.client.get("/templates/favorites").json(), [])

        self.current_user = self.owner
        removed = self.client.delete(f"/templates/{template_id}/favorite")
        self.assertFalse(removed.json()["is_favorite"])

    def test_custom_template_crud_clone_and_ownership(self):
        system_template = self.client.get(
            "/templates",
            params={"scope": "system", "popular_only": True},
        ).json()[0]
        cloned = self.client.post(
            "/templates/custom",
            json={
                "title": "Bản sao riêng",
                "source_template_id": system_template["id"],
            },
        )
        self.assertEqual(cloned.status_code, 201)
        custom = cloned.json()
        self.assertFalse(custom["is_system"])
        self.assertTrue(custom["is_owner"])
        self.assertEqual(
            custom["prompt_template"],
            system_template["prompt_template"],
        )

        updated = self.client.patch(
            f"/templates/custom/{custom['id']}",
            json={"title": "Mẫu đã chỉnh sửa"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["title"], "Mẫu đã chỉnh sửa")

        cannot_edit_system = self.client.patch(
            f"/templates/custom/{system_template['id']}",
            json={"title": "Không hợp lệ"},
        )
        self.assertEqual(cannot_edit_system.status_code, 404)

        self.current_user = self.other
        self.assertEqual(
            self.client.get(f"/templates/{custom['id']}").status_code,
            404,
        )
        self.assertEqual(
            self.client.delete(
                f"/templates/custom/{custom['id']}"
            ).status_code,
            404,
        )

        self.current_user = self.owner
        deleted = self.client.delete(f"/templates/custom/{custom['id']}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(
            self.client.get(f"/templates/{custom['id']}").status_code,
            404,
        )

    def test_create_template_from_owned_saved_content(self):
        conversation = Conversation(
            title="Nguồn nội dung",
            user_id=self.owner.id,
        )
        self.db.add(conversation)
        self.db.commit()
        saved = SavedContent(
            user_id=self.owner.id,
            conversation_id=conversation.id,
            title="Nội dung nguồn",
            content="Nội dung quảng cáo đã được lưu.",
            platform="facebook",
        )
        self.db.add(saved)
        self.db.commit()

        response = self.client.post(
            "/templates/custom",
            json={
                "title": "Mẫu từ thư viện",
                "source_saved_content_id": saved.id,
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json()["prompt_template"],
            saved.content,
        )

        self.current_user = self.other
        rejected = self.client.post(
            "/templates/custom",
            json={
                "title": "Không được tạo",
                "source_saved_content_id": saved.id,
            },
        )
        self.assertEqual(rejected.status_code, 404)


if __name__ == "__main__":
    unittest.main()
