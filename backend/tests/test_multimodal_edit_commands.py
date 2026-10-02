import unittest

from app.services.multimodal.models import (
    MediaAsset,
    MediaEditInstruction,
    ModalityType,
    MultimodalEditCommand,
    MultimodalPayload,
    MultimodalTaskType,
)
from app.services.multimodal.service import (
    MultimodalService,
    multimodal_service,
)


class MultimodalEditCommandsTest(unittest.TestCase):
    def setUp(self):
        self.service = MultimodalService()

    def test_multimodal_edit_commands_definition_and_formatting(self):
        instructions = [
            MediaEditInstruction(
                command=MultimodalEditCommand.REMOVE_ON_SCREEN_TEXT,
                target_asset_id="video-raw-01.mp4",
                timestamp_start=0.0,
                timestamp_end=5.0,
            ),
            MediaEditInstruction(
                command=MultimodalEditCommand.INJECT_CTA_OVERLAY,
                target_asset_id="video-raw-01.mp4",
                cta_text="Bấm vào giỏ hàng góc trái",
                timestamp_start=25.0,
                timestamp_end=30.0,
            ),
            MediaEditInstruction(
                command=MultimodalEditCommand.CHANGE_ASPECT_RATIO,
                target_asset_id="video-raw-01.mp4",
                target_aspect_ratio="9:16",
            ),
            MediaEditInstruction(
                command=MultimodalEditCommand.ADD_SUBTITLES,
                target_asset_id="video-raw-01.mp4",
                subtitle_language="vi",
            ),
            MediaEditInstruction(
                command=MultimodalEditCommand.TRIM_VIDEO,
                target_asset_id="video-raw-01.mp4",
                timestamp_start=3.0,
                timestamp_end=33.0,
            ),
        ]

        formatted = self.service.format_edit_instructions(instructions)

        self.assertIn("MULTIMODAL EDITING INSTRUCTIONS", formatted)
        self.assertIn("remove_on_screen_text", formatted)
        self.assertIn("inject_cta_overlay", formatted)
        self.assertIn("Bấm vào giỏ hàng góc trái", formatted)
        self.assertIn("change_aspect_ratio", formatted)
        self.assertIn("9:16", formatted)
        self.assertIn("add_subtitles", formatted)
        self.assertIn("trim_video", formatted)


if __name__ == "__main__":
    unittest.main()
