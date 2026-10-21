"""Regression for punctuation wrapping observed in the demo008 preview."""
import sys
import unittest
from pathlib import Path

from PIL import ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import render_video

FONT = Path("C:/Windows/Fonts/simhei.ttf")


class Fonts:
    def get(self, role, size):
        return ImageFont.truetype(str(FONT), size), 0


@unittest.skipUnless(FONT.exists(), "Requires the production Windows CJK font")
class SubtitleLayoutTests(unittest.TestCase):
    def layout(self, text):
        cfg = {"subtitle": {"color": "#FFFFFF", "stroke_color": "#000000",
                            "shadow": {"offset": [1, 1], "alpha": 120, "enabled": False}}}
        return render_video.build_subtitle_overlays(
            [{"start": 0, "end": 4, "text": text}], Fonts(), cfg,
            "preview", 0.5, 304)[0]

    def test_long_sentence_keeps_final_period_on_the_text_line(self):
        result = self.layout("我还想把世界当成一台可以参与创造的模拟器。")
        self.assertEqual(result["lines"], 1)
        self.assertGreaterEqual(result["size"], 16)
        self.assertLess(result["size"], 24)

    def test_normal_two_line_caption_keeps_its_font_size(self):
        result = self.layout("这是需要分成两行显示的一条较长字幕文字用来检查正常换行显示。")
        self.assertEqual(result["lines"], 2)
        self.assertEqual(result["size"], 24)


if __name__ == "__main__":
    unittest.main()
