"""Bilingual regressions: intact words, complete subtitles and isolated profiles."""
import sys
import unittest
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import language_profiles as lp
import make_voice
import render_video
from test_dynamic_title import layout_title
from text_layout import word_wrap

FONT = Path("C:/Windows/Fonts/arialbd.ttf")


class ProfileTests(unittest.TestCase):
    def test_legacy_project_keeps_both_original_configs(self):
        self.assertEqual(lp.project_language({}), "zh")
        for filename, section in (("frame_v1.yaml", "frame"), ("cover_v1.yaml", "cover")):
            original = yaml.safe_load((ROOT / "config" / filename).read_text("utf-8"))
            self.assertEqual(lp.apply_profile(original, "zh", section), original)
            lp.apply_profile(original, "en", section)
            self.assertEqual(
                original, yaml.safe_load((ROOT / "config" / filename).read_text("utf-8")))

    def test_english_contractions_case_and_html_entities_keep_correct_timings(self):
        spans = make_voice.assign_words_to_lines(
            ["I'm curious.", "Try, then try again."],
            [("I", 0, 80), ("&apos;m", 80, 80), ("CURIOUS", 200, 400),
             ("Try", 800, 150), ("then", 950, 200), ("try", 1200, 150),
             ("again", 1400, 300)], "en")
        self.assertEqual(spans, [[0, 600], [800, 1700]])

    def test_missing_english_words_fail_instead_of_silently_dropping_a_caption(self):
        with self.assertRaisesRegex(ValueError, "complete script"):
            make_voice.assign_words_to_lines(
                ["Be a beginner.", "Try again."],
                [("Be", 0, 100), ("a", 100, 100), ("beginner", 200, 200)], "en")

    def test_caption_line_break_cannot_split_an_english_word(self):
        with self.assertRaisesRegex(ValueError, "splits a spoken word"):
            make_voice.assign_words_to_lines(["play", "ground"], [("playground", 0, 100)], "en")

    def test_english_narration_keeps_word_boundaries_and_accepts_smart_quotes(self):
        self.assertEqual(make_voice.narration_key("I'm curious.\nTry again!", "en"),
                         make_voice.narration_key("I’m curious, try again.", "en"))
        self.assertNotEqual(make_voice.narration_key("Now here.", "en"),
                            make_voice.narration_key("Nowhere.", "en"))


class Fonts:
    def get(self, role, size):
        return ImageFont.truetype(str(FONT), size), 0


@unittest.skipUnless(FONT.exists(), "Requires the production English font")
class EnglishLayoutTests(unittest.TestCase):
    def setUp(self):
        self.draw = ImageDraw.Draw(Image.new("RGB", (800, 600)))
        self.font = Fonts().get("sans_en_bold", 24)[0]

    def test_wrap_keeps_complete_words_contractions_and_all_text(self):
        text = "I'm curious about the world. Let's try something new."
        rows = word_wrap(text, self.draw, self.font, 220)
        self.assertGreater(len(rows), 1)
        self.assertEqual(" ".join(row[0] for row in rows), text)
        self.assertTrue(all(row[2] <= 220 for row in rows))
        self.assertEqual([word for row in rows for word in row[0].split()], text.split())

    def test_title_wrapping_keeps_highlight_attached_to_the_whole_word(self):
        td = {"font": "sans_en_bold", "wrap": "word", "size": 24, "line_height": 30,
              "max_lines": 8, "reserved_area": {"width": 210, "height": 300}}
        rows, _, _, overflow = layout_title(
            self.draw, Fonts(), td, ["Make the world your playground"], ["playground"], 24)
        self.assertFalse(overflow)
        self.assertEqual(" ".join(row[0] for row in rows), "Make the world your playground")
        emphasized = "".join(ch for text, flags, _ in rows
                             for ch, flag in zip(text, flags) if flag)
        self.assertEqual(emphasized, "playground")

    def test_two_line_caption_does_not_leave_curious_alone_on_the_last_line(self):
        text = "I could make something just because I'm curious."
        rows = word_wrap(text, self.draw, self.font, 480, balance_two_lines=True)
        self.assertEqual(len(rows), 2)
        self.assertEqual(" ".join(row[0] for row in rows), text)
        self.assertTrue(all(len(row[0].split()) >= 3 for row in rows))
        self.assertTrue(all(row[2] <= 480 for row in rows))

    def overlay(self, text):
        cfg = {"subtitle": {"font": "sans_en_bold", "wrap": "word",
                            "color": "#FFFFFF", "stroke_color": "#000000",
                            "shadow": {"offset": [0, 0], "alpha": 0, "enabled": False}}}
        return render_video.build_subtitle_overlays(
            [{"start": 0, "end": 4, "text": text}], Fonts(), cfg, "preview", 0.5, 304)[0]

    def test_regular_english_caption_fits_without_truncation(self):
        result = self.overlay("Every hobby had to turn into something useful.")
        self.assertLessEqual(result["lines"], 2)
        self.assertGreaterEqual(result["size"], 16)

    def test_long_english_caption_is_rejected_instead_of_truncated(self):
        with self.assertRaisesRegex(ValueError, "two lines"):
            self.overlay("A meaningful caption should remain complete. " * 12)

    def test_long_unbroken_word_is_rejected_instead_of_clipped(self):
        with self.assertRaisesRegex(ValueError, "two lines"):
            self.overlay("A" * 100)


if __name__ == "__main__":
    unittest.main()
