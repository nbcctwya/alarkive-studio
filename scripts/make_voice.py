# -*- coding: utf-8 -*-
"""项目 TTS 配音 + 同步字幕生成（edge-tts）。

- 声音：使用各项目 meta.yaml 的 voice_primary，失败回退 voice_fallback。
- 新项目默认晓伊（zh-CN-XiaoyiNeural），备选云希（zh-CN-YunxiNeural），正常语速。
- 流式接收音频与 WordBoundary 事件，逐词时间戳按 script 非空行分组成 SRT。
- 可选 script.narration_file 保存自然段朗读稿，字幕仍按 script.file 分行；两者正文必须一致。
- 文本-时间轴对齐：词文本与各行做归一化（去标点空白）顺序匹配，避免偏移错位。
- 网络失败自动重试（默认 3 次）。
- 同时用 imageio-ffmpeg 的 ffmpeg 转出 wav 供后续合成。

用法：python scripts/make_voice.py --project projects/demo001
"""
import argparse
import asyncio
import html
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import wave
from pathlib import Path

import edge_tts
import imageio_ffmpeg
import yaml

from language_profiles import project_language

ROOT = Path(__file__).resolve().parent.parent

RETRIES = 3
GAP_MS = 60  # 相邻字幕条目之间的最小间隔


def norm(s: str, language: str = "zh") -> str:
    """归一化：只保留中日韩文字与字母数字，忽略标点/空白/引号差异。"""
    if language == "en":
        s = unicodedata.normalize("NFKC", html.unescape(s)).casefold()
        return "".join(ch for ch in s if ch.isalnum())
    return "".join(re.findall(r"[0-9A-Za-z一-鿿]", s))


def narration_key(text: str, language: str):
    if language == "en":
        text = unicodedata.normalize("NFKC", html.unescape(text))
        # Whitespace can move between complete words, but "now here" is not "nowhere".
        return tuple(norm(word, "en") for word in re.findall(
            r"[^\W_]+(?:['’][^\W_]+)*", text))
    return norm(text)


async def synth(text: str, voice: str, rate: str, mp3_path: Path):
    """流式合成，返回 [(word, offset_ms, duration_ms)]。"""
    audio = bytearray()
    words = []
    communicate = edge_tts.Communicate(text, voice, rate=rate,
                                       boundary="WordBoundary")
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio.extend(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            # 兼容不同版本的键名大小写
            off = chunk.get("offset", chunk.get("Offset"))
            dur = chunk.get("duration", chunk.get("Duration"))
            words.append((chunk["text"], off / 10_000, dur / 10_000))
    mp3_path.write_bytes(bytes(audio))
    return words


def assign_english_words(lines: list[str], words: list[tuple]):
    """Match every English word before writing captions; fail rather than drop text."""
    norm_lines = [norm(line, "en") for line in lines]
    events = [(norm(word, "en"), off, dur) for word, off, dur in words
              if norm(word, "en")]
    expected = "".join(norm_lines)
    actual = "".join(word for word, _, _ in events)
    if not expected or any(not line for line in norm_lines) or expected != actual:
        raise ValueError("English speech word events do not match the complete script. "
                         "Check numbers, abbreviations and the narration before continuing.")
    spans = [[None, None] for _ in lines]
    li, consumed = 0, 0
    for word, off, dur in events:
        while consumed == len(norm_lines[li]):
            li, consumed = li + 1, 0
        if consumed + len(word) > len(norm_lines[li]):
            raise ValueError("An English caption boundary splits a spoken word. "
                             "Move the line break to a word boundary.")
        if spans[li][0] is None:
            spans[li][0] = off
        spans[li][1] = off + dur
        consumed += len(word)
    return spans


def assign_words_to_lines(lines: list[str], words: list[tuple], language: str = "zh"):
    """顺序匹配：把词事件分配到各行，返回每行 (start_ms, end_ms)。"""
    if language == "en":
        return assign_english_words(lines, words)
    norm_lines = [norm(ln) for ln in lines]
    spans = [[None, None] for _ in lines]
    li = 0          # 当前行
    pos = 0         # 当前行归一化文本的消耗位置
    unmatched = 0
    for word, off, dur in words:
        wn = norm(word)
        if not wn:
            continue
        # 跳过已被完全消耗的行
        while li < len(lines) and pos >= len(norm_lines[li]):
            li += 1
            pos = 0
        if li >= len(lines):
            unmatched += 1
            continue
        if norm_lines[li].startswith(wn, pos):
            if spans[li][0] is None:
                spans[li][0] = off
            spans[li][1] = off + dur
            pos += len(wn)
        else:
            # 尝试推进到后续行（容错：TTS 分词与原文偶发不对齐）
            advanced = False
            for nj in range(li + 1, len(lines)):
                if norm_lines[nj].startswith(wn):
                    li, pos = nj, len(wn)
                    if spans[li][0] is None:
                        spans[li][0] = off
                    spans[li][1] = off + dur
                    advanced = True
                    break
            if not advanced:
                unmatched += 1
    if unmatched:
        print(f"[warn] {unmatched} 个词未能匹配到任何行")
    return spans


def srt_ts(ms: float) -> str:
    ms = max(0, round(ms))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(lines: list[str], spans: list[list], srt_path: Path) -> float:
    entries = []
    prev_end = 0.0
    for ln, (st, en) in zip(lines, spans):
        if st is None:
            continue
        st = max(st, prev_end)  # 保证单调不重叠
        en = max(en, st + 200)
        entries.append((st, en, ln))
        prev_end = en + GAP_MS
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, (st, en, ln) in enumerate(entries, 1):
            f.write(f"{i}\n{srt_ts(st)} --> {srt_ts(en)}\n{ln}\n\n")
    return entries[-1][1] if entries else 0.0


def promote_staged_file(source: Path, target: Path) -> None:
    """Publish complete bytes with the destination directory's Windows ACL.

    Renaming out of TemporaryDirectory can retain its owner-only inherited ACL
    on Windows, leaving the renderer unable to read a voice created by another
    process account. A sibling temporary file inherits the project's ACL.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    pending = None
    try:
        with tempfile.NamedTemporaryFile(
                prefix=f".{target.name}.", suffix=".tmp",
                dir=target.parent, delete=False) as output:
            pending = Path(output.name)
            with source.open("rb") as input_file:
                shutil.copyfileobj(input_file, output)
        pending.replace(target)
    finally:
        if pending is not None:
            pending.unlink(missing_ok=True)


def build_voice(project: Path, meta: dict, lines: list[str], text: str,
                work_dir: Path | None = None) -> None:
    language = project_language(meta)
    vc = meta["voice"]
    mp3_target = project / vc["output_mp3"]
    srt_target = project / meta["subtitle"]["file"]
    wav_target = project / vc["output_wav"]
    mp3_path = work_dir / "voice.mp3" if work_dir is not None else mp3_target
    srt_path = work_dir / "subtitle.srt" if work_dir is not None else srt_target
    wav_path = work_dir / "voice.wav" if work_dir is not None else wav_target
    mp3_path.parent.mkdir(parents=True, exist_ok=True)
    voices = [vc["voice_primary"], vc["voice_fallback"]]

    words, used = None, None
    for voice in voices:
        for attempt in range(1, RETRIES + 1):
            try:
                print(f"[tts] 声音={voice}  第 {attempt} 次尝试…")
                words = asyncio.run(synth(text, voice, vc["rate"], mp3_path))
                used = voice
                break
            except Exception as e:
                print(f"[tts] 失败: {e}")
                time.sleep(2 * attempt)
        if words:
            break
    if not words:
        sys.exit("[error] TTS 合成失败（两种声音均已重试）")

    # 字幕
    spans = assign_words_to_lines(lines, words, language)
    srt_path.parent.mkdir(parents=True, exist_ok=True)
    last_end = write_srt(lines, spans, srt_path)
    n_entries = sum(1 for st, _ in spans if st is not None)

    # mp3 -> wav（供后续合成）
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ffmpeg, "-y", "-i", str(mp3_path), str(wav_path)],
                   check=True, capture_output=True)

    # 时长核对：用标准库 wave 读 wav（系统无 ffprobe，pydub 无法直接探时长）
    with wave.open(str(wav_path), "rb") as wf:
        audio_ms = wf.getnframes() / wf.getframerate() * 1000
    if work_dir is not None:
        # Keep the previous complete output intact when English alignment fails.
        for source, target in ((mp3_path, mp3_target), (srt_path, srt_target),
                               (wav_path, wav_target)):
            promote_staged_file(source, target)
    vc["voice_used"] = used
    vc["duration_sec"] = round(audio_ms / 1000, 2)
    meta["subtitle"]["entries"] = n_entries
    (project / "meta.yaml").write_text(
        yaml.safe_dump(meta, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"[voice] 声音={used}  rate={vc['rate']}")
    print(f"[voice] 音频时长={audio_ms / 1000:.2f}s  "
          f"SRT最后结束={last_end / 1000:.2f}s  差={abs(audio_ms - last_end) / 1000:.2f}s")
    print(f"[subtitle] 条目数={n_entries}  词事件数={len(words)}")
    print(f"[ok] {mp3_target}")
    print(f"[ok] {wav_target}")
    print(f"[ok] {srt_target}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=str(ROOT / "projects" / "demo001"))
    args = ap.parse_args()
    project = Path(args.project)
    with open(project / "meta.yaml", encoding="utf-8") as f:
        meta = yaml.safe_load(f)
    language = project_language(meta)
    lines = [ln.strip().replace("**", "") for ln in (project / meta["script"]["file"])
             .read_text(encoding="utf-8").splitlines() if ln.strip()]
    text = "\n".join(lines)
    narration_file = meta["script"].get("narration_file")
    if narration_file:
        narration = (project / narration_file).read_text(encoding="utf-8").replace("**", "").strip()
        if narration_key(narration, language) != narration_key(text, language):
            sys.exit("[error] 朗读稿与字幕稿正文不一致，请先同步两份文稿（允许标点和断行不同）")
        text = narration
        print(f"[info] 使用自然段朗读稿 {narration_file}")
    print(f"[info] 非空段落 {len(lines)} 行，共 {len(text)} 字符")
    if language == "en":
        with tempfile.TemporaryDirectory(prefix=".voice-en-", dir=project) as temp:
            build_voice(project, meta, lines, text, Path(temp))
    else:
        build_voice(project, meta, lines, text)


if __name__ == "__main__":
    sys.exit(main())
