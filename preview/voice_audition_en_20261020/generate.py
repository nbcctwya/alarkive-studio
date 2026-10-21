"""Generate two matching English auditions with the project's verified TTS setup."""
import asyncio
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from make_voice import synth


async def main():
    text = (HERE / "text.txt").read_text("utf-8").strip()
    records = []
    for name, voice in (("ava", "en-US-AvaNeural"), ("andrew", "en-US-AndrewNeural")):
        output = HERE / f"{name}.mp3"
        word_file = HERE / f"{name}_words.json"
        if output.exists() and word_file.exists():
            words = json.loads(word_file.read_text("utf-8"))
            print(f"[skip] {voice}", flush=True)
        else:
            print(f"[tts] {voice}", flush=True)
            words = await synth(text, voice, "+0%", output)
            if not words:
                raise RuntimeError(f"No word timestamps returned for {voice}")
            word_file.write_text(json.dumps(words, ensure_ascii=False, indent=2), "utf-8")
        records.append({"name": name, "voice": voice, "rate": "+0%",
                        "file": output.name, "words": len(words),
                        "last_word_end_sec": round((words[-1][1] + words[-1][2]) / 1000, 3)})
    (HERE / "results.json").write_text(json.dumps(records, indent=2), "utf-8")
    print(json.dumps(records, indent=2), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
