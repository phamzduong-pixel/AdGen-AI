import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.voiceover import router as voiceover_router
from app.core.security import get_current_user
from app.database.database import Base, get_db
from app.models.user import User
from app.models.voiceover_audio import VoiceoverAudio
from app.schemas.voiceover import VoiceoverGenerateResponse
from app.services.voiceover.providers.vieneu_reference_provider import (
    ReferenceVoiceProviderTimeoutError,
)


class ReferenceVoiceApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
        self.db = self.Session()
        self.user = User(
            username="reference-owner",
            email="reference-owner@example.com",
            hashed_password="unused",
            email_verified=True,
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

        self.app = FastAPI()
        self.app.include_router(voiceover_router)
        self.app.dependency_overrides[get_db] = lambda: self.db
        self.app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = TestClient(self.app)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.audio_dir = Path(self.temp_dir.name) / "audio"
        self.audio_dir.mkdir()

    def tearDown(self):
        self.client.close()
        self.db.close()
        self.engine.dispose()
        self.temp_dir.cleanup()

    def _response(self):
        audio_id = "reference-output"
        return VoiceoverGenerateResponse(
            success=True,
            audio_id=audio_id,
            audio_url=f"/voiceover/audio/{audio_id}.mp3",
            download_url=f"/voiceover/audio/{audio_id}.mp3?download=true",
            duration_seconds=2.0,
            file_size_bytes=1234,
            voice_id="vieneu-v3-turbo-local",
            voice_name="Local reference voice",
            speed=1.0,
            cleaned_text="hello",
        )

    def test_reference_endpoint_persists_owner_record_after_provider_success(self):
        response = self._response()
        voiceover_module = __import__(
            "app.api.voiceover",
            fromlist=["voiceover_service"],
        )
        with patch.object(
            voiceover_module.voiceover_service,
            "generate_reference_voiceover",
            new=AsyncMock(return_value=response),
        ):
            result = self.client.post(
                "/voiceover/generate-reference",
                data={"text": "hello"},
                files={"file": ("reference.wav", b"audio", "audio/wav")},
            )

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["voice_id"], "vieneu-v3-turbo-local")
        record = self.db.query(VoiceoverAudio).one()
        self.assertEqual(record.audio_id, "reference-output")
        self.assertEqual(record.user_id, self.user.id)

    def test_reference_endpoint_maps_provider_timeout_without_internal_details(self):
        voiceover_module = __import__(
            "app.api.voiceover",
            fromlist=["voiceover_service"],
        )
        with patch.object(
            voiceover_module.voiceover_service,
            "generate_reference_voiceover",
            new=AsyncMock(side_effect=ReferenceVoiceProviderTimeoutError),
        ):
            result = self.client.post(
                "/voiceover/generate-reference",
                data={"text": "hello"},
                files={"file": ("reference.wav", b"audio", "audio/wav")},
            )

        self.assertEqual(result.status_code, 504)
        self.assertEqual(result.json()["detail"]["code"], "VOICE_REFERENCE_PROVIDER_TIMEOUT")
        self.assertEqual(self.db.query(VoiceoverAudio).count(), 0)


if __name__ == "__main__":
    unittest.main()