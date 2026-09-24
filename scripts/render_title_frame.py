# -*- coding: utf-8 -*-
"""项目标题帧渲染：读取项目 title.txt，在冻结的 header_base 上绘制动态标题。

复用 scripts/test_dynamic_title.py 的排版逻辑（像素测量贪心换行、强调词着色、
超出预留区自动降字号），不修改任何冻结资产。

用法：
  python scripts/render_title_frame.py --project projects/demo001
"""
import argparse
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import generate_frame as gf  # noqa: E402
from test_dynamic_title import layout_title  # noqa: E402


def render_title_frame(project: Path, config: Path) -> Path:
    with open(config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    with open(project / "meta.yaml", encoding="utf-8") as f:
        meta = yaml.safe_load(f)

    hints = (project / meta["title"]["file"]).read_text(encoding="utf-8") \
        .splitlines()
    hints = [ln.strip() for ln in hints if ln.strip()]
    highlights = list(meta["title"]["highlight"])

    fonts = gf.FontBook(cfg["fonts"])
    td = cfg["header"]["title_dynamic"]
    ra = td["reserved_area"]
    cv = cfg["canvas"]

    header = Image.open(ROOT / cfg["output"]["header"]).convert("RGBA")
    footer = Image.open(ROOT / cfg["output"]["footer"]).convert("RGBA")
    canvas = Image.new("RGBA", (cv["width"], cv["height"]),
                       gf.hex_rgba(cfg["broll"]["placeholder_color"]))
    canvas.paste(header, (0, 0))
    canvas.paste(footer, (0, cv["header_height"] + cv["broll_height"]))
    draw = ImageDraw.Draw(canvas)

    size = td["size"]
    while True:
        rows, line_height, total_h, overflow = layout_title(
            draw, fonts, td, hints, highlights, size)
        if not overflow or size <= td["min_size"]:
            break
        size -= 2
    if overflow:
        print(f"[warn] 已达字号下限 {td['min_size']} 仍超出预留区", file=sys.stderr)

    font, stroke = fonts.get(td["font"], size)
    color = gf.hex_rgba(td["color"])
    accent = gf.hex_rgba(td["accent_color"])
    x0 = ra["x"]
    y0 = ra["y"] + (ra["height"] - total_h) // 2

    y = y0
    for text, flags, _w in rows:
        cx = x0
        for ch, fl in zip(text, flags):
            fill = accent if fl else color
            draw.text((cx, y), ch, font=font, fill=fill,
                      stroke_width=stroke, stroke_fill=fill)
            cx += draw.textlength(ch, font=font)
        y += line_height

    out = project / meta["output"]["title_frame"]
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out)

    print(f"[title] 字号={size}  行高={line_height}  行数={len(rows)}")
    for i, (text, _flags, w) in enumerate(rows, 1):
        print(f"  行{i}: {text}  (宽 {w:.0f}px)")
    print(f"[title] bounding box = ({x0}, {y0}, "
          f"{x0 + round(max(w for _, _, w in rows))}, {y0 + total_h})")
    print(f"[fonts] {td['font']}: {fonts.used[td['font']]}")
    print(f"[ok] {out}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=str(ROOT / "projects" / "demo001"))
    ap.add_argument("--config", default=str(ROOT / "config" / "frame_v1.yaml"))
    args = ap.parse_args()
    render_title_frame(Path(args.project), Path(args.config))


if __name__ == "__main__":
    sys.exit(main())
