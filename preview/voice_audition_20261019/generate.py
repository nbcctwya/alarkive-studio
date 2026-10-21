"""Generate isolated, same-text voice auditions without touching project audio."""
import asyncio
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Keep the audition client separate from the project's installed dependencies.
sys.path.insert(0, str(Path(__file__).resolve().parent / "_deps"))
import edge_tts
import imageio_ffmpeg

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
TEXT = """答案早就来了，只是你不喜欢。
有些事情，你不是想不明白，你只是一直在等一个自己更喜欢的答案。
所以你查资料，问朋友，刷帖子，看别人的经历。
同一件事，你想了一遍又一遍：今天觉得应该放下，明天又觉得，也许还有机会。
你告诉自己，我再等等，等我彻底想明白了，再做决定。
可一个月过去了，三个月过去了，甚至一年过去了，新的信息并没有增加多少，你却还在纠结同一个问题。"""
CANDIDATES = [
    ("00_current", "当前配音方式对照", "zh-CN-YunjianNeural", "-4%"),
    ("01_yunjian", "云健：调整断句与语速", "zh-CN-YunjianNeural", "+0%"),
    ("02_yunyang", "云扬：沉稳男声候选", "zh-CN-YunyangNeural", "+0%"),
    ("03_yunxi", "云希：自然男声候选", "zh-CN-YunxiNeural", "+0%"),
    ("04_xiaoxiao", "晓晓：温柔女声候选", "zh-CN-XiaoxiaoNeural", "+0%"),
    ("05_xiaoyi", "晓伊：明亮女声候选", "zh-CN-XiaoyiNeural", "+0%"),
]


async def main():
    print("Edge TTS:", edge_tts.__version__, flush=True)
    gpu = shutil.which("nvidia-smi")
    if gpu:
        result = subprocess.run(
            [gpu, "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=15)
        print("GPU:", result.stdout.strip() or result.stderr.strip(), flush=True)

    voices = await asyncio.wait_for(edge_tts.list_voices(), timeout=30)
    available = {voice["ShortName"]: voice for voice in voices}
    (OUT / "available_voices.json").write_text(json.dumps(
        [v for v in voices if v.get("Locale") == "zh-CN"],
        ensure_ascii=False, indent=2), encoding="utf-8")
    original_lines = [s.strip().replace("**", "") for s in
                      (ROOT / "projects/demo007/script.txt").read_text("utf-8").splitlines()
                      if s.strip()]
    last = next(i for i, line in enumerate(original_lines)
                if line == "你却还在纠结同一个问题。")
    original = "\n".join(original_lines[:last + 1])
    (OUT / "text_original.txt").write_text(original, encoding="utf-8")
    (OUT / "text_flow.txt").write_text(TEXT, encoding="utf-8")
    results = []
    for name, label, voice, rate in CANDIDATES:
        row = dict(name=name, label=label, voice=voice, rate=rate, ok=False)
        results.append(row)
        if voice not in available:
            row["error"] = "Voice unavailable"
            print("SKIP", voice, flush=True)
            continue
        path = OUT / (name + ".mp3")
        temporary = OUT / (name + ".partial.mp3")
        for attempt in range(2):
            try:
                print("GENERATING", label, voice, rate, flush=True)
                if not path.exists():
                    text = original if name == "00_current" else TEXT
                    await asyncio.wait_for(
                        edge_tts.Communicate(text, voice, rate=rate).save(str(temporary)),
                        timeout=60)
                    temporary.replace(path)
                check = subprocess.run(
                    [imageio_ffmpeg.get_ffmpeg_exe(), "-i", str(path), "-f", "null", "-"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
                check.check_returncode()
                duration = re.search(r"Duration: ([0-9:.]+)", check.stderr)
                row.update(ok=True, file=path.name, duration=duration.group(1) if duration else None,
                           bytes=path.stat().st_size)
                print("OK", path.name, row["duration"], flush=True)
                break
            except Exception as exc:
                row["error"] = type(exc).__name__ + ": " + str(exc).split(", url=")[0]
                print("FAILED", voice, row["error"], flush=True)
                if attempt == 0:
                    await asyncio.sleep(2)

    (OUT / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2),
                                      encoding="utf-8")
    cards = []
    for row in results:
        if not row["ok"]:
            continue
        cards.append(f'<section><h2>{html.escape(row["label"])}</h2>'
                     f'<p>{html.escape(row["voice"])} · 语速 {row["rate"]} · {row["duration"]}</p>'
                     f'<audio controls preload="none" src="{row["file"]}"></audio></section>')
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Alark 配音试听</title><style>
body{max-width:840px;margin:40px auto;padding:0 20px;font:17px/1.7 system-ui;background:#f8f7f3;color:#183d30}
section{background:white;border:1px solid #dce2dc;border-radius:14px;padding:16px 24px;margin:16px 0}
h1{font-size:30px}h2{font-size:20px;margin:0}p{color:#56685e}audio{width:100%}pre{white-space:pre-wrap;font:inherit}
</style><h1>Alark 配音试听</h1>
<p>00 是当前断句和 -4% 语速的对照。01–05 使用同一段连贯文稿、正常语速，方便比较音色。
这些样音均来自现有 Edge TTS 免费服务，风格标签只是筛选方向；尚未换成新的配音引擎。</p>'''
    page += "".join(cards) + "<h2>01–05 试听文稿</h2><pre>" + html.escape(TEXT) + "</pre></html>"
    (OUT / "index.html").write_text(page, encoding="utf-8")
    print("COMPLETED", sum(row["ok"] for row in results), "/", len(results), flush=True)
    if not all(row["ok"] for row in results):
        raise SystemExit(1)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(main())
