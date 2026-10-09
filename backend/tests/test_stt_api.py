import io
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.stt import router as stt_router
from app.core.security import get_current_user
from app.models.user import User
from app.services.stt.models import TranscriptionResult
from app.services.stt.providers.unavailable import UnavailableSTTProvider
from app.services.stt.service import stt_service
from tests.audio_fixtures import make_wav_bytes



class StubProvider:
    provider_id = "unit-test-provider"

    async def transcribe(self, audio_path, *, content_type, language):
        return TranscriptionResult(
            transcript="Noi dung tieng Viet",
            language=language,
            provider=self.provider_id,
            metadata={"unit_test": True},
        )


class STTApiTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(stt_router)
        self.user = User(
            username="stt-owner",
            email="stt-owner@example.com",
            hashed_password="unused",
            email_verified=True,
        )
        self.app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close()

    def test_authenticated_success_returns_typed_result_without_path(self):
        with patch.object(stt_service, "provider", StubProvider()):
            response = self.client.post(
                "/stt/transcribe",
                files={"file": ("voice.wav", io.BytesIO(make_wav_bytes()), "audio/wav")},
                data={"language": "vi-VN"},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["transcript"], "Noi dung tieng Viet")
        self.assertEqual(body["language"], "vi-VN")
        self.assertEqual(body["provider"], "unit-test-provider")
        self.assertNotIn("path", body)
        self.assertNotIn("audio_path", body)

    def test_unconfigured_provider_returns_explicit_error(self):
        with patch.object(stt_service, "provider", UnavailableSTTProvider()):
            response = self.client.post(
                "/stt/transcribe",
                files={"file": ("voice.wav", io.BytesIO(make_wav_bytes()), "audio/wav")},
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"]["code"], "STT_PROVIDER_NOT_CONFIGURED")

    def test_endpoint_requires_authentication(self):
        self.app.dependency_overrides.clear()
        response = self.client.post(
            "/stt/transcribe",
            files={"file": ("voice.wav", io.BytesIO(make_wav_bytes()), "audio/wav")},
        )

        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
