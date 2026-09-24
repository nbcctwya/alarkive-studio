# -*- coding: utf-8 -*-
"""每期选片清单：timeline 定稿后，从每个入选素材的 in/out 中点抽代表帧，
拼成缩略图网格供合成前看图审片（内部工具，不套品牌视觉）。

用法：python scripts/make_shot_list.py --project projects/demo001
输出：projects/<id>/selected_broll/shot_list.jpg + 控制台文本清单
"""
import argparse
import math
import subprocess
import sys
from io import BytesIO
from pathlib import Path

import imageio_ffmpeg
import yaml
from PIL import Image, ImageDraw, ImageStat

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import generate_frame as gf  # noqa: E402  复用 FontBook（中文字体回退链）

COLS = 5
THUMB_W, THUMB_H = 320, 180
CELL_PAD = 10
CAPTION_H = 96
BG = (245, 245, 243)
FG = (30, 30, 30)
FG_WEAK = (110, 110, 110)
DARK_MEAN = 8  # 判定黑帧的平均亮度阈值


def grab_frame(ffmpeg: str, material: Path, t: float) -> Image.Image:
    """从素材 t 秒处抽一帧（-ss 前置快速定位）。"""
    r = subprocess.run([ffmpeg, "-ss", f"{t:.2f}", "-i", str(material),
                        "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
                       capture_output=True, check=True)
    return Image.open(BytesIO(r.stdout)).convert("RGB")


def center_crop_thumb(img: Image.Image) -> Image.Image:
    """等比缩放 + center crop 到 THUMB_W x THUMB_H，不拉伸。"""
    scale = max(THUMB_W / img.width, THUMB_H / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)),
                     Image.LANCZOS)
    x = (img.width - THUMB_W) // 2
    y = (img.height - THUMB_H) // 2
    return img.crop((x, y, x + THUMB_W, y + THUMB_H))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=str(ROOT / "projects" / "demo001"))
    args = ap.parse_args()
    project = Path(args.project)

    timeline = yaml.safe_load((project / "timeline.yaml").read_text("utf-8"))
    shots = timeline["shots"]
    cfg = yaml.safe_load((ROOT / "config" / "frame_v1.yaml").read_text("utf-8"))
    fonts = gf.FontBook(cfg["fonts"])
    f_cap, _ = fonts.get("sans_cn_heavy", 20)
    f_weak, _ = fonts.get("sans_cn_heavy", 17)

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    rows = math.ceil(len(shots) / COLS)
    cell_w, cell_h = THUMB_W + CELL_PAD * 2, THUMB_H + CAPTION_H + CELL_PAD
    sheet = Image.new("RGB", (cell_w * COLS, cell_h * rows), BG)
    d = ImageDraw.Draw(sheet)

    for i, sh in enumerate(shots):
        material = ROOT / sh["material"]
        mid = (sh["in"] + sh["out"]) / 2
        img = grab_frame(ffmpeg, material, mid)
        # 黑帧则改抽区间 1/4、3/4 处
        if ImageStat.Stat(img.convert("L").resize((32, 18))).mean[0] < DARK_MEAN:
            for alt in (sh["in"] + (sh["out"] - sh["in"]) * 0.25,
                        sh["in"] + (sh["out"] - sh["in"]) * 0.75):
                img = grab_frame(ffmpeg, material, alt)
                if ImageStat.Stat(img.convert("L").resize((32, 18))).mean[0] \
                        >= DARK_MEAN:
                    print(f"[note] 镜头{sh['seq']} 中点黑帧，改抽 {alt:.1f}s")
                    break
        thumb = center_crop_thumb(img)

        col, row = i % COLS, i // COLS
        x0, y0 = col * cell_w + CELL_PAD, row * cell_h + CELL_PAD
        sheet.paste(thumb, (x0, y0))
        d.rectangle((x0, y0, x0 + THUMB_W - 1, y0 + THUMB_H - 1),
                    outline=(200, 200, 200))
        cy = y0 + THUMB_H + 8
        d.text((x0 + 2, cy),
               f"#{sh['seq']:02d}  {sh['start']:.1f}–{sh['end']:.1f}s",
               font=f_cap, fill=FG)
        d.text((x0 + 2, cy + 28), sh["category"], font=f_weak, fill=FG_WEAK)
        text = sh.get("srt_text", "")
        text = text[:16] + "…" if len(text) > 16 else text
        d.text((x0 + 2, cy + 54), text, font=f_weak, fill=FG)

        print(f"  #{sh['seq']:02d} {sh['start']:6.1f}–{sh['end']:6.1f}s "
              f"{sh['category']:<10} {Path(sh['material']).name[:48]:<48} "
              f"{text}")

    out = project / "selected_broll" / "shot_list.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=90)
    print(f"[ok] {out}  {sheet.width}x{sheet.height}  "
          f"{len(shots)} 格（{COLS} 列 x {rows} 行）")


if __name__ == "__main__":
    sys.exit(main())
