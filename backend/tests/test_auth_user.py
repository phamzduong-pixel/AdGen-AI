import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from jose import jwt

from app.api.auth import router as auth_router
from app.api.user import router as user_router
from app.database.database import Base
from app.database.database import get_db
from app.core.config import settings
from app.models.campaign import Campaign  # noqa: F401
from app.models.content_activity import ContentActivity  # noqa: F401
from app.models.conversation import Conversation  # noqa: F401
from app.models.message import Message  # noqa: F401
from app.models.saved_content import SavedContent  # noqa: F401
from app.models.uploaded_file import UploadedFile  # noqa: F401
from app.models.user_settings import UserSettings  # noqa: F401
from app.services.file_storage import LocalFileStorage


class AuthUserApiTest(unittest.TestCase):
    def setUp(self):
        self.original_google_client_id = settings.GOOGLE_CLIENT_ID
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.session_factory = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
        app = FastAPI()
        app.include_router(auth_router)
        app.include_router(user_router)

        def override_db():
            db = self.session_factory()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)

    def tearDown(self):
        settings.GOOGLE_CLIENT_ID = self.original_google_client_id
        self.client.close()
        self.engine.dispose()

    def register(self, username="tester", email="tester@example.com"):
        response = self.client.post(
            "/auth/register",
            json={
                "username": username,
                "email": email,
                "password": "password123",
            },
        )
        if response.status_code == 200:
            from app.models.user import User

            with self.session_factory() as db:
                user = db.query(User).filter(User.email == email).first()
                user.email_verified = True
                db.commit()
        return response

    def login(self, username="tester", password="password123"):
        return self.client.post(
            "/auth/login",
            data={"username": username, "password": password},
        )

    def test_register_duplicates_login_and_unauthorized(self):
        response = self.register()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("hashed_password", response.json())
        self.assertNotIn("password", response.json())

        self.assertEqual(self.register().status_code, 400)
        self.assertEqual(
            self.register(username="other", email="tester@example.com").status_code,
            400,
        )
        self.assertEqual(self.login().status_code, 200)
        self.assertEqual(self.login(password="wrong-password").status_code, 401)
        self.assertEqual(
            self.login(username="tester@example.com").status_code,
            200,
        )
        self.assertEqual(self.login(username="missing").status_code, 404)
        self.assertEqual(self.client.get("/users/me").status_code, 401)

    def test_avatar_upload_is_private_and_can_be_removed(self):
        self.register()
        self.register("other", "other@example.com")
        owner_token = self.login().json()["access_token"]
        other_token = self.login("other").json()["access_token"]
        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        other_headers = {"Authorization": f"Bearer {other_token}"}
        png = b"\x89PNG\r\n\x1a\n" + b"test-avatar"

        with TemporaryDirectory() as temporary_directory:
            storage = LocalFileStorage(Path(temporary_directory))
            with patch("app.api.user.file_storage", storage):
                uploaded = self.client.post(
                    "/users/me/avatar",
                    headers=owner_headers,
                    files={"file": ("avatar.png", png, "image/png")},
                )
                self.assertEqual(uploaded.status_code, 200)
                self.assertEqual(uploaded.json()["avatar_url"], "/users/me/avatar")
                self.assertEqual(self.client.get("/users/me/avatar").status_code, 401)

                owner_image = self.client.get("/users/me/avatar", headers=owner_headers)
                self.assertEqual(owner_image.status_code, 200)
                self.assertEqual(owner_image.content, png)
                self.assertEqual(self.client.get("/users/me/avatar", headers=other_headers).status_code, 404)

                rejected = self.client.post(
                    "/users/me/avatar",
                    headers=owner_headers,
                    files={"file": ("not-an-image.txt", b"text", "text/plain")},
                )
                self.assertEqual(rejected.status_code, 400)

                removed = self.client.delete("/users/me/avatar", headers=owner_headers)
                self.assertEqual(removed.status_code, 200)
                self.assertIsNone(removed.json()["avatar_url"])
                self.assertEqual(self.client.get("/users/me/avatar", headers=owner_headers).status_code, 404)
    def test_google_config_exposes_only_a_valid_public_client_id(self):
        settings.GOOGLE_CLIENT_ID = "123456789-testclient.apps.googleusercontent.com"
        configured = self.client.get("/auth/google/config")
        self.assertEqual(configured.status_code, 200)
        self.assertRegex(
            configured.json()["client_id"],
            r"^\d+-[A-Za-z0-9_-]+\.apps\.googleusercontent\.com$",
        )

        settings.GOOGLE_CLIENT_ID = ""
        unavailable = self.client.get("/auth/google/config")
        self.assertEqual(unavailable.status_code, 200)
        self.assertIsNone(unavailable.json()["client_id"])
    @patch("app.services.google_auth_service._verify_google_id_token")
    def test_google_login_creates_new_user(self, verify_token):
        settings.GOOGLE_CLIENT_ID = (
            "123456789-testclient.apps.googleusercontent.com"
        )
        verify_token.return_value = {
            "sub": "google-user-1",
            "email": "google@example.com",
            "email_verified": True,
            "name": "Google Tester",
            "picture": "https://example.com/avatar.png",
        }

        response = self.client.post(
            "/auth/google",
            json={"credential": "valid-google-credential-value"},
        )
        self.assertEqual(response.status_code, 200)
        verify_token.assert_called_once_with(
            "valid-google-credential-value",
            settings.GOOGLE_CLIENT_ID,
        )
        token = response.json()["access_token"]
        me = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["email"], "google@example.com")
        self.assertEqual(me.json()["auth_provider"], "google")
        self.assertTrue(me.json()["email_verified"])
        self.assertNotIn("google_sub", me.json())
        self.assertNotIn("hashed_password", me.json())
        self.assertEqual(
            self.login(username="google@example.com").status_code,
            400,
        )

    def test_avatar_upload_is_private_and_can_be_removed(self):
        self.register()
        self.register("other", "other@example.com")
        owner_token = self.login().json()["access_token"]
        other_token = self.login("other").json()["access_token"]
        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        other_headers = {"Authorization": f"Bearer {other_token}"}
        png = b"\x89PNG\r\n\x1a\n" + b"test-avatar"

        with TemporaryDirectory() as temporary_directory:
            storage = LocalFileStorage(Path(temporary_directory))
            with patch("app.api.user.file_storage", storage):
                uploaded = self.client.post(
                    "/users/me/avatar",
                    headers=owner_headers,
                    files={"file": ("avatar.png", png, "image/png")},
                )
                self.assertEqual(uploaded.status_code, 200)
                self.assertEqual(uploaded.json()["avatar_url"], "/users/me/avatar")
                self.assertEqual(self.client.get("/users/me/avatar").status_code, 401)

                owner_image = self.client.get("/users/me/avatar", headers=owner_headers)
                self.assertEqual(owner_image.status_code, 200)
                self.assertEqual(owner_image.content, png)
                self.assertEqual(self.client.get("/users/me/avatar", headers=other_headers).status_code, 404)

                rejected = self.client.post(
                    "/users/me/avatar",
                    headers=owner_headers,
                    files={"file": ("not-an-image.txt", b"text", "text/plain")},
                )
                self.assertEqual(rejected.status_code, 400)

                removed = self.client.delete("/users/me/avatar", headers=owner_headers)
                self.assertEqual(removed.status_code, 200)
                self.assertIsNone(removed.json()["avatar_url"])
                self.assertEqual(self.client.get("/users/me/avatar", headers=owner_headers).status_code, 404)
    def test_google_config_exposes_only_a_valid_public_client_id(self):
        settings.GOOGLE_CLIENT_ID = "123456789-testclient.apps.googleusercontent.com"
        configured = self.client.get("/auth/google/config")
        self.assertEqual(configured.status_code, 200)
        self.assertRegex(
            configured.json()["client_id"],
            r"^\d+-[A-Za-z0-9_-]+\.apps\.googleusercontent\.com$",
        )

        settings.GOOGLE_CLIENT_ID = ""
        unavailable = self.client.get("/auth/google/config")
        self.assertEqual(unavailable.status_code, 200)
        self.assertIsNone(unavailable.json()["client_id"])
    @patch("app.services.google_auth_service._verify_google_id_token")
    def test_google_login_links_existing_email_without_duplicate(self, verify_token):
        self.register()
        with self.session_factory() as db:
            from app.models.user import User

            user = db.query(User).one()
            user.email_verified = False
            db.commit()
        settings.GOOGLE_CLIENT_ID = (
            "123456789-testclient.apps.googleusercontent.com"
        )
        verify_token.return_value = {
            "sub": "existing-google-sub",
            "email": "tester@example.com",
            "email_verified": True,
            "name": "Tester",
            "hd": "example.com",
        }

        first = self.client.post(
            "/auth/google",
            json={"credential": "valid-existing-user-token"},
        )
        second = self.client.post(
            "/auth/google",
            json={"credential": "valid-existing-user-token"},
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(self.login().status_code, 200)
        with self.session_factory() as db:
            from app.models.user import User

            self.assertEqual(db.query(User).count(), 1)
            user = db.query(User).one()
            self.assertEqual(user.google_sub, "existing-google-sub")
            self.assertEqual(user.auth_provider, "local")
            self.assertTrue(user.email_verified)

    def test_avatar_upload_is_private_and_can_be_removed(self):
        self.register()
        self.register("other", "other@example.com")
        owner_token = self.login().json()["access_token"]
        other_token = self.login("other").json()["access_token"]
        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        other_headers = {"Authorization": f"Bearer {other_token}"}
        png = b"\x89PNG\r\n\x1a\n" + b"test-avatar"

        with TemporaryDirectory() as temporary_directory:
            storage = LocalFileStorage(Path(temporary_directory))
            with patch("app.api.user.file_storage", storage):
                uploaded = self.client.post(
                    "/users/me/avatar",
                    headers=owner_headers,
                    files={"file": ("avatar.png", png, "image/png")},
                )
                self.assertEqual(uploaded.status_code, 200)
                self.assertEqual(uploaded.json()["avatar_url"], "/users/me/avatar")
                self.assertEqual(self.client.get("/users/me/avatar").status_code, 401)

                owner_image = self.client.get("/users/me/avatar", headers=owner_headers)
                self.assertEqual(owner_image.status_code, 200)
                self.assertEqual(owner_image.content, png)
                self.assertEqual(self.client.get("/users/me/avatar", headers=other_headers).status_code, 404)

                rejected = self.client.post(
                    "/users/me/avatar",
                    headers=owner_headers,
                    files={"file": ("not-an-image.txt", b"text", "text/plain")},
                )
                self.assertEqual(rejected.status_code, 400)

                removed = self.client.delete("/users/me/avatar", headers=owner_headers)
                self.assertEqual(removed.status_code, 200)
                self.assertIsNone(removed.json()["avatar_url"])
                self.assertEqual(self.client.get("/users/me/avatar", headers=owner_headers).status_code, 404)
    def test_google_config_exposes_only_a_valid_public_client_id(self):
        settings.GOOGLE_CLIENT_ID = "123456789-testclient.apps.googleusercontent.com"
        configured = self.client.get("/auth/google/config")
        self.assertEqual(configured.status_code, 200)
        self.assertRegex(
            configured.json()["client_id"],
            r"^\d+-[A-Za-z0-9_-]+\.apps\.googleusercontent\.com$",
        )

        settings.GOOGLE_CLIENT_ID = ""
        unavailable = self.client.get("/auth/google/config")
        self.assertEqual(unavailable.status_code, 200)
        self.assertIsNone(unavailable.json()["client_id"])
    @patch("app.services.google_auth_service._verify_google_id_token")
    def test_google_login_rejects_invalid_token(self, verify_token):
        settings.GOOGLE_CLIENT_ID = (
            "123456789-testclient.apps.googleusercontent.com"
        )
        verify_token.side_effect = ValueError("signature details stay private")
        response = self.client.post(
            "/auth/google",
            json={"credential": "invalid-google-credential"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json()["detail"],
            "Không thể xác minh tài khoản Google",
        )
        self.assertNotIn("signature", response.text)

    def test_google_login_without_client_id_is_disabled(self):
        settings.GOOGLE_CLIENT_ID = ""
        response = self.client.post(
            "/auth/google",
            json={"credential": "credential-long-enough-for-schema"},
        )
        self.assertEqual(response.status_code, 503)

    def test_avatar_upload_is_private_and_can_be_removed(self):
        self.register()
        self.register("other", "other@example.com")
        owner_token = self.login().json()["access_token"]
        other_token = self.login("other").json()["access_token"]
        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        other_headers = {"Authorization": f"Bearer {other_token}"}
        png = b"\x89PNG\r\n\x1a\n" + b"test-avatar"

        with TemporaryDirectory() as temporary_directory:
            storage = LocalFileStorage(Path(temporary_directory))
            with patch("app.api.user.file_storage", storage):
                uploaded = self.client.post(
                    "/users/me/avatar",
                    headers=owner_headers,
                    files={"file": ("avatar.png", png, "image/png")},
                )
                self.assertEqual(uploaded.status_code, 200)
                self.assertEqual(uploaded.json()["avatar_url"], "/users/me/avatar")
                self.assertEqual(self.client.get("/users/me/avatar").status_code, 401)

                owner_image = self.client.get("/users/me/avatar", headers=owner_headers)
                self.assertEqual(owner_image.status_code, 200)
                self.assertEqual(owner_image.content, png)
                self.assertEqual(self.client.get("/users/me/avatar", headers=other_headers).status_code, 404)

                rejected = self.client.post(
                    "/users/me/avatar",
                    headers=owner_headers,
                    files={"file": ("not-an-image.txt", b"text", "text/plain")},
                )
                self.assertEqual(rejected.status_code, 400)

                removed = self.client.delete("/users/me/avatar", headers=owner_headers)
                self.assertEqual(removed.status_code, 200)
                self.assertIsNone(removed.json()["avatar_url"])
                self.assertEqual(self.client.get("/users/me/avatar", headers=owner_headers).status_code, 404)
    def test_google_config_exposes_only_a_valid_public_client_id(self):
        settings.GOOGLE_CLIENT_ID = "123456789-testclient.apps.googleusercontent.com"
        configured = self.client.get("/auth/google/config")
        self.assertEqual(configured.status_code, 200)
        self.assertRegex(
            configured.json()["client_id"],
            r"^\d+-[A-Za-z0-9_-]+\.apps\.googleusercontent\.com$",
        )

        settings.GOOGLE_CLIENT_ID = ""
        unavailable = self.client.get("/auth/google/config")
        self.assertEqual(unavailable.status_code, 200)
        self.assertIsNone(unavailable.json()["client_id"])
    @patch("app.services.google_auth_service._verify_google_id_token")
    def test_google_login_rejects_placeholder_client_id(self, verify_token):
        settings.GOOGLE_CLIENT_ID = (
            "123456789-.........apps.googleusercontent.com"
        )
        response = self.client.post(
            "/auth/google",
            json={"credential": "credential-long-enough-for-schema"},
        )
        self.assertEqual(response.status_code, 503)
        verify_token.assert_not_called()

    def test_expired_jwt_is_rejected(self):
        self.register()
        expired = jwt.encode(
            {
                "sub": "1",
                "ver": 0,
                "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        response = self.client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {expired}"},
        )
        self.assertEqual(response.status_code, 401)

    def test_profile_update_settings_and_duplicate_protection(self):
        self.register()
        self.register("second", "second@example.com")
        token = self.login().json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        profile = self.client.get("/users/me", headers=headers)
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.json()["total_conversations"], 0)

        updated = self.client.patch(
            "/users/me",
            headers=headers,
            json={"username": "renamed", "email": "tester@example.com"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["username"], "renamed")

        duplicate = self.client.patch(
            "/users/me",
            headers=headers,
            json={"username": "second", "email": "tester@example.com"},
        )
        self.assertEqual(duplicate.status_code, 409)

        changed_email = self.client.patch(
            "/users/me",
            headers=headers,
            json={"username": "renamed", "email": "renamed@example.com"},
        )
        self.assertEqual(changed_email.status_code, 200)
        self.assertTrue(changed_email.json()["email_verified"])
        self.assertEqual(
            self.client.get("/users/me", headers=headers).status_code,
            200,
        )
        settings = self.client.put(
            "/users/me/settings",
            headers=headers,
            json={
                "default_platform": "tiktok",
                "default_tone": "creative",
                "default_language": "vi",
                "default_length": "short",
                "default_export_format": "txt",
                "include_timestamps": False,
            },
        )
        self.assertEqual(settings.status_code, 200)
        self.assertEqual(settings.json()["default_platform"], "tiktok")

    def test_password_change_invalidates_existing_token(self):
        self.register()
        token = self.login().json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        wrong = self.client.post(
            "/users/me/change-password",
            headers=headers,
            json={
                "current_password": "wrong-password",
                "new_password": "new-password-123",
                "confirm_password": "new-password-123",
            },
        )
        self.assertEqual(wrong.status_code, 400)

        changed = self.client.post(
            "/users/me/change-password",
            headers=headers,
            json={
                "current_password": "password123",
                "new_password": "new-password-123",
                "confirm_password": "new-password-123",
            },
        )
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(self.client.get("/users/me", headers=headers).status_code, 401)
        self.assertEqual(
            self.login(password="new-password-123").status_code,
            200,
        )


if __name__ == "__main__":
    unittest.main()
