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


class VoiceoverOwnershipApiTest(unittest.TestCase):
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
            username="voice-owner",
            email="voice-owner@example.com",
            hashed_password="unused",
            email_verified=True,
        )
        self.other = User(
            username="voice-other",
            email="voice-other@example.com",
            hashed_password="unused",
            email_verified=True,
        )
        self.db.add_all([self.owner, self.other])
        self.db.commit()
        self.db.refresh(self.owner)
        self.db.refresh(self.other)
        self.current_user = self.owner

        self.app = FastAPI()
        self.app.include_router(voiceover_router)
        self.app.dependency_overrides[get_db] = lambda: self.db
        self.app.dependency_overrides[get_current_user] = lambda: self.current_user
        self.client = TestClient(self.app)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.audio_dir = Path(self.temp_dir.name) / "audio"
        self.audio_dir.mkdir()

    def tearDown(self):
        self.client.close()
        self.db.close()
        self.engine.dispose()
        self.temp_dir.cleanup()

    def _response(self, audio_id="owned-audio"):
        filename = f"{audio_id}.mp3"
        (self.audio_dir / filename).write_bytes(b"fake-mp3")
        return VoiceoverGenerateResponse(
            success=True,
            audio_id=audio_id,
            audio_url=f"/voiceover/audio/{filename}",
            download_url=f"/voiceover/audio/{filename}?download=true",
            duration_seconds=1.0,
            file_size_bytes=8,
            voice_id="mock-voice",
            voice_name="Mock Voice",
            speed=1.0,
            cleaned_text="hello",
        )

    def test_generate_requires_authentication(self):
        self.app.dependency_overrides.clear()
        response = self.client.post("/voiceover/generate", json={"text": "hello"})
        self.assertEqual(response.status_code, 401)

    def test_tts_error_details_do_not_expose_internal_exception_text(self):
        voiceover_module = __import__(
            "app.api.voiceover",
            fromlist=["voiceover_service"],
        )
        with patch.object(
            voiceover_module.voiceover_service,
            "get_available_voices",
            new=AsyncMock(side_effect=RuntimeError("secret internal path")),
        ):
            voices_response = self.client.get("/voiceover/voices")

        with patch.object(
            voiceover_module.voiceover_service,
            "clean_script",
            side_effect=RuntimeError("secret internal path"),
        ):
            clean_response = self.client.post(
                "/voiceover/clean-script",
                json={"raw_script": "hello"},
            )

        with patch.object(
            voiceover_module.voiceover_service,
            "generate_voiceover",
            new=AsyncMock(side_effect=ValueError("secret internal path")),
        ):
            generate_response = self.client.post(
                "/voiceover/generate",
                json={"text": "hello"},
            )

        for response in (voices_response, clean_response, generate_response):
            self.assertNotIn("secret internal path", response.text)

        self.assertEqual(voices_response.status_code, 500)
        self.assertEqual(clean_response.status_code, 400)
        self.assertEqual(generate_response.status_code, 400)

    def test_owner_can_generate_stream_and_download_but_other_user_cannot(self):
        response = self._response()
        with patch("app.api.voiceover.AUDIO_DIR", self.audio_dir), patch.object(
            __import__("app.api.voiceover", fromlist=["voiceover_service"]).voiceover_service,
            "generate_voiceover",
            new=AsyncMock(return_value=response),
        ):
            generated = self.client.post("/voiceover/generate", json={"text": "hello"})

        self.assertEqual(generated.status_code, 200)
        record = self.db.query(VoiceoverAudio).one()
        self.assertEqual(record.user_id, self.owner.id)

        with patch("app.api.voiceover.AUDIO_DIR", self.audio_dir):
            streamed = self.client.get(response.audio_url)
            self.assertEqual(streamed.status_code, 200)
            self.assertIn("inline", streamed.headers["content-disposition"])
            downloaded = self.client.get(response.download_url)
            self.assertEqual(downloaded.status_code, 200)
            self.assertIn("attachment", downloaded.headers["content-disposition"])

            self.current_user = self.other
            self.assertEqual(self.client.get(response.audio_url).status_code, 404)
            self.assertEqual(self.client.get(response.download_url).status_code, 404)

    def test_legacy_file_without_owner_is_never_auto_assigned(self):
        legacy = self.audio_dir / "legacy.mp3"
        legacy.write_bytes(b"legacy")
        with patch("app.api.voiceover.AUDIO_DIR", self.audio_dir):
            response = self.client.get("/voiceover/audio/legacy.mp3")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.db.query(VoiceoverAudio).count(), 0)


if __name__ == "__main__":
    unittest.main()
