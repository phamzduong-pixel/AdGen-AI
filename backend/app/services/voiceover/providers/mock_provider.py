from typing import List, Dict, Any, Optional
from app.services.voiceover.providers.base import BaseTTSProvider

class MockTTSProvider(BaseTTSProvider):
    """
    Fallback mock provider that produces a small valid silent/stub MP3 byte stream.
    """

    # Minimal silent MP3 frame
    SILENT_MP3_BYTES = (
        b'\xff\xfb\x90\x44\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    ) * 80

    @property
    def provider_id(self) -> str:
        return "mock"

    async def get_available_voices(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "mock-vi-female",
                "name": "Giọng Thử Nghiệm (Nữ)",
                "gender": "female",
                "language": "vi-VN",
                "description": "Giọng mock phục vụ unit test offline",
                "sample_rate": 24000
            }
        ]

    async def synthesize(
        self,
        text: str,
        voice_id: str = "mock-vi-female",
        speed: float = 1.0,
        pitch: int = 0,
        output_file_path: Optional[str] = None
    ) -> bytes:
        data = self.SILENT_MP3_BYTES
        if output_file_path:
            with open(output_file_path, "wb") as f:
                f.write(data)
        return data
