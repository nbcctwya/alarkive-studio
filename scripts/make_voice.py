# -*- coding: utf-8 -*-
"""项目 TTS 配音 + 同步字幕生成（edge-tts）。

- 声音：优先 meta.yaml 的 voice_primary（zh-CN-YunjianNeural），失败回退 fallback。
- 流式接收音频与 WordBoundary 事件，逐词时间戳按 script 非空行分组成 SRT。
- 文本-时间轴对齐：词文本与各行做归一化（去标点空白）顺序匹配，避免偏移错位。
- 网络失败自动重试（默认 3 次）。
- 同时用 imageio-ffmpeg 的 ffmpeg 转出 wav 供后续合成。

用法：python scripts/make_voice.py --project projects/demo001
"""
import argparse
import asyncio
import re
import subprocess
import sys
import time
import wave
from pathlib import Path

import edge_tts
import imageio_ffmpeg
import yaml

ROOT = Path(__file__).resolve().parent.parent

RETRIES = 3
GAP_MS = 60  # 相邻字幕条目之间的最小间隔


def norm(s: str) -> str:
    """归一化：只保留中日韩文字与字母数字，忽略标点/空白/引号差异。"""
    return "".join(re.findall(r"[0-9A-Za-z一-鿿]", s))


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


def assign_words_to_lines(lines: list[str], words: list[tuple]):
    """顺序匹配：把词事件分配到各行，返回每行 (start_ms, end_ms)。"""
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=str(ROOT / "projects" / "demo001"))
    args = ap.parse_args()
    project = Path(args.project)

    with open(project / "meta.yaml", encoding="utf-8") as f:
        meta = yaml.safe_load(f)
    vc = meta["voice"]

    lines = [ln.strip() for ln in (project / meta["script"]["file"])
             .read_text(encoding="utf-8").splitlines() if ln.strip()]
    text = "\n".join(lines)
    print(f"[info] 非空段落 {len(lines)} 行，共 {len(text)} 字符")

    mp3_path = project / vc["output_mp3"]
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
    spans = assign_words_to_lines(lines, words)
    srt_path = project / meta["subtitle"]["file"]
    srt_path.parent.mkdir(parents=True, exist_ok=True)
    last_end = write_srt(lines, spans, srt_path)
    n_entries = sum(1 for st, _ in spans if st is not None)

    # mp3 -> wav（供后续合成）
    wav_path = project / vc["output_wav"]
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ffmpeg, "-y", "-i", str(mp3_path), str(wav_path)],
                   check=True, capture_output=True)

    # 时长核对：用标准库 wave 读 wav（系统无 ffprobe，pydub 无法直接探时长）
    with wave.open(str(wav_path), "rb") as wf:
        audio_ms = wf.getnframes() / wf.getframerate() * 1000
    print(f"[voice] 声音={used}  rate={vc['rate']}")
    print(f"[voice] 音频时长={audio_ms / 1000:.2f}s  "
          f"SRT最后结束={last_end / 1000:.2f}s  差={abs(audio_ms - last_end) / 1000:.2f}s")
    print(f"[subtitle] 条目数={n_entries}  词事件数={len(words)}")
    print(f"[ok] {mp3_path}")
    print(f"[ok] {wav_path}")
    print(f"[ok] {srt_path}")


if __name__ == "__main__":
    sys.exit(main())
