import importlib.util
import os
from pathlib import Path

from app.core.config import settings
from app.services.stt.models import STTProviderNotConfiguredError
from app.services.stt.providers.base import BaseSTTProvider
from app.services.stt.providers.google_cloud import GoogleCloudSTTProvider
from app.services.stt.providers.unavailable import UnavailableSTTProvider
from app.services.stt.providers.vosk import VoskSTTProvider


def _google_speech_sdk_available() -> bool:
    try:
        return importlib.util.find_spec("google.cloud.speech_v2") is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def _vosk_sdk_available() -> bool:
    try:
        return importlib.util.find_spec("vosk") is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def _default_vosk_model_path() -> Path:
    local_app_data = os.getenv("LOCALAPPDATA", "").strip()
    if local_app_data:
        return Path(local_app_data) / "AdGenAI" / "models" / "vosk-model-small-vn-0.4"
    return Path.home() / ".local" / "share" / "AdGenAI" / "models" / "vosk-model-small-vn-0.4"

def build_stt_provider() -> BaseSTTProvider:
    """Build only an explicitly configured and safely initialized provider."""

    if settings.STT_PROVIDER == "vosk":
        if not _vosk_sdk_available():
            return UnavailableSTTProvider("vosk dependency is not installed")
        model_path = Path(settings.VOSK_MODEL_PATH) if settings.VOSK_MODEL_PATH else _default_vosk_model_path()
        if not model_path.is_dir():
            return UnavailableSTTProvider("Vosk model path does not point to a directory")
        try:
            return VoskSTTProvider(model_path=model_path)
        except STTProviderNotConfiguredError:
            return UnavailableSTTProvider("Vosk provider is not configured")
        except Exception:
            return UnavailableSTTProvider("Vosk provider could not be initialized")
    if settings.STT_PROVIDER != "google-cloud":
        return UnavailableSTTProvider("STT_PROVIDER is not configured for a supported provider")

    credentials_path = settings.GOOGLE_APPLICATION_CREDENTIALS
    if credentials_path and not Path(credentials_path).is_file():
        return UnavailableSTTProvider(
            "GOOGLE_APPLICATION_CREDENTIALS does not point to a file"
        )
    if not _google_speech_sdk_available():
        return UnavailableSTTProvider(
            "google-cloud-speech dependency is not installed"
        )

    try:
        return GoogleCloudSTTProvider()
    except STTProviderNotConfiguredError:
        return UnavailableSTTProvider(
            "Google Cloud Speech provider is not configured"
        )
    except Exception:
        return UnavailableSTTProvider(
            "Google Cloud Speech provider could not be initialized"
        )
