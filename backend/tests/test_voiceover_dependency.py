import asyncio
import sys
import unittest
from unittest.mock import patch

from app.services.voiceover.providers.edge_tts_provider import EdgeTTSProvider


class VoiceoverDependencyTests(unittest.TestCase):
    def test_missing_edge_tts_is_reported_at_synthesis_boundary(self):
        provider = EdgeTTSProvider()

        async def run():
            with patch.dict(sys.modules, {"edge_tts": None}):
                with self.assertRaisesRegex(RuntimeError, "edge-tts"):
                    await provider.synthesize("test")

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
