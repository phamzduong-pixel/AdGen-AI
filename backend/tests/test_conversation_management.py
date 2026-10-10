import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.conversation import router as conversation_router
from app.api.message import router as message_router
from app.api.upload import router as upload_router
from app.core.security import get_current_user
from app.database.database import Base
from app.database.database import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.schemas.message import MessageCreate
from app.schemas.message import AdBrief
from app.services.conversation_service import generate_conversation_title
from app.services.message_service import stream_message_service
from app.services.message_service import edit_message_stream_service
from app.schemas.message import MessageUpdate


class ConversationManagementApiTest(unittest.TestCase):
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
            username="owner",
            email="owner@example.com",
            hashed_password="not-used",
        )
        self.other_user = User(
            username="other",
            email="other@example.com",
            hashed_password="not-used",
        )
        self.db.add_all([self.owner, self.other_user])
        self.db.commit()
        self.db.refresh(self.owner)
        self.db.refresh(self.other_user)

        app = FastAPI()
        app.include_router(conversation_router)
        app.include_router(message_router)
        app.include_router(upload_router)

        def override_db():
            yield self.db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: self.owner
        self.client = TestClient(app)

    def tearDown(self):
        self.db.close()

    def test_rename_pin_sort_and_delete_with_message_cascade(self):
        first = self.client.post(
            "/conversations",
            json={"title": "  Chiến dịch   mùa hè  "},
        )
        self.assertEqual(first.status_code, 200)
        first_data = first.json()
        self.assertEqual(first_data["title"], "Chiến dịch mùa hè")
        self.assertFalse(first_data["is_pinned"])

        second = self.client.post(
            "/conversations",
            json={"title": "Hội thoại thứ hai"},
        )
        self.assertEqual(second.status_code, 200)
        second_id = second.json()["id"]

        renamed = self.client.put(
            f"/conversations/{first_data['id']}",
            json={"title": "  Tên   đã đổi  "},
        )
        self.assertEqual(renamed.status_code, 200)
        self.assertEqual(renamed.json()["title"], "Tên đã đổi")

        pinned = self.client.patch(
            f"/conversations/{first_data['id']}/pin",
            json={"is_pinned": True},
        )
        self.assertEqual(pinned.status_code, 200)
        self.assertTrue(pinned.json()["is_pinned"])

        conversations = self.client.get("/conversations")
        self.assertEqual(conversations.status_code, 200)
        self.assertEqual(conversations.json()[0]["id"], first_data["id"])

        message = Message(
            conversation_id=first_data["id"],
            role="user",
            content="Tin nhắn sẽ bị xóa",
        )
        self.db.add(message)
        self.db.commit()

        deleted = self.client.delete(
            f"/conversations/{first_data['id']}",
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(
            deleted.json()["conversation_id"],
            first_data["id"],
        )
        self.assertIsNone(
            self.db.query(Conversation)
            .filter(Conversation.id == first_data["id"])
            .first()
        )
        self.assertEqual(
            self.db.query(Message)
            .filter(Message.conversation_id == first_data["id"])
            .count(),
            0,
        )
        self.assertIsNotNone(
            self.db.query(Conversation)
            .filter(Conversation.id == second_id)
            .first()
        )

    def test_empty_title_and_non_owner_are_rejected(self):
        empty_title = self.client.post(
            "/conversations",
            json={"title": "    "},
        )
        self.assertEqual(empty_title.status_code, 422)

        other_conversation = Conversation(
            title="Không thuộc người dùng hiện tại",
            user_id=self.other_user.id,
        )
        self.db.add(other_conversation)
        self.db.commit()
        self.db.refresh(other_conversation)

        for method, path, payload in (
            (
                "put",
                f"/conversations/{other_conversation.id}",
                {"title": "Không được đổi"},
            ),
            (
                "patch",
                f"/conversations/{other_conversation.id}/pin",
                {"is_pinned": True},
            ),
            (
                "delete",
                f"/conversations/{other_conversation.id}",
                None,
            ),
        ):
            response = self.client.request(method.upper(), path, json=payload)
            self.assertEqual(response.status_code, 404)

    def test_first_ai_response_generates_title_and_manual_title_is_preserved(self):
        created = self.client.post(
            "/conversations",
            json={"title": "Cuộc trò chuyện mới"},
        )
        self.assertEqual(created.status_code, 200)
        conversation_id = created.json()["id"]
        first_content = (
            "  Hãy   viết nội dung quảng cáo\n"
            "cho sản phẩm cà phê mới ra mắt hôm nay  "
        )

        with patch(
            "app.services.message_service.stream_ai",
            return_value=iter(["Nội dung ", "phản hồi"]),
        ):
            response_chunks = list(
                stream_message_service(
                    message=MessageCreate(
                        conversation_id=conversation_id,
                        content=first_content,
                    ),
                    db=self.db,
                    current_user=self.owner,
                )
            )

        self.assertEqual("".join(response_chunks), "Nội dung phản hồi")
        self.db.expire_all()
        conversation = self.db.get(Conversation, conversation_id)
        self.assertEqual(
            conversation.title,
            "Hãy viết nội dung quảng cáo cho sản",
        )
        self.assertTrue(conversation.has_generated_title)
        self.assertFalse(conversation.is_title_custom)

        renamed = self.client.put(
            f"/conversations/{conversation_id}",
            json={"title": "Tên do người dùng đặt"},
        )
        self.assertEqual(renamed.status_code, 200)
        self.assertTrue(renamed.json()["is_title_custom"])

        with patch(
            "app.services.message_service.stream_ai",
            return_value=iter(["Phản hồi thứ hai"]),
        ):
            list(
                stream_message_service(
                    message=MessageCreate(
                        conversation_id=conversation_id,
                        content="Nội dung khác không được dùng làm tiêu đề",
                    ),
                    db=self.db,
                    current_user=self.owner,
                )
            )

        self.db.expire_all()
        self.assertEqual(
            self.db.get(Conversation, conversation_id).title,
            "Tên do người dùng đặt",
        )

    def test_generated_title_has_word_and_character_limits(self):
        title = generate_conversation_title(
            "Một hai ba bốn năm sáu bảy tám chín mười"
        )
        self.assertLessEqual(len(title.split()), 8)
        self.assertLessEqual(len(title), 50)

        long_title = generate_conversation_title(
            "Siêudàikhôngcókhoảngtrắngvàvượtquánămmươikýtự"
            "tiếptụcdàithêm"
        )
        self.assertLessEqual(len(long_title), 50)

    def test_upload_attachment_link_to_message_and_clear_messages(self):
        created = self.client.post(
            "/conversations",
            json={"title": "Cuộc trò chuyện mới"},
        )
        conversation_id = created.json()["id"]

        uploaded = self.client.post(
            f"/uploads/{conversation_id}",
            files={
                "file": (
                    "../../anh-quang-cao.png",
                    b"fake-png-content",
                    "image/png",
                )
            },
        )
        self.assertEqual(uploaded.status_code, 201)
        uploaded_data = uploaded.json()
        self.assertEqual(uploaded_data["filename"], "anh-quang-cao.png")
        self.assertEqual(uploaded_data["content_type"], "image/png")
        self.assertGreater(uploaded_data["size"], 0)

        with patch(
            "app.services.message_service.stream_ai",
            return_value=iter(["Đã nhận yêu cầu"]),
        ):
            list(
                stream_message_service(
                    message=MessageCreate(
                        conversation_id=conversation_id,
                        content="Viết nội dung cho ảnh đính kèm",
                        attachment_ids=[uploaded_data["id"]],
                    ),
                    db=self.db,
                    current_user=self.owner,
                )
            )

        messages = self.client.get(f"/messages/{conversation_id}")
        self.assertEqual(messages.status_code, 200)
        user_message = messages.json()[0]
        self.assertEqual(user_message["attachments"][0]["id"], uploaded_data["id"])

        downloaded = self.client.get(
            f"/uploads/file/{uploaded_data['id']}/download"
        )
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded.content, b"fake-png-content")

        cleared = self.client.delete(
            f"/messages/conversation/{conversation_id}"
        )
        self.assertEqual(cleared.status_code, 200)
        self.assertEqual(
            self.client.get(f"/messages/{conversation_id}").json(),
            [],
        )
        self.assertEqual(
            self.client.get(f"/uploads/{conversation_id}").json(),
            [],
        )

    def test_upload_rejects_invalid_mime_and_oversized_files(self):
        created = self.client.post(
            "/conversations",
            json={"title": "Kiểm tra upload"},
        )
        conversation_id = created.json()["id"]

        invalid_mime = self.client.post(
            f"/uploads/{conversation_id}",
            files={"file": ("image.png", b"content", "text/plain")},
        )
        self.assertEqual(invalid_mime.status_code, 400)

        with patch("app.services.upload_service.MAX_FILE_SIZE", 4):
            oversized = self.client.post(
                f"/uploads/{conversation_id}",
                files={"file": ("safe-name.txt", b"12345", "text/plain")},
            )

        self.assertEqual(oversized.status_code, 413)
        self.assertEqual(self.db.query(UploadedFile).count(), 0)

    def test_ad_brief_is_validated_stored_and_sent_to_ai_history(self):
        created = self.client.post(
            "/conversations",
            json={"title": "Cuộc trò chuyện mới"},
        )
        conversation_id = created.json()["id"]
        captured = {}

        def fake_stream_ai(history, prompt_type, custom_platform_name=None, brand_context="", product_context="", **kwargs):
            captured["history"] = history
            captured["prompt_type"] = prompt_type
            yield "Nội dung quảng cáo"

        brief = AdBrief(
            product_name="AdGen AI",
            description="Công cụ tạo nội dung quảng cáo đa nền tảng",
            target_audience="Marketer và chủ doanh nghiệp",
            objective="Tăng chuyển đổi/bán hàng",
            platform="facebook",
            tone="Chuyên nghiệp",
            length="Ngắn",
            keywords="AI, quảng cáo",
            cta="Dùng thử ngay",
            language="Tiếng Việt",
        )

        with patch(
            "app.services.message_service.stream_ai",
            side_effect=fake_stream_ai,
        ):
            list(
                stream_message_service(
                    message=MessageCreate(
                        conversation_id=conversation_id,
                        content="Tạo một mẫu quảng cáo",
                        prompt_type="facebook",
                        ad_brief=brief,
                    ),
                    db=self.db,
                    current_user=self.owner,
                )
            )

        self.assertEqual(captured["prompt_type"], "facebook")
        self.assertEqual(
            captured["history"][-1]["ad_brief"]["product_name"],
            "AdGen AI",
        )
        stored_message = (
            self.db.query(Message)
            .filter(
                Message.conversation_id == conversation_id,
                Message.role == "user",
            )
            .one()
        )
        self.assertIn("AdGen AI", stored_message.ad_brief_json)
        self.assertEqual(stored_message.prompt_type, "facebook")

        invalid = self.client.post(
            "/messages",
            json={
                "conversation_id": conversation_id,
                "content": "Tạo quảng cáo",
                "ad_brief": {
                    "product_name": " ",
                    "description": "\n",
                },
            },
        )
        self.assertEqual(invalid.status_code, 422)

    def test_stopping_stream_saves_partial_but_never_empty_assistant(self):
        created = self.client.post(
            "/conversations",
            json={"title": "Cuộc trò chuyện mới"},
        )
        conversation_id = created.json()["id"]

        with patch(
            "app.services.message_service.stream_ai",
            return_value=iter(["Phần nội dung đã tạo", " không được nhận"]),
        ):
            generator = stream_message_service(
                message=MessageCreate(
                    conversation_id=conversation_id,
                    content="Tạo nội dung",
                ),
                db=self.db,
                current_user=self.owner,
            )
            self.assertEqual(next(generator), "Phần nội dung đã tạo")
            generator.close()

        partial = (
            self.db.query(Message)
            .filter(
                Message.conversation_id == conversation_id,
                Message.role == "assistant",
            )
            .one()
        )
        self.assertEqual(partial.content, "Phần nội dung đã tạo")

        second = self.client.post(
            "/conversations",
            json={"title": "Cuộc trò chuyện mới"},
        )
        second_id = second.json()["id"]
        with patch(
            "app.services.message_service.stream_ai",
            return_value=iter(["Không được bắt đầu"]),
        ):
            never_started = stream_message_service(
                message=MessageCreate(
                    conversation_id=second_id,
                    content="Dừng ngay",
                ),
                db=self.db,
                current_user=self.owner,
            )
            never_started.close()

        self.assertEqual(
            self.db.query(Message)
            .filter(
                Message.conversation_id == second_id,
                Message.role == "assistant",
            )
            .count(),
            0,
        )

        user_message = (
            self.db.query(Message)
            .filter(
                Message.conversation_id == conversation_id,
                Message.role == "user",
            )
            .first()
        )
        with patch(
            "app.services.message_service.stream_ai",
            return_value=iter(["Bản chỉnh sửa một phần", " phần còn lại"]),
        ):
            edited = edit_message_stream_service(
                message_id=user_message.id,
                message_data=MessageUpdate(content="Nội dung đã chỉnh sửa"),
                db=self.db,
                current_user=self.owner,
            )
            self.assertEqual(next(edited), "Bản chỉnh sửa một phần")
            edited.close()

        latest_assistant = (
            self.db.query(Message)
            .filter(
                Message.conversation_id == conversation_id,
                Message.role == "assistant",
            )
            .order_by(Message.id.desc())
            .first()
        )
        # CP-8 keeps the prior completed assistant when an edit stream is
        # cancelled; the partial replacement is not a completed response.
        self.assertEqual(latest_assistant.content, "Phần nội dung đã tạo")


if __name__ == "__main__":
    unittest.main()
