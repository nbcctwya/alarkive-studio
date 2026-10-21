"""Exercise the English path using real audition audio, without editing a Chinese project."""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from types import SimpleNamespace

import imageio_ffmpeg
import yaml
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import generate_cover as gc
import generate_frame as gf
import language_profiles as lp
import make_voice
import produce
import render_title_frame
import render_video

SOURCE = ROOT / "projects" / "demo008"
AUDITIONS = ROOT / "preview" / "voice_audition_en_20261020"
PROJECT = HERE / "english_sample"
CAPTIONS = [
    "I used to treat the world",
    "like a tower I had to climb.",
    "Every book had to make me smarter.",
    "Every hobby had to turn into something useful.",
    "Even rest felt like preparation for more work.",
    "Lately, I've been trying a different question:",
    "what if the world could be my playground?",
    "I could make something just because I'm curious.",
    "Be a beginner.",
    "Try, change my mind, and try again.",
    "I still want to do things well.",
    "I just want to enjoy being here, too.",
]


def image_hash(image):
    return hashlib.sha256(image.convert("RGB").tobytes()).hexdigest()


def chinese_regression():
    baseline = json.loads((HERE / "zh_baseline.json").read_text("utf-8"))
    meta = yaml.safe_load((SOURCE / "meta.yaml").read_text("utf-8"))
    frame_cfg = lp.apply_profile(
        yaml.safe_load((ROOT / "config/frame_v1.yaml").read_text("utf-8")), "zh", "frame")
    cover_cfg = lp.apply_profile(
        yaml.safe_load((ROOT / "config/cover_v1.yaml").read_text("utf-8")), "zh", "cover")
    fonts = gf.FontBook(frame_cfg["fonts"])
    hints = (SOURCE / "title.txt").read_text("utf-8").splitlines()
    hashes = {
        mode: image_hash(gc.render_cover(mode, cover_cfg, frame_cfg, fonts,
                                        hints, meta["title"]["highlight"]))
        for mode in ("vertical", "horizontal")
    }
    with tempfile.TemporaryDirectory(dir=HERE, prefix="chinese-check-") as temp:
        project = Path(temp)
        shutil.copyfile(SOURCE / "title.txt", project / "title.txt")
        (project / "meta.yaml").write_text(yaml.safe_dump(meta, allow_unicode=True), "utf-8")
        output = render_title_frame.render_title_frame(project, ROOT / "config/frame_v1.yaml")
        with Image.open(output) as image:
            hashes["title_frame"] = image_hash(image)
    assert hashes == baseline, "Chinese cover/title pixels changed"
    print("[ok] Chinese title and both covers are pixel-identical to the baseline", flush=True)
    return hashes


def prepare():
    chinese = chinese_regression()
    for name in ("voice", "subtitle", "output", "selected_broll"):
        (PROJECT / name).mkdir(parents=True, exist_ok=True)
    (PROJECT / "script.txt").write_text("\n".join(CAPTIONS) + "\n", "utf-8")
    shutil.copyfile(AUDITIONS / "text.txt", PROJECT / "narration.txt")
    assert make_voice.norm("\n".join(CAPTIONS), "en") == make_voice.norm(
        (PROJECT / "narration.txt").read_text("utf-8"), "en")
    (PROJECT / "title.txt").write_text("Make the World\nYour Playground\n", "utf-8")
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    audition_checks = {}
    for voice in ("ava", "andrew"):
        words = json.loads((AUDITIONS / f"{voice}_words.json").read_text("utf-8"))
        spans = make_voice.assign_words_to_lines(CAPTIONS, words, "en")
        audition_checks[voice] = {"matched_captions": len(spans), "word_events": len(words)}
        subprocess.run([ffmpeg, "-v", "error", "-xerror", "-i",
                        str(AUDITIONS / f"{voice}.mp3"), "-f", "null", "-"], check=True)
        if voice == "ava":
            make_voice.write_srt(CAPTIONS, spans, PROJECT / "subtitle/english_sample.srt")
    shutil.copyfile(AUDITIONS / "ava.mp3", PROJECT / "voice/english_sample.mp3")
    wav_path = PROJECT / "voice/english_sample.wav"
    subprocess.run([ffmpeg, "-v", "error", "-y", "-i",
                    str(PROJECT / "voice/english_sample.mp3"), str(wav_path)], check=True)
    with wave.open(str(wav_path)) as audio:
        duration = audio.getnframes() / audio.getframerate()
    meta = {
        "id": "english_sample", "language": "en", "frame_version": "v1.0",
        "title": {"file": "title.txt", "highlight": ["Playground"]},
        "cover": {"highlight": ["Playground"]},
        "script": {"file": "script.txt", "narration_file": "narration.txt"},
        "voice": {**lp.load_profile("en")["voice"], "engine": "edge-tts",
                  "voice_used": "en-US-AvaNeural", "duration_sec": round(duration, 2),
                  "output_mp3": "voice/english_sample.mp3",
                  "output_wav": "voice/english_sample.wav"},
        "subtitle": {"file": "subtitle/english_sample.srt", "entries": len(CAPTIONS)},
        "output": {"title_frame": "output/title_frame.png"},
    }
    (PROJECT / "meta.yaml").write_text(yaml.safe_dump(meta, sort_keys=False), "utf-8")
    entries = render_video.parse_srt(PROJECT / meta["subtitle"]["file"])
    source_shots = yaml.safe_load((SOURCE / "timeline.yaml").read_text("utf-8"))["shots"]
    # Previously reviewed footage, reused only in this isolated technical preview.
    groups = [(6, 1, 2), (2, 3, 3), (3, 4, 4), (1, 5, 5),
              (11, 6, 7), (16, 8, 9), (14, 10, 11), (21, 12, 12)]
    shots = []
    for seq, (source_seq, first, last) in enumerate(groups, 1):
        source = source_shots[source_seq - 1]
        start = 0 if first == 1 else entries[first - 1]["start"]
        end = entries[last]["start"] if last < len(entries) else round(duration, 2)
        length = round(end - start, 3)
        shots.append({
            "seq": seq, "start": start, "end": end, "duration": length,
            "material": source["material"], "category": source["category"],
            "in": 0.1, "out": round(0.1 + length, 3),
            "srt_entries": list(range(first, last + 1)),
            "reason": "English technical preview; footage previously visually reviewed for demo008.",
        })
    (PROJECT / "timeline.yaml").write_text(yaml.safe_dump({"shots": shots}, sort_keys=False), "utf-8")
    pipe = produce.Pipeline(SimpleNamespace(id="english_sample", force=False, language="en"))
    pipe.project, pipe.meta_path = PROJECT, PROJECT / "meta.yaml"
    pipe.validate_timeline(PROJECT / "timeline.yaml")
    pipe.step_title()
    pipe.step_cover()
    render_video.frame_test(PROJECT, 4.0, PROJECT / "output/frame_check.png")
    (HERE / "report.json").write_text(json.dumps({
        "chinese_pixel_hashes": chinese, "auditions": audition_checks,
        "english_audio_sec": duration, "english_subtitle_entries": len(entries),
        "sample_project": str(PROJECT.relative_to(ROOT)),
    }, indent=2), "utf-8")
    return pipe


def main():
    pipe = prepare()
    if "--render" in sys.argv:
        pipe.args.force = "--force-render" in sys.argv
        pipe.step_render()
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        outputs = sorted((PROJECT / "output").glob("english_sample_*.mp4"))
        assert len(outputs) == 3
        for output in outputs:
            subprocess.run([ffmpeg, "-v", "error", "-xerror", "-i", str(output),
                            "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"], check=True)
            print(f"[ok] Full audio/video decode: {output.name}", flush=True)
        report = json.loads((HERE / "report.json").read_text("utf-8"))
        report["decoded_videos"] = [output.name for output in outputs]
        (HERE / "report.json").write_text(json.dumps(report, indent=2), "utf-8")


if __name__ == "__main__":
    main()
