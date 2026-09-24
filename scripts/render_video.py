# -*- coding: utf-8 -*-
"""Alark Frame v1.0 · Demo 视频最终合成（native 1080x1328 / 半分辨率预览）。

管线：逐镜头 ffmpeg 解码（scale+crop 至 B-roll 区域，30fps rawvideo 帧流）
→ Pillow 合成（静态 Header/Footer 基底 + B-roll 帧 + 预渲染字幕叠层）
→ 管道写入第二个 ffmpeg 进程编码 H.264 + AAC。

用法：
  # 单帧管线验证（抽取 t 秒处的合成帧存 PNG）
  python scripts/render_video.py --project projects/demo001 --frame-test 65.0 \
      --frame-out projects/demo001/output/frame_check.png
  # 前 10 秒预览
  python scripts/render_video.py --project projects/demo001 --mode preview --duration 10
  # 全量
  python scripts/render_video.py --project projects/demo001 --mode preview
  python scripts/render_video.py --project projects/demo001 --mode final
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import imageio_ffmpeg
import yaml
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import generate_frame as gf  # noqa: E402
from build_timeline import parse_srt  # noqa: E402

FPS = 30

MODES = {
    # (宽, 高, 字幕字号起点, 描边, crf, preset, 音频码率, faststart)
    "preview": dict(W=540, H=664, sub_size=24, stroke=2, crf="30",
                    preset="veryfast", abr="128k", faststart=False),
    "final": dict(W=1080, H=1328, sub_size=48, stroke=3, crf="20",
                  preset="slow", abr="192k", faststart=True),
}
# 区域比例（native: header 440 / broll 608 / footer 280，preview 减半）
REGION_SCALE = {"preview": 0.5, "final": 1.0}
SUB_MIN_SIZE_FINAL = 32          # 字幕自动缩小下限（对应 final；preview 减半）
SUB_BOTTOM_UP_FINAL = 70         # 字幕底边距 B-roll 底（60~85 规范取中）
SUB_MARGIN_X_FINAL = 60          # 字幕左右边距


def wrap_cjk(draw, text, font, max_w):
    """按像素宽度贪心折行（CJK 逐字）。"""
    lines, cur, w = [], [], 0.0
    for ch in text:
        cw = draw.textlength(ch, font=font)
        if cur and w + cw > max_w:
            lines.append("".join(cur))
            cur, w = [], 0.0
        cur.append(ch)
        w += cw
    if cur:
        lines.append("".join(cur))
    return lines


def build_subtitle_overlays(entries, fonts, cfg, mode, scale, broll_h):
    """预渲染每条字幕为 B-roll 区域大小的 RGBA 叠层（暖白+黑描边+轻阴影）。"""
    m = MODES[mode]
    W = m["W"]
    sub = cfg["subtitle"]
    max_w = W - 2 * round(SUB_MARGIN_X_FINAL * scale)
    bottom_up = round(SUB_BOTTOM_UP_FINAL * scale)
    size0 = m["sub_size"]
    size_min = max(16, round(SUB_MIN_SIZE_FINAL * scale))
    fill = gf.hex_rgba(sub["color"])
    shadow_off = tuple(round(v * scale) for v in sub["shadow"]["offset"])
    shadow_fill = (0, 0, 0, sub["shadow"]["alpha"])
    overlays = []
    probe = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    for e in entries:
        size = size0
        while True:
            font, stroke_w = fonts.get("sans_cn_heavy", size)
            lines = wrap_cjk(probe, e["text"], font, max_w)
            if len(lines) <= 2 or size <= size_min:
                break
            size -= 2
        lines = lines[:2]
        layer = Image.new("RGBA", (W, broll_h), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        lh = round(size * 1.3)
        y = broll_h - bottom_up - lh * len(lines)
        stroke = m["stroke"]
        for ln in lines:
            lw = d.textlength(ln, font=font)
            x = (W - lw) / 2
            if sub["shadow"]["enabled"]:
                d.text((x + shadow_off[0], y + shadow_off[1]), ln, font=font,
                       fill=shadow_fill, stroke_width=stroke,
                       stroke_fill=shadow_fill)
            d.text((x, y), ln, font=font, fill=fill, stroke_width=stroke,
                   stroke_fill=gf.hex_rgba(sub["stroke_color"]))
            y += lh
        overlays.append({"start": e["start"], "end": e["end"],
                         "layer": layer, "size": size, "lines": len(lines)})
    return overlays


def active_overlay(overlays, idx, t):
    """返回 (当前叠层或 None, 下标)；idx 为上次命中的下标（时间单调前进）。"""
    if idx is not None and overlays[idx]["start"] <= t < overlays[idx]["end"]:
        return overlays[idx]["layer"], idx
    for i, ov in enumerate(overlays):
        if ov["start"] <= t < ov["end"]:
            return ov["layer"], i
    return None, None


def make_decoder(ffmpeg, material, tin, dur, W, broll_h):
    vf = (f"scale={W}:{broll_h}:force_original_aspect_ratio=increase,"
          f"crop={W}:{broll_h},fps={FPS}")
    return subprocess.Popen(
        [ffmpeg, "-ss", f"{tin:.2f}", "-i", material, "-t", f"{dur:.3f}",
         "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)


def make_encoder(ffmpeg, out_path, wav, audio_dur, mode, W, H, limit_dur=None):
    m = MODES[mode]
    cmd = [ffmpeg, "-y",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-",
           "-i", str(wav), "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-crf", m["crf"], "-preset", m["preset"],
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", m["abr"]]
    if m["faststart"]:
        cmd += ["-movflags", "+faststart"]
    cmd += ["-t", f"{(limit_dur or audio_dur):.3f}", str(out_path)]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def load_project(project):
    with open(project / "meta.yaml", encoding="utf-8") as f:
        meta = yaml.safe_load(f)
    with open(ROOT / "config" / "frame_v1.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    timeline = yaml.safe_load((project / "timeline.yaml").read_text("utf-8"))
    entries = parse_srt(project / meta["subtitle"]["file"])
    return meta, cfg, timeline, entries


def frame_test(project, t, out_path):
    meta, cfg, timeline, _entries = load_project(project)
    mode, scale = "final", REGION_SCALE["final"]
    m = MODES[mode]
    W, H = m["W"], m["H"]
    header_h, broll_h = 440, 608
    base = Image.open(project / meta["output"]["title_frame"]).convert("RGB")
    fonts = gf.FontBook(cfg["fonts"])
    overlays = build_subtitle_overlays(_entries, fonts, cfg, mode, scale, broll_h)

    shot = next(s for s in timeline["shots"] if s["start"] <= t < s["end"])
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    rel_t = t - shot["start"]
    dec = make_decoder(ffmpeg, ROOT / shot["material"], shot["in"] + rel_t,
                       1.0, W, broll_h)
    raw = dec.stdout.read(W * broll_h * 3)
    dec.stdout.close()
    dec.wait()
    frame = Image.frombytes("RGB", (W, broll_h), raw)
    layer, _ = active_overlay(overlays, None, t)
    if layer is not None:
        frame = Image.alpha_composite(frame.convert("RGBA"), layer).convert("RGB")
    base.paste(frame, (0, header_h))
    base.save(out_path)
    print(f"[ok] 测试帧 t={t}s  镜头#{shot['seq']}  素材={Path(shot['material']).name}")
    used = [f"{o['lines']}行@{o['size']}px" for o in overlays if o["start"] <= t < o["end"]]
    print(f"[ok] 字幕: {used[0] if used else '无'}")
    print(f"[ok] {out_path}")


def render_wrapped(project, limit_dur=None):
    """wrapped_9_16：正式版上下补黑边成标准 9:16（参数读 config wrapped_9_16 节）。

    从已编码的正式版重编码视频流（pad 滤镜）、音轨直接拷贝，不动帧合成管线。
    """
    meta, cfg, _timeline, _entries = load_project(project)
    w = cfg["wrapped_9_16"]
    src = project / "output/demo001_v1.mp4"
    if not src.exists():
        sys.exit("[error] wrapped 需要正式版先行：--mode final")
    out_path = project / "output/demo001_wrapped.mp4"
    color = "0x" + w["background"].lstrip("#")
    vf = f"pad={w['width']}:{w['height']}:0:{w['padding_top']}:{color}"
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ffmpeg, "-y", "-i", str(src), "-vf", vf,
           "-c:v", "libx264", "-crf", "19", "-preset", "slow",
           "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart"]
    if limit_dur:
        cmd += ["-t", f"{limit_dur:.3f}"]
    cmd.append(str(out_path))
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"[ok] {out_path}  {w['width']}x{w['height']}"
          f"（上下黑边各 {w['padding_top']}px）")
    return out_path


def render(project, mode, limit_dur=None):
    meta, cfg, timeline, entries = load_project(project)
    scale = REGION_SCALE[mode]
    m = MODES[mode]
    W, H = m["W"], m["H"]
    header_h = round(440 * scale)
    broll_h = round(608 * scale)
    audio_dur = float(meta["voice"]["duration_sec"])
    total_dur = min(limit_dur, audio_dur) if limit_dur else audio_dur
    total_frames = round(total_dur * FPS)

    base = Image.open(project / meta["output"]["title_frame"]).convert("RGB")
    if scale != 1.0:
        base = base.resize((W, H), Image.LANCZOS)

    fonts = gf.FontBook(cfg["fonts"])
    overlays = build_subtitle_overlays(entries, fonts, cfg, mode, scale, broll_h)
    sub_sizes = sorted({o["size"] for o in overlays})
    print(f"[info] 字幕字号使用: {sub_sizes}（起点 {m['sub_size']}）")

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    out_path = project / ("output/demo001_preview.mp4" if mode == "preview"
                          else "output/demo001_v1.mp4")
    enc = make_encoder(ffmpeg, out_path, project / meta["voice"]["output_wav"],
                       audio_dur, mode, W, H, limit_dur)

    frame_size = W * broll_h * 3
    sent = 0
    t0 = time.time()
    for shot in timeline["shots"]:
        if sent >= total_frames:
            break
        f0 = round(shot["start"] * FPS)
        f1 = min(round(shot["end"] * FPS), total_frames)
        n_frames = max(0, f1 - f0)
        if n_frames == 0:
            continue
        dur = shot["end"] - shot["start"]
        dec = make_decoder(ffmpeg, ROOT / shot["material"], shot["in"],
                           dur + 0.1, W, broll_h)
        last_raw = None
        got = 0
        while got < n_frames:
            raw = dec.stdout.read(frame_size)
            if len(raw) == frame_size:
                last_raw = raw
            elif last_raw is None:
                break
            raw = last_raw
            t = (f0 + got) / FPS
            layer, oidx = active_overlay(overlays, None, t)
            frame = Image.frombytes("RGB", (W, broll_h), raw)
            if layer is not None:
                frame = Image.alpha_composite(frame.convert("RGBA"), layer)
            base.paste(frame.convert("RGB"), (0, header_h))
            enc.stdin.write(base.tobytes())
            got += 1
            sent += 1
            if sent % 300 == 0:
                el = time.time() - t0
                print(f"[render] {sent}/{total_frames} 帧 "
                      f"({sent / total_frames * 100:.0f}%)  "
                      f"已用 {el / 60:.1f}min  "
                      f"预计还需 {(total_frames - sent) / max(sent, 1) * el / 60:.1f}min",
                      flush=True)
        dec.stdout.close()
        dec.wait()
    enc.stdin.close()
    enc.wait()
    el = time.time() - t0
    print(f"[ok] {out_path}  {sent} 帧  耗时 {el / 60:.1f}min")
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=str(ROOT / "projects" / "demo001"))
    ap.add_argument("--mode", choices=["preview", "final", "wrapped"],
                    default="preview")
    ap.add_argument("--duration", type=float, default=None, help="限制渲染秒数")
    ap.add_argument("--frame-test", type=float, default=None, help="只渲染 t 秒处单帧")
    ap.add_argument("--frame-out", default=None)
    args = ap.parse_args()
    project = Path(args.project)

    if args.frame_test is not None:
        out = args.frame_out or str(project / "output" / "frame_check.png")
        frame_test(project, args.frame_test, out)
    elif args.mode == "wrapped":
        render_wrapped(project, args.duration)
    else:
        render(project, args.mode, args.duration)


if __name__ == "__main__":
    sys.exit(main())
