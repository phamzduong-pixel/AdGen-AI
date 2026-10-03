"""Manual mock smoke check for Voice Studio service flow.

This script is intentionally outside pytest discovery and never calls a real
TTS provider. API ownership cases live in ``tests/test_voiceover_api.py``.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch

from app.core.config import settings
from app.schemas.voiceover import VoiceoverGenerateRequest
from app.services.voiceover.providers.mock_provider import MockTTSProvider
from app.services.voiceover.voiceover_service import VoiceoverService


async def main() -> int:
    with tempfile.TemporaryDirectory() as directory, patch.object(settings, 'UPLOAD_DIR', directory):
        service = VoiceoverService(provider=MockTTSProvider())
        result = await service.generate_voiceover(
            VoiceoverGenerateRequest(text='A mock voiceover flow for local smoke testing.')
        )
        output = Path(directory) / 'audio' / f'{result.audio_id}.mp3'
        assert output.is_file()
        assert result.file_size_bytes == output.stat().st_size
        print(f'generated={result.audio_id} bytes={result.file_size_bytes}')
    print('VOICEOVER_SERVICE_SMOKE_PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))