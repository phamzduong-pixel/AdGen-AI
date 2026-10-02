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
from app.database.database import Base
from app.database.database import get_db
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.services.email_service import EmailConfigurationError
from app.services.email_service import email_provider
from app.services.password_reset_service import password_reset_rate_limiter


class PasswordResetApiTest(unittest.TestCase):
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
        password_reset_rate_limiter.clear()
        self.config_patch = patch.object(
            email_provider,
            "ensure_configured",
            return_value=None,
        )
        self.send_patch = patch.object(
            email_provider,
            "send_code",
            side_effect=self._capture_code,
        )
        self.config_patch.start()
        self.send_patch.start()

    def tearDown(self):
        self.config_patch.stop()
        self.send_patch.stop()
        password_reset_rate_limiter.clear()
        self.client.close()
        self.engine.dispose()

    def _capture_code(self, recipient, code, expires_minutes):
        self.codes[recipient] = code
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())
        self.assertGreater(expires_minutes, 0)

    def register(self, email="tester@example.com"):
        response = self.client.post(
            "/auth/register",
            json={
                "username": "tester",
                "email": email,
                "password": "password123",
            },
        )
        if response.status_code == 200:
            with self.session_factory() as db:
                user = db.query(User).filter(User.email == email).first()
                user.email_verified = True
                db.commit()
        return response

    def request_code(self, email="tester@example.com"):
        return self.client.post(
            "/auth/forgot-password",
            json={"email": email},
        )

    def verify_code(self, email="tester@example.com", code=None):
        return self.client.post(
            "/auth/verify-reset-code",
            json={"email": email, "code": code or self.codes[email]},
        )

    def test_request_does_not_reveal_account_existence(self):
        self.register()
        existing = self.request_code()
        missing = self.request_code("missing@example.com")
        self.assertEqual(existing.status_code, 200)
        self.assertEqual(missing.status_code, 200)
        self.assertEqual(existing.json(), missing.json())
        self.assertIn("tester@example.com", self.codes)
        self.assertNotIn("missing@example.com", self.codes)

    def test_missing_email_configuration_is_clear_and_uniform(self):
        self.config_patch.stop()
        with patch.object(
            email_provider,
            "ensure_configured",
            side_effect=EmailConfigurationError("missing SMTP_PASSWORD"),
        ):
            self.assertEqual(self.request_code().status_code, 503)
            self.assertEqual(
                self.request_code("missing@example.com").status_code,
                503,
            )
        self.config_patch.start()

    def test_resend_too_soon_is_rate_limited(self):
        self.register()
        self.assertEqual(self.request_code().status_code, 200)
        response = self.request_code()
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response.headers)

    def test_correct_code_is_single_use_and_returns_reset_token(self):
        self.register()
        self.request_code()
        verified = self.verify_code()
        self.assertEqual(verified.status_code, 200)
        self.assertGreaterEqual(len(verified.json()["reset_token"]), 32)
        self.assertGreater(verified.json()["expires_in"], 0)
        self.assertEqual(self.verify_code().status_code, 400)
        with self.session_factory() as db:
            record = db.query(PasswordResetToken).one()
            self.assertNotEqual(record.otp_hash, self.codes["tester@example.com"])
            self.assertIsNotNone(record.verified_at)

    def test_wrong_expired_and_max_attempt_codes_are_rejected(self):
        self.register()
        self.request_code()
        correct_code = self.codes["tester@example.com"]
        wrong_code = f"{(int(correct_code) + 1) % 1_000_000:06d}"
        for _ in range(5):
            response = self.verify_code(code=wrong_code)
        self.assertEqual(response.status_code, 400)
        self.assertIn("hết hạn", response.json()["detail"])
        self.assertEqual(self.verify_code().status_code, 400)

        password_reset_rate_limiter.clear()
        self.request_code()
        with self.session_factory() as db:
            record = (
                db.query(PasswordResetToken)
                .order_by(PasswordResetToken.id.desc())
                .first()
            )
            record.expires_at = utc_now() - timedelta(seconds=1)
            db.commit()
        self.assertEqual(self.verify_code().status_code, 400)

    def test_reset_password_updates_login_and_invalidates_old_session(self):
        self.register()
        old_login = self.client.post(
            "/auth/login",
            data={"username": "tester", "password": "password123"},
        )
        old_token = old_login.json()["access_token"]
        self.request_code()
        reset_token = self.verify_code().json()["reset_token"]
        response = self.client.post(
            "/auth/reset-password",
            json={
                "reset_token": reset_token,
                "new_password": "new-password-456",
                "confirm_password": "new-password-456",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.client.post(
                "/auth/login",
                data={"username": "tester", "password": "password123"},
            ).status_code,
            401,
        )
        self.assertEqual(
            self.client.post(
                "/auth/login",
                data={"username": "tester", "password": "new-password-456"},
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {old_token}"},
            ).status_code,
            401,
        )
        self.assertEqual(
            self.client.post(
                "/auth/reset-password",
                json={
                    "reset_token": reset_token,
                    "new_password": "another-password-789",
                    "confirm_password": "another-password-789",
                },
            ).status_code,
            400,
        )

    def test_invalid_expired_token_and_password_mismatch_are_rejected(self):
        invalid = self.client.post(
            "/auth/reset-password",
            json={
                "reset_token": "x" * 48,
                "new_password": "new-password-456",
                "confirm_password": "new-password-456",
            },
        )
        self.assertEqual(invalid.status_code, 400)

        mismatch = self.client.post(
            "/auth/reset-password",
            json={
                "reset_token": "x" * 48,
                "new_password": "new-password-456",
                "confirm_password": "different-password-789",
            },
        )
        self.assertEqual(mismatch.status_code, 422)

        self.register()
        self.request_code()
        reset_token = self.verify_code().json()["reset_token"]
        with self.session_factory() as db:
            record = db.query(PasswordResetToken).one()
            record.reset_token_expires_at = utc_now() - timedelta(seconds=1)
            db.commit()
        expired = self.client.post(
            "/auth/reset-password",
            json={
                "reset_token": reset_token,
                "new_password": "new-password-456",
                "confirm_password": "new-password-456",
            },
        )
        self.assertEqual(expired.status_code, 400)

    def test_google_only_account_receives_safe_guidance(self):
        self.register()
        with self.session_factory() as db:
            user = db.query(User).one()
            user.auth_provider = "google"
            db.commit()
        self.request_code()
        reset_token = self.verify_code().json()["reset_token"]
        response = self.client.post(
            "/auth/reset-password",
            json={
                "reset_token": reset_token,
                "new_password": "new-password-456",
                "confirm_password": "new-password-456",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Google", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
