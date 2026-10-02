from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseTTSProvider(ABC):
    """
    Abstract interface for Text-to-Speech engines.
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Identifier of the provider e.g. edge-tts, elevenlabs, google-cloud"""
        pass

    @abstractmethod
    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """Returns list of voice dicts {id, name, gender, language, description}"""
        pass

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        pitch: int = 0,
        output_file_path: Optional[str] = None
    ) -> bytes:
        """
        Synthesizes text to audio.
        If output_file_path is provided, writes file directly.
        Returns audio bytes.
        """
        pass