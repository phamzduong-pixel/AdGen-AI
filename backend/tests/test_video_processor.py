import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from app.services.media.video_processor import FFmpegVideoProcessor, VideoProcessorError


class VideoProcessorTest(unittest.TestCase):
    def test_subtitle_timestamp_carries_millisecond_rounding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.mp4'
            destination = root / 'output.mp4'
            source.write_bytes(b'source')
            processor = FFmpegVideoProcessor('ffmpeg', 'ffprobe', timeout_seconds=1)

            def capture_and_fail(args):
                subtitle_path = destination.with_suffix('.srt')
                content = subtitle_path.read_text(encoding='utf-8')
                self.assertIn('00:00:01,000 --> 00:00:02,000', content)
                raise VideoProcessorError('test stop before ffmpeg')

            processor._run = capture_and_fail
            with self.assertRaises(VideoProcessorError):
                processor.subtitles(
                    source,
                    destination,
                    [{'text': 'Xin chao', 'start': 0.9996, 'end': 1.9996}],
                    'bottom',
                )
            self.assertFalse(destination.with_suffix('.srt').exists())


    def test_sidecar_files_are_cleaned_when_write_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            destination = root / "output.mp4"
            source.write_bytes(b"source")
            processor = FFmpegVideoProcessor("ffmpeg", "ffprobe", timeout_seconds=1)
            cases = [
                ("text", destination.with_suffix(".txt"), lambda: processor.text_overlay(source, destination, "CTA", 0, 1, "bottom", 48, "white", True)),
                ("subtitle", destination.with_suffix(".srt"), lambda: processor.subtitles(source, destination, [{"text": "Xin chào", "start": 0, "end": 1}], "bottom")),
                ("merge", destination.with_suffix(".concat.txt"), lambda: processor.merge([source], destination)),
            ]
            for _, sidecar, operation in cases:
                sidecar.write_text("partial", encoding="utf-8")
                with patch.object(Path, "write_text", side_effect=OSError("disk full")):
                    with self.assertRaises(OSError):
                        operation()
                self.assertFalse(sidecar.exists())

if __name__ == '__main__':
    unittest.main()
