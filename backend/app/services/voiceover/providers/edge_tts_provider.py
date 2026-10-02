import io
from typing import List, Dict, Any, Optional
from app.services.voiceover.providers.base import BaseTTSProvider

class EdgeTTSProvider(BaseTTSProvider):
    """
    High quality, zero-cost neural TTS provider using Microsoft Edge Neural voices.
    """

    SUPPORTED_VOICES = [
        {
            "id": "vi-VN-HoaiMyNeural",
            "name": "Hoài My (Nữ - Tự nhiên, truyền cảm)",
            "gender": "female",
            "language": "vi-VN",
            "description": "Giọng nữ miền Bắc nhẹ nhàng, tự nhiên, thích hợp review và kịch bản viral",
            "sample_rate": 24000
        },
        {
            "id": "vi-VN-NamMinhNeural",
            "name": "Nam Minh (Nam - Trầm ấm, dứt khoát)",
            "gender": "male",
            "language": "vi-VN",
            "description": "Giọng nam miền Bắc chững chạc, uy tín, thích hợp quảng cáo sản phẩm và tin tức",
            "sample_rate": 24000
        },
        {
            "id": "en-US-JennyNeural",
            "name": "Jenny (Nữ - Tiếng Anh)",
            "gender": "female",
            "language": "en-US",
            "description": "American English female voice, energetic and friendly",
            "sample_rate": 24000
        },
        {
            "id": "en-US-GuyNeural",
            "name": "Guy (Nam - Tiếng Anh)",
            "gender": "male",
            "language": "en-US",
            "description": "American English male voice, professional and confident",
            "sample_rate": 24000
        }
    ]

    @property
    def provider_id(self) -> str:
        return "edge-tts"

    async def get_available_voices(self) -> List[Dict[str, Any]]:
        return self.SUPPORTED_VOICES

    def _format_rate(self, speed: float) -> str:
        """Converts speed multiplier (e.g. 1.1) to edge-tts rate format (e.g. '+10%')"""
        percent = int(round((speed - 1.0) * 100))
        if percent >= 0:
            return f"+{percent}%"
        return f"{percent}%"

    def _format_pitch(self, pitch: int) -> str:
        """Converts pitch int to edge-tts pitch format (e.g. '+5Hz')"""
        if pitch >= 0:
            return f"+{pitch}Hz"
        return f"{pitch}Hz"

    async def synthesize(
        self,
        text: str,
        voice_id: str = "vi-VN-HoaiMyNeural",
        speed: float = 1.0,
        pitch: int = 0,
        output_file_path: Optional[str] = None
    ) -> bytes:
        try:
            import edge_tts
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Voiceover dependency 'edge-tts' is not installed. "
                "Install the backend requirements before using voiceover."
            ) from exc

        rate_str = self._format_rate(speed)
        pitch_str = self._format_pitch(pitch)

        communicate = edge_tts.Communicate(
            text=text,
            voice=voice_id,
            rate=rate_str,
            pitch=pitch_str
        )

        if output_file_path:
            await communicate.save(output_file_path)
            with open(output_file_path, "rb") as f:
                return f.read()

        # In-memory streaming
        audio_stream = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_stream.write(chunk["data"])
        return audio_stream.getvalue()
