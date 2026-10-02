import unittest
from datetime import datetime
from datetime import timedelta
from unittest.mock import patch

from app.core.datetime_utils import utc_now

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.auth import router as auth_router
from app.core.config import settings
from app.database.database import Base
from app.database.database import get_db
from app.models.email_verification import EmailVerificationToken
from app.models.user import User
from app.models.user_session import UserSession
from app.services.email_service import email_provider
from app.services.email_verification_service import verification_rate_limiter


class EmailVerificationSessionApiTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.session_factory = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
        app = FastAPI()
        app.include_router(auth_router)

        def override_db():
            db = self.session_factory()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)
        self.codes = {}
        verification_rate_limiter.clear()
        self.config_patch = patch.object(
            email_provider,
            "ensure_configured",
            return_value=None,
        )
        self.send_patch = patch.object(
            email_provider,
            "send_verification_code",
            side_effect=self._capture_code,
        )
        self.config_patch.start()
        self.send_patch.start()

    def tearDown(self):
        self.config_patch.stop()
        self.send_patch.stop()
        verification_rate_limiter.clear()
        self.client.close()
        self.engine.dispose()

    def _capture_code(self, recipient, code, expires_minutes):
        self.codes[recipient] = code
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())
        self.assertEqual(
            expires_minutes,
            settings.EMAIL_VERIFICATION_EXPIRE_MINUTES,
        )

    def register(self, username="tester", email="tester@example.com"):
        return self.client.post(
            "/auth/register",
            json={
                "username": username,
                "email": email,
                "password": "password123",
            },
        )

    def login(self, username="tester", password="password123", user_agent=None):
        headers = {"User-Agent": user_agent} if user_agent else {}
        return self.client.post(
            "/auth/login",
            data={"username": username, "password": password},
            headers=headers,
        )

    def verify(self, email="tester@example.com", code=None):
        return self.client.post(
            "/auth/verify-email",
            json={"email": email, "code": code or self.codes[email]},
        )

    def test_registration_sends_hashed_single_use_code_and_enables_login(self):
        response = self.register()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["email_verified"])
        self.assertEqual(self.login().status_code, 200)

        with self.session_factory() as db:
            user = db.query(User).filter(User.email == "tester@example.com").first()
            user.email_verified = False
            db.commit()

        # Explicitly request verification code
        send_res = self.client.post(
            "/auth/send-verification-code",
            json={"email": "tester@example.com"},
        )
        self.assertEqual(send_res.status_code, 200)
        self.assertIn("tester@example.com", self.codes)

        verified = self.verify()
        self.assertEqual(verified.status_code, 200)
        self.assertEqual(self.login().status_code, 200)
        self.assertEqual(self.verify().status_code, 400)
        with self.session_factory() as db:
            record = db.query(EmailVerificationToken).one()
            self.assertNotEqual(record.code_hash, self.codes["tester@example.com"])
            self.assertIsNotNone(record.used_at)
            self.assertTrue(db.query(User).one().email_verified)

    def test_wrong_expired_and_max_attempt_codes_are_rejected(self):
        self.register()
        with self.session_factory() as db:
            user = db.query(User).filter(User.email == "tester@example.com").first()
            user.email_verified = False
            db.commit()
        self.client.post(
            "/auth/send-verification-code",
            json={"email": "tester@example.com"},
        )
        correct = self.codes["tester@example.com"]
        wrong = f"{(int(correct) + 1) % 1_000_000:06d}"
        for _ in range(settings.EMAIL_VERIFICATION_MAX_ATTEMPTS):
            response = self.verify(code=wrong)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.verify(code=correct).status_code, 400)

        with self.session_factory() as db:
            user = db.query(User).one()
            user.email_verified = False
            db.commit()
        verification_rate_limiter.clear()
        self.client.post(
            "/auth/send-verification-code",
            json={"email": "tester@example.com"},
        )
        with self.session_factory() as db:
            record = (
                db.query(EmailVerificationToken)
                .order_by(EmailVerificationToken.id.desc())
                .first()
            )
            record.expires_at = utc_now() - timedelta(seconds=1)
            db.commit()
        self.assertEqual(self.verify().status_code, 400)

    def test_resend_is_generic_rate_limited_and_invalidates_old_code(self):
        self.register()
        with self.session_factory() as db:
            user = db.query(User).filter(User.email == "tester@example.com").first()
            user.email_verified = False
            db.commit()
        first = self.client.post(
            "/auth/send-verification-code",
            json={"email": "tester@example.com"},
        )
        self.assertEqual(first.status_code, 200)
        old_code = self.codes["tester@example.com"]
        too_soon = self.client.post(
            "/auth/send-verification-code",
            json={"email": "tester@example.com"},
        )
        self.assertEqual(too_soon.status_code, 429)
        self.assertIn("Retry-After", too_soon.headers)

        verification_rate_limiter.clear()
        second = self.client.post(
            "/auth/send-verification-code",
            json={"email": "tester@example.com"},
        )
        self.assertEqual(second.status_code, 200)
        new_code = self.codes["tester@example.com"]

        self.assertEqual(self.verify(code=old_code).status_code, 400)
        self.assertEqual(self.verify(code=new_code).status_code, 200)

        verification_rate_limiter.clear()
        missing = self.client.post(
            "/auth/send-verification-code",
            json={"email": "missing@example.com"},
        )
        self.assertEqual(first.json()["message"], missing.json()["message"])

    def test_sessions_create_list_revoke_and_enforce_ownership(self):
        self.register()
        first = self.login(user_agent="Mozilla/5.0 Windows Chrome/120.0")
        second = self.login(user_agent="Mozilla/5.0 iPhone Safari/17.0")
        first_token = first.json()["access_token"]
        second_token = second.json()["access_token"]
        first_headers = {"Authorization": f"Bearer {first_token}"}
        second_headers = {"Authorization": f"Bearer {second_token}"}

        sessions = self.client.get("/auth/sessions", headers=first_headers)
        self.assertEqual(sessions.status_code, 200)
        self.assertEqual(len(sessions.json()), 2)
        current = next(item for item in sessions.json() if item["is_current"])
        other = next(item for item in sessions.json() if not item["is_current"])
        self.assertNotEqual(current["ip_address"], "testclient")

        revoked = self.client.delete(
            f"/auth/sessions/{other['id']}",
            headers=first_headers,
        )
        self.assertEqual(revoked.status_code, 200)
        self.assertEqual(
            self.client.get("/auth/me", headers=second_headers).status_code,
            401,
        )

        self.register("other", "other@example.com")
        other_user_token = self.login("other").json()["access_token"]
        other_user_headers = {"Authorization": f"Bearer {other_user_token}"}
        foreign_session = self.client.get(
            "/auth/sessions",
            headers=other_user_headers,
        ).json()[0]
        self.assertEqual(
            self.client.delete(
                f"/auth/sessions/{foreign_session['id']}",
                headers=first_headers,
            ).status_code,
            404,
        )

    def test_logout_current_and_logout_all_revoke_tokens(self):
        self.register()
        one = self.login().json()["access_token"]
        two = self.login().json()["access_token"]
        one_headers = {"Authorization": f"Bearer {one}"}
        two_headers = {"Authorization": f"Bearer {two}"}
        self.assertEqual(
            self.client.post("/auth/logout", headers=one_headers).status_code,
            200,
        )
        self.assertEqual(
            self.client.get("/auth/me", headers=one_headers).status_code,
            401,
        )
        self.assertEqual(
            self.client.post("/auth/logout-all", headers=two_headers).status_code,
            200,
        )
        self.assertEqual(
            self.client.get("/auth/me", headers=two_headers).status_code,
            401,
        )
        with self.session_factory() as db:
            self.assertEqual(
                db.query(UserSession).filter(
                    UserSession.revoked_at.is_(None)
                ).count(),
                0,
            )


if __name__ == "__main__":
    unittest.main()
