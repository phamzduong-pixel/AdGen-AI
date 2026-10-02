import unittest

from app.prompts.youtube import YOUTUBE_PROMPT
from app.services.prompt_service import (
    build_system_prompt,
    get_specialized_prompt,
    is_supported_prompt_type,
    normalize_prompt_type,
)


class YouTubePromptTest(unittest.TestCase):
    def test_youtube_prompt_content_and_structure(self):
        self.assertIn("YouTube", YOUTUBE_PROMPT)
        self.assertIn("Retention Curve", YOUTUBE_PROMPT)
        self.assertIn("YouTube Shorts", YOUTUBE_PROMPT)
        self.assertIn("Thumbnail", YOUTUBE_PROMPT)
        self.assertIn("Timestamps", YOUTUBE_PROMPT)
        self.assertIn("Subscribe", YOUTUBE_PROMPT)

    def test_prompt_service_youtube_resolution(self):
        self.assertTrue(is_supported_prompt_type("youtube"))
        self.assertTrue(is_supported_prompt_type("yt"))
        self.assertTrue(is_supported_prompt_type("youtube_video"))
        self.assertTrue(is_supported_prompt_type("youtube_shorts"))
        self.assertTrue(is_supported_prompt_type("shorts"))

        self.assertEqual(normalize_prompt_type("YT"), "youtube")
        self.assertEqual(normalize_prompt_type("youtube_shorts"), "youtube")

        specialized = get_specialized_prompt("youtube")
        self.assertEqual(specialized, YOUTUBE_PROMPT)

    def test_build_system_prompt_youtube(self):
        system_prompt = build_system_prompt(prompt_type="youtube")
        self.assertIn("YOUTUBE", system_prompt)
        self.assertIn("PLATFORM INTELLIGENCE: YOUTUBE", system_prompt)
        self.assertIn("VERIFIED KNOWLEDGE", system_prompt)
        self.assertIn("Retention", system_prompt)


if __name__ == "__main__":
    unittest.main()
