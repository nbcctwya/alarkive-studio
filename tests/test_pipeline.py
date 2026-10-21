"""Offline regressions for metadata, render replacement and timeline validation.

Run with: python -B -m unittest discover -s tests -v
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import make_voice
import produce


def write_wav(path, seconds=1.0):
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(24000)
        audio.writeframes(b"\0\0" * round(24000 * seconds))


class PipelineTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="alarkive-test-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(produce, "ROOT", self.root))
        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        script = self.root / "input.txt"
        script.write_text("Hello world\n", encoding="utf-8")
        self.args = SimpleNamespace(id="demo002", force=False, script=str(script),
                                    title_lines=["Review"], highlight=[])
        self.pipe = produce.Pipeline(self.args)
        self.pipe.step_init()
        (self.root / "assets").mkdir()
        (self.root / "assets" / "broll_index.json").write_text(json.dumps({
            "People/Working/clip.mp4": {"duration": 10.0}
        }), encoding="utf-8")
        self.shot = dict(seq=1, start=0.0, end=1.0, duration=1.0,
                         material="B-roll/Landscape video/People/Working/clip.mp4",
                         category="Working", srt_entries=[1], reason="Opening")
        self.shot.update({"in": 0.0, "out": 1.0})

    def save_meta(self, meta):
        self.pipe.meta_path.write_text(yaml.safe_dump(meta), encoding="utf-8")

    def set_duration(self, duration):
        meta = self.pipe.meta()
        meta["voice"]["duration_sec"] = duration
        self.save_meta(meta)

    def existing_voice(self):
        project = self.pipe.project
        mp3 = project / "voice/demo002.mp3"
        wav = project / "voice/demo002.wav"
        srt = project / "subtitle/demo002.srt"
        mp3.write_bytes(b"existing audio")
        write_wav(wav, seconds=1.25)
        srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello world\n",
                       encoding="utf-8")
        return {path: path.read_bytes() for path in (mp3, wav, srt)}

    def test_voice_saves_metadata_and_preserves_other_settings(self):
        meta = self.pipe.meta()
        meta["custom"] = {"keep": True}
        self.save_meta(meta)

        async def synth(text, voice, rate, mp3_path):
            mp3_path.write_bytes(b"mocked TTS audio")
            return [("Hello", 0, 200), ("world", 200, 300)]

        def convert(cmd, **kwargs):
            write_wav(Path(cmd[-1]))

        with patch.object(make_voice, "synth", synth), \
                patch.object(make_voice.subprocess, "run", convert), \
                patch.object(make_voice.imageio_ffmpeg, "get_ffmpeg_exe",
                             return_value="ffmpeg"), \
                patch.object(sys, "argv", ["make_voice.py", "--project",
                                          str(self.pipe.project)]):
            make_voice.main()
        result = self.pipe.meta()
        self.assertEqual(result["voice"]["duration_sec"], 1.0)
        self.assertEqual(result["voice"]["voice_used"], meta["voice"]["voice_primary"])
        self.assertEqual(result["subtitle"]["entries"], 1)
        self.assertEqual(result["custom"], meta["custom"])
        self.assertEqual(result["title"], meta["title"])

    def test_resume_recovers_duration_without_changing_audio_or_subtitles(self):
        original = self.existing_voice()
        with patch.object(produce, "run") as run:
            self.pipe.step_voice()
        run.assert_not_called()
        self.assertEqual(self.pipe.meta()["voice"]["duration_sec"], 1.25)
        for path, content in original.items():
            self.assertEqual(path.read_bytes(), content)

    def test_narration_can_flow_across_caption_lines(self):
        meta = self.pipe.meta()
        meta["script"]["narration_file"] = "narration.txt"
        self.save_meta(meta)
        (self.pipe.project / "script.txt").write_text("Hello\nworld\n", encoding="utf-8")
        (self.pipe.project / "narration.txt").write_text("Hello world.", encoding="utf-8")
        spoken = []

        async def synth(text, voice, rate, mp3_path):
            spoken.append(text)
            mp3_path.write_bytes(b"mocked TTS audio")
            return [("Hello", 0, 200), ("world", 300, 300)]

        with patch.object(make_voice, "synth", synth), \
                patch.object(make_voice.subprocess, "run",
                             side_effect=lambda cmd, **kwargs: write_wav(Path(cmd[-1]))), \
                patch.object(sys, "argv", ["make_voice.py", "--project", str(self.pipe.project)]):
            make_voice.main()
        self.assertEqual(spoken, ["Hello world."])
        srt = (self.pipe.project / meta["subtitle"]["file"]).read_text("utf-8")
        self.assertIn("00:00:00,000 --> 00:00:00,200\nHello", srt)
        self.assertIn("00:00:00,300 --> 00:00:00,600\nworld", srt)
        self.assertEqual(self.pipe.meta()["subtitle"]["entries"], 2)

    def test_narration_mismatch_stops_before_synthesis(self):
        meta = self.pipe.meta()
        meta["script"]["narration_file"] = "narration.txt"
        self.save_meta(meta)
        (self.pipe.project / "narration.txt").write_text("Different words.", encoding="utf-8")
        with patch.object(make_voice, "synth") as synth, \
                patch.object(sys, "argv", ["make_voice.py", "--project", str(self.pipe.project)]), \
                self.assertRaises(SystemExit):
            make_voice.main()
        synth.assert_not_called()
        self.assertFalse((self.pipe.project / meta["voice"]["output_mp3"]).exists())

    def test_resume_keeps_existing_metadata(self):
        self.existing_voice()
        self.set_duration(1.234567)
        original = self.pipe.meta_path.read_bytes()
        with patch.object(produce, "run") as run:
            self.pipe.step_voice()
        run.assert_not_called()
        self.assertEqual(self.pipe.meta_path.read_bytes(), original)

    def test_default_projects_keep_the_existing_chinese_voice_settings(self):
        meta = self.pipe.meta()
        self.assertEqual(meta["language"], "zh")
        self.assertEqual(meta["voice"]["voice_primary"], "zh-CN-XiaoyiNeural")
        self.assertEqual(meta["voice"]["voice_fallback"], "zh-CN-YunxiNeural")
        self.assertEqual(meta["voice"]["rate"], "+0%")

    def test_english_project_has_separate_defaults_and_resumes_without_a_flag(self):
        args = SimpleNamespace(**{**vars(self.args), "id": "demo002_en", "language": "en"})
        english = produce.Pipeline(args)
        english.step_init()
        meta = english.meta()
        self.assertEqual(meta["language"], "en")
        self.assertEqual(meta["voice"]["voice_primary"], "en-US-AndrewNeural")
        self.assertEqual(meta["voice"]["voice_fallback"], "en-US-AvaNeural")
        self.assertEqual(self.pipe.meta()["language"], "zh")
        original = english.meta_path.read_bytes()
        args.language = None
        produce.Pipeline(args).step_init()
        self.assertEqual(english.meta_path.read_bytes(), original)

    def test_cannot_switch_an_existing_chinese_project_to_english_even_with_force(self):
        meta = self.pipe.meta()
        meta.pop("language")  # Historical projects have no language field.
        self.save_meta(meta)
        original = self.pipe.meta_path.read_bytes()
        for force in (False, True):
            args = SimpleNamespace(**{**vars(self.args), "force": force, "language": "en"})
            with self.subTest(force=force), self.assertRaises(SystemExit):
                produce.Pipeline(args)
        self.assertEqual(self.pipe.meta_path.read_bytes(), original)

    def test_failed_english_alignment_keeps_the_previous_complete_audio_and_captions(self):
        meta = self.pipe.meta()
        meta["language"] = "en"
        self.save_meta(meta)
        files = self.existing_voice()
        before_meta = self.pipe.meta_path.read_bytes()

        async def wrong_speech(text, voice, rate, mp3_path):
            mp3_path.write_bytes(b"new mismatched speech")
            return [("Different", 0, 200), ("words", 200, 300)]

        with patch.object(make_voice, "synth", wrong_speech), \
                patch.object(sys, "argv", ["make_voice.py", "--project", str(self.pipe.project)]), \
                self.assertRaisesRegex(ValueError, "complete script"):
            make_voice.main()
        self.assertEqual(self.pipe.meta_path.read_bytes(), before_meta)
        for path, content in files.items():
            self.assertEqual(path.read_bytes(), content)
        self.assertEqual(list(self.pipe.project.glob(".voice-en-*")), [])

    def test_successful_english_voice_promotes_all_staged_files(self):
        meta = self.pipe.meta()
        meta["language"] = "en"
        self.save_meta(meta)
        self.existing_voice()

        async def speech(text, voice, rate, mp3_path):
            mp3_path.write_bytes(b"new aligned speech")
            return [("Hello", 0, 200), ("world", 300, 500)]

        with patch.object(make_voice, "synth", speech), \
                patch.object(make_voice.subprocess, "run",
                             side_effect=lambda cmd, **kwargs: write_wav(Path(cmd[-1]), 1.5)), \
                patch.object(sys, "argv", ["make_voice.py", "--project", str(self.pipe.project)]):
            make_voice.main()
        self.assertEqual((self.pipe.project / meta["voice"]["output_mp3"]).read_bytes(),
                         b"new aligned speech")
        self.assertEqual(self.pipe.meta()["voice"]["duration_sec"], 1.5)
        self.assertIn("00:00:00,800", (self.pipe.project / meta["subtitle"]["file"]).read_text())
        self.assertEqual(list(self.pipe.project.glob(".voice-en-*")), [])

    def test_interrupted_voice_publish_preserves_previous_file_and_cleans_partial(self):
        target = self.pipe.project / "voice/demo002.mp3"
        target.write_bytes(b"previous complete voice")
        source = self.root / "staged.mp3"
        source.write_bytes(b"new complete voice")

        def interrupted_copy(input_file, output):
            output.write(b"partial")
            raise OSError("Simulated interrupted copy")

        with patch.object(make_voice.shutil, "copyfileobj", interrupted_copy), \
                self.assertRaisesRegex(OSError, "interrupted copy"):
            make_voice.promote_staged_file(source, target)
        self.assertEqual(target.read_bytes(), b"previous complete voice")
        self.assertEqual(list(target.parent.glob(".*.tmp")), [])

    def test_force_replaces_each_video_before_wrapping(self):
        suffixes = {"preview": "preview", "final": "v1", "wrapped": "wrapped"}
        for pid in ("demo001", "demo002"):
            with self.subTest(project=pid):
                args = SimpleNamespace(**{**vars(self.args), "id": pid})
                pipe = produce.Pipeline(args)
                pipe.step_init()
                output = pipe.project / "output"
                for suffix in suffixes.values():
                    (output / f"{pid}_{suffix}.mp4").write_bytes(b"old")
                modes = []

                def render(script, *args):
                    mode = args[args.index("--mode") + 1]
                    modes.append(mode)
                    if mode == "wrapped":
                        self.assertEqual((output / f"{pid}_v1.mp4").read_bytes(), b"new")
                    (output / f"demo001_{suffixes[mode]}.mp4").write_bytes(b"new")

                pipe.args.force = True
                with patch.object(produce, "run", render):
                    pipe.step_render()
                self.assertEqual(modes, ["preview", "final", "wrapped"])
                for suffix in suffixes.values():
                    self.assertEqual((output / f"{pid}_{suffix}.mp4").read_bytes(), b"new")
                    if pid != "demo001":
                        self.assertFalse((output / f"demo001_{suffix}.mp4").exists())

    def test_render_skips_existing_outputs_by_default(self):
        for suffix in ("preview", "v1", "wrapped"):
            (self.pipe.project / "output" / f"demo002_{suffix}.mp4").write_bytes(b"old")
        with patch.object(produce, "run") as run:
            self.pipe.step_render()
        run.assert_not_called()

    def validate(self, data):
        path = self.pipe.project / "timeline.yaml"
        path.write_text(yaml.safe_dump(data), encoding="utf-8")
        self.pipe.validate_timeline(path)

    def test_timeline_accepts_existing_path_case_and_slash_styles(self):
        self.set_duration(1.0)
        for material in (self.shot["material"], self.shot["material"].lower(),
                         self.shot["material"].replace("/", "\\")):
            with self.subTest(material=material):
                self.validate({"shots": [{**self.shot, "material": material}]})

    def test_timeline_reports_missing_fields_and_invalid_structure(self):
        self.set_duration(1.0)
        cases = [None, [], {}, {"shots": []}, {"shots": {}}, {"shots": [None]}]
        for field in self.shot:
            cases.append({"shots": [{k: v for k, v in self.shot.items() if k != field}]})
        for data in cases:
            with self.subTest(data=data), self.assertRaises(SystemExit):
                self.validate(data)

    def test_timeline_rejects_invalid_ranges_values_and_coverage(self):
        self.set_duration(1.0)
        changes = [
            {"in": -1.0, "out": 0.0}, {"in": 2.0, "out": 1.0},
            {"start": -1.0, "end": 0.0}, {"end": 0.0}, {"duration": 0.0},
            {"duration": 2.0}, {"out": 2.0}, {"seq": 2}, {"start": 0.1},
            {"end": 11.0, "out": 11.0, "duration": 11.0},
            {"end": 0.5, "out": 0.5, "duration": 0.5},
            {"material": None}, {"material": "missing.mp4"}, {"category": None},
            {"reason": " "}, {"srt_entries": []}, {"srt_entries": [0]},
        ]
        for field in ("start", "end", "duration", "in", "out"):
            for value in (None, "oops", True, float("nan"), float("inf")):
                changes.append({field: value})
        for change in changes:
            with self.subTest(change=change), self.assertRaises(SystemExit):
                self.validate({"shots": [{**self.shot, **change}]})
        with self.assertRaises(SystemExit):
            self.validate({"shots": [self.shot, {**self.shot, "seq": 2,
                                                "start": 0.8, "end": 1.8}]})


if __name__ == "__main__":
    unittest.main()
