# -*- coding: utf-8 -*-
"""Alark Frame v1.0 动态标题渲染测试（静态预览，不涉及视频）。

在冻结资产 header_base.png 的预留标题区绘制动态主标题，与黑色 B-roll 占位、
footer_base.png 拼接输出 preview/title_test.png。不修改任何冻结资产文件。

用法（均为可选参数，默认即本次测试用例）：
  python scripts/test_dynamic_title.py
  python scripts/test_dynamic_title.py \
      --title "真正拉开人与人差距的" "从来不是努力" "而是选择" \
      --highlight 选择 \
      --output preview/title_test.png

排版规则：
  - --title 的每个参数是一条语义断行提示；提示内部再按字体实际像素宽度
    （ImageDraw.textlength 逐字测量）贪心换行，禁止按固定字符数断行。
  - --highlight 指定强调词（可多个），逐词匹配、逐字单独着 accent 暖金色。
  - 排版结果超出 header.title_dynamic.reserved_area 时自动逐级缩小字号重排，
    下限 min_size，绝不裁切。
"""
import argparse
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import generate_frame as gf  # noqa: E402  复用 hex_rgba / FontBook

DEFAULT_TITLE = ["真正拉开人与人差距的", "从来不是努力", "而是选择"]
DEFAULT_HIGHLIGHT = ["选择"]


def mark_highlights(line: str, highlights: list[str]) -> list[bool]:
    """按 highlight 词表逐词匹配，返回每个字符是否为强调字。"""
    flags = [False] * len(line)
    for word in highlights:
        start = 0
        while True:
            i = line.find(word, start)
            if i < 0:
                break
            for j in range(i, i + len(word)):
                flags[j] = True
            start = i + len(word)
    return flags


def greedy_wrap(line: str, flags: list[bool], draw: ImageDraw.ImageDraw,
                font, max_width: int) -> list[tuple[str, list[bool], float]]:
    """按字体实际像素宽度贪心换行，返回 [(文本, 强调标记, 行宽)]。"""
    rows, cur, cur_flags, cur_w = [], [], [], 0.0
    for ch, fl in zip(line, flags):
        cw = draw.textlength(ch, font=font)
        if cur and cur_w + cw > max_width:
            rows.append(("".join(cur), cur_flags, cur_w))
            cur, cur_flags, cur_w = [], [], 0.0
        cur.append(ch)
        cur_flags.append(fl)
        cur_w += cw
    if cur:
        rows.append(("".join(cur), cur_flags, cur_w))
    return rows


def layout_title(draw, fonts, td, hints, highlights, size):
    """按给定字号排版，返回 (行列表, 总高, 是否超出预留区)。"""
    ra = td["reserved_area"]
    ratio = td["line_height"] / td["size"]
    line_height = round(size * ratio)
    font, stroke = fonts.get(td["font"], size)
    rows = []
    for hint in hints:
        rows.extend(greedy_wrap(hint, mark_highlights(hint, highlights),
                                draw, font, ra["width"]))
    total_h = line_height * len(rows)
    overflow = (len(rows) > td["max_lines"] or total_h > ra["height"]
                or any(w > ra["width"] for _, _, w in rows))
    return rows, line_height, total_h, overflow


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "config" / "frame_v1.yaml"))
    ap.add_argument("--title", nargs="+", default=DEFAULT_TITLE,
                    help="标题语义断行提示（每参数一行提示，内部仍按像素贪心换行）")
    ap.add_argument("--highlight", nargs="*", default=DEFAULT_HIGHLIGHT,
                    help="强调词列表，着 accent 暖金色")
    ap.add_argument("--output", default=str(ROOT / "preview" / "title_test.png"))
    args = ap.parse_args()

    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    fonts = gf.FontBook(cfg["fonts"])
    td = cfg["header"]["title_dynamic"]
    ra = td["reserved_area"]
    cv = cfg["canvas"]

    # 冻结资产：只读，不修改
    header = Image.open(ROOT / cfg["output"]["header"]).convert("RGBA")
    footer = Image.open(ROOT / cfg["output"]["footer"]).convert("RGBA")

    canvas = Image.new("RGBA", (cv["width"], cv["height"]),
                       gf.hex_rgba(cfg["broll"]["placeholder_color"]))
    canvas.paste(header, (0, 0))
    canvas.paste(footer, (0, cv["header_height"] + cv["broll_height"]))
    draw = ImageDraw.Draw(canvas)

    # 自动缩小字号直至排版落入预留区（带下限保护）
    size = td["size"]
    while True:
        rows, line_height, total_h, overflow = layout_title(
            draw, fonts, td, args.title, args.highlight, size)
        if not overflow or size <= td["min_size"]:
            break
        size -= 2
    if overflow:
        print(f"[warn] 已达字号下限 {td['min_size']} 仍超出预留区，请缩短标题",
              file=sys.stderr)

    font, stroke = fonts.get(td["font"], size)
    color = gf.hex_rgba(td["color"])
    accent = gf.hex_rgba(td["accent_color"])
    x0 = ra["x"]
    y0 = ra["y"] + (ra["height"] - total_h) // 2  # 预留区内垂直居中

    y = y0
    max_w = 0.0
    for text, flags, w in rows:
        cx = x0
        for ch, fl in zip(text, flags):
            fill = accent if fl else color
            draw.text((cx, y), ch, font=font, fill=fill,
                      stroke_width=stroke, stroke_fill=fill)
            cx += draw.textlength(ch, font=font)
        max_w = max(max_w, w)
        y += line_height

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out)

    print(f"[title] 字号={size}  行高={line_height}  行数={len(rows)}")
    for i, (text, flags, w) in enumerate(rows, 1):
        marks = "".join("^" if fl else " " for fl in flags)
        print(f"  行{i}: {text}  (宽 {w:.0f}px)  {marks.strip() and '高亮: ' + marks}")
    print(f"[title] bounding box = ({x0}, {y0}, {x0 + round(max_w)}, {y0 + total_h})")
    print(f"[title] 预留区 = ({ra['x']}, {ra['y']}, "
          f"{ra['x'] + ra['width']}, {ra['y'] + ra['height']})")
    print(f"[fonts] {td['font']}: {fonts.used[td['font']]}")
    print(f"[ok] {out}")


if __name__ == "__main__":
    sys.exit(main())
