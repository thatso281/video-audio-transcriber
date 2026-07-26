import unittest

from media_processor import MediaProcessor


class TranscriptCleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.processor = MediaProcessor()

    def test_removes_spaces_before_punctuation(self) -> None:
        segments = [
            {"start": 0.0, "end": 1.0, "text": "Hello ,"},
            {"start": 1.0, "end": 2.0, "text": "world !"},
        ]
        self.assertEqual(
            self.processor._build_clean_transcript(segments),
            "Hello, world!",
        )

    def test_creates_paragraph_after_long_pause(self) -> None:
        segments = [
            {"start": 0.0, "end": 1.0, "text": "First sentence."},
            {"start": 3.0, "end": 4.0, "text": "Second paragraph."},
        ]
        self.assertEqual(
            self.processor._build_clean_transcript(segments),
            "First sentence.\n\nSecond paragraph.",
        )

    def test_timestamp_format(self) -> None:
        self.assertEqual(
            self.processor._format_timestamp(3661.234),
            "01:01:01.234",
        )


if __name__ == "__main__":
    unittest.main()
