# -*- coding: utf-8 -*-
"""Alark Cover v1.0 · 统一封面生成（竖版 1080x1440 / 横版 1920x1080）。

复用（不修改）：
  - generate_frame.make_textured_base  等高线纹理（config/frame_v1.yaml texture）
  - generate_frame.FontBook / hex_rgba / TextPen
  - test_dynamic_title.layout_title / mark_highlights  主标题排版
版式参数全部来自 config/cover_v1.yaml。

标题输入优先级：项目 meta.yaml 的 cover 字段 -> 项目 title.txt -> 命令行。

用法：
  python scripts/generate_cover.py --project projects/demo001 --mode vertical
  python scripts/generate_cover.py --project projects/demo001 --mode horizontal
  python scripts/generate_cover.py --project projects/demo001 --mode both
  python scripts/generate_cover.py --title-lines "真正拉开人与人差距的" \
      "从来不是努力" "而是选择" --highlight 选择 --mode both
"""
import argparse
import shutil
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import generate_frame as gf  # noqa: E402
from test_dynamic_title import layout_title  # noqa: E402


# ------------------------------------------------------------ 绘制辅助

def draw_motif(img: Image.Image, motif: dict, W: int, H: int) -> None:
    """极简路径意象：低透明二次贝塞尔曲线（固定几何，无随机）。"""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for ln in motif["lines"]:
        p0 = (ln["p0"][0] * W, ln["p0"][1] * H)
        c = (ln["c"][0] * W, ln["c"][1] * H)
        p1 = (ln["p1"][0] * W, ln["p1"][1] * H)
        pts = []
        for i in range(61):
            t = i / 60
            x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t ** 2 * p1[0]
            y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t ** 2 * p1[1]
            pts.append((x, y))
        d.line(pts, fill=gf.hex_rgba(motif["color"], ln["alpha"]),
               width=ln["width"], joint="curve")
    img.alpha_composite(layer)


def draw_title(img, draw, fonts, td, hints, highlights) -> None:
    """复用 test_dynamic_title.layout_title 排版，逐字着色绘制。"""
    ra = td["reserved_area"]
    size = td["size"]
    while True:
        rows, line_height, total_h, overflow = layout_title(
            draw, fonts, td, hints, highlights, size)
        if not overflow or size <= td["min_size"]:
            break
        size -= 2
    if overflow:
        print(f"[warn] 标题已达字号下限 {td['min_size']} 仍超出预留区",
              file=sys.stderr)
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
    print(f"[title] 字号={size}  行数={len(rows)}  bbox=({x0},{y0},"
          f"{x0 + round(max(w for _, _, w in rows))},{y0 + total_h})")


def draw_brand(img, draw, pen, fonts, common, bc) -> None:
    """底部品牌区：圆形 Logo + Alark知新录 + slogan。"""
    b = common["brand"]
    lg = bc["logo"]
    logo = Image.open(ROOT / b["logo_file"]).convert("RGBA")
    logo = logo.resize((lg["size"], lg["size"]), Image.LANCZOS)
    img.alpha_composite(logo, (lg["x"], lg["y"]))
    draw = ImageDraw.Draw(img, "RGBA")

    nm = bc["name"]
    fill = gf.hex_rgba(b["name_color"])
    en = b["name_en"]
    en_font, en_stroke = fonts.get(en["font"], nm["en_size"])
    x = nm["x"]
    baseline = nm["baseline"]
    for ch in en["text"]:
        draw.text((x, baseline), ch, font=en_font, fill=fill, anchor="ls",
                  stroke_width=en_stroke, stroke_fill=fill)
        x += draw.textlength(ch, font=en_font) + en["tracking"]
    x += b["en_cn_gap"]
    cn = b["name_cn"]
    cn_font, cn_stroke = fonts.get(cn["font"], nm["cn_size"])
    for ch in cn["text"]:
        draw.text((x, baseline), ch, font=cn_font, fill=fill, anchor="ls",
                  stroke_width=cn_stroke, stroke_fill=fill)
        x += draw.textlength(ch, font=cn_font) + cn["tracking"]

    s = b["slogan"]
    sc = bc["slogan"]
    pen.write(s["text"], sc["x"], sc["y"], role=s["font"], size=sc["size"],
              tracking=s["tracking"],
              fill=gf.hex_rgba(s["color"], s["alpha"]))


def render_cover(mode: str, cover_cfg: dict, frame_cfg: dict, fonts,
                 hints: list[str], highlights: list[str]) -> Image.Image:
    mc = cover_cfg[mode]
    cm = cover_cfg["common"]
    W, H = mc["width"], mc["height"]

    # 背景：frame_v1 同款等高线纹理（读 frame_v1 的 colors/texture）
    img = gf.make_textured_base(W, H, frame_cfg)
    draw = ImageDraw.Draw(img, "RGBA")
    pen = gf.TextPen(draw, fonts)

    mh = {**cm["masthead"], **mc["masthead"]}
    pen.write(mh["text"], mh["x"], mh["y"], role=mh["font"], size=mh["size"],
              tracking=mh["tracking"], fill=gf.hex_rgba(mh["color"], mh["alpha"]))

    sg = {**cm["signature"], **mc["signature"]}
    sig = Image.open(ROOT / sg["file"]).convert("RGBA")
    ratio = sg["width"] / sig.width
    sig = sig.resize((sg["width"], round(sig.height * ratio)), Image.LANCZOS)
    sig.putalpha(sig.getchannel("A").point(lambda v: round(v * sg["opacity"])))
    img.alpha_composite(sig, (W - sg["margin_right"] - sig.width,
                              sg["margin_top"]))
    draw = ImageDraw.Draw(img, "RGBA")

    for key in ("aux_1", "aux_2"):
        ax = {**cm[key], **mc[key]}
        y = ax["y_top"]
        dash = ax.get("dash") or ax.get("dashes")
        if key == "aux_2" and dash:  # 上横线
            draw.rectangle((ax["x_right"] - dash["width"], y, ax["x_right"],
                            y + dash["height"] - 1),
                           fill=gf.hex_rgba(dash["color"], dash["alpha"]))
            y += dash["height"] + dash["gap"]
        for ln in ax["lines"]:
            pen.write(ln, ax["x_right"], y, role=ax["font"], size=ax["size"],
                      tracking=ax["tracking"],
                      fill=gf.hex_rgba(ax["color"], ax["alpha"]), align="right")
            y += ax["line_height"]
        if dash:  # 下横线
            y += dash["gap"]
            draw.rectangle((ax["x_right"] - dash["width"], y, ax["x_right"],
                            y + dash["height"] - 1),
                           fill=gf.hex_rgba(dash["color"], dash["alpha"]))

    draw_motif(img, mc["motif"], W, H)
    draw = ImageDraw.Draw(img, "RGBA")

    td = {**cm["title"], **mc["title"]}
    rule = {**cm["title"]["rule"], **mc["title"]["rule"]}
    td.pop("rule")
    draw.rectangle((rule["x"], rule["y_top"], rule["x"] + rule["width"] - 1,
                    rule["y_bottom"]), fill=gf.hex_rgba(rule["color"], rule["alpha"]))
    draw_title(img, draw, fonts, td, hints, highlights)

    pen = gf.TextPen(draw, fonts)
    draw_brand(img, draw, pen, fonts, cm, mc["brand"])
    return img


# ------------------------------------------------------------ 输入解析与输出

def resolve_inputs(project: Path | None, args) -> tuple[list[str], list[str]]:
    lines, highlights = None, None
    if project is not None:
        meta_path = project / "meta.yaml"
        if meta_path.exists():
            meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
            cover = meta.get("cover", {})
            highlights = (cover.get("highlight") or meta.get("title_highlight")
                          or meta.get("title", {}).get("highlight"))
            tf = project / meta.get("title", {}).get("file", "title.txt")
            if tf.exists():
                lines = [ln.strip() for ln in
                         tf.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        lines = args.title_lines
    if not highlights:
        highlights = args.highlight
    if not lines:
        sys.exit("[error] 无标题输入（meta/title.txt/--title-lines 均为空）")
    return lines, highlights or []


def make_contact(imgs: dict[str, Image.Image], cc: dict, fonts,
                 out: Path) -> None:
    band, gap, margin = cc["band_height"], cc["gap"], cc["margin"]
    v = imgs["vertical"]
    vh = cc["vertical_height"]
    v = v.resize((round(v.width * vh / v.height), vh), Image.LANCZOS)
    h = imgs["horizontal"]
    hw = cc["horizontal_width"]
    h = h.resize((hw, round(h.height * hw / h.width)), Image.LANCZOS)

    W = margin * 2 + v.width + gap + h.width
    H = margin * 2 + band + max(v.height, h.height)
    comp = Image.new("RGB", (W, H), gf.hex_rgba(cc["background"])[:3])
    d = ImageDraw.Draw(comp)
    font, _ = fonts.get(cc["label_font"], cc["label_size"])
    color = gf.hex_rgba(cc["label_color"])[:3]
    d.text((margin + v.width // 2, margin + band // 2), "vertical",
           font=font, fill=color, anchor="mm")
    d.text((margin + v.width + gap + h.width // 2, margin + band // 2),
           "horizontal", font=font, fill=color, anchor="mm")
    comp.paste(v, (margin, margin + band))
    comp.paste(h, (margin + v.width + gap, margin + band))
    comp.save(out, quality=92)
    print(f"[ok] {out}  {W}x{H}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=None)
    ap.add_argument("--mode", choices=["vertical", "horizontal", "both"],
                    default="both")
    ap.add_argument("--title-lines", nargs="+", default=None)
    ap.add_argument("--highlight", nargs="*", default=None)
    args = ap.parse_args()

    frame_cfg = yaml.safe_load(
        (ROOT / "config" / "frame_v1.yaml").read_text(encoding="utf-8"))
    cover_cfg = yaml.safe_load(
        (ROOT / "config" / "cover_v1.yaml").read_text(encoding="utf-8"))
    fonts = gf.FontBook(frame_cfg["fonts"])

    project = Path(args.project) if args.project else None
    hints, highlights = resolve_inputs(project, args)
    print(f"[info] 标题 {len(hints)} 行 / 强调词 {highlights}")

    modes = ["vertical", "horizontal"] if args.mode == "both" else [args.mode]
    imgs = {}
    for mode in modes:
        img = render_cover(mode, cover_cfg, frame_cfg, fonts, hints, highlights)
        imgs[mode] = img
        if project is not None:
            p = project / "output" / f"cover_{mode}_v1.png"
            p.parent.mkdir(parents=True, exist_ok=True)
            img.convert("RGB").save(p)
            print(f"[ok] {p}  {img.width}x{img.height}")
        pv = ROOT / "preview" / f"cover_v1_{mode}_preview.png"
        pv.parent.mkdir(parents=True, exist_ok=True)
        img.convert("RGB").save(pv)
        print(f"[ok] {pv}")

    if len(imgs) == 2:
        make_contact(imgs, cover_cfg["contact"], fonts,
                     ROOT / "preview" / "cover_v1_contact.jpg")
    else:  # 单模式也出 contact：读另一张已有输出补齐
        other = "horizontal" if modes[0] == "vertical" else "vertical"
        cand = []
        if project is not None:
            cand.append(project / "output" / f"cover_{other}_v1.png")
        cand.append(ROOT / "preview" / f"cover_v1_{other}_preview.png")
        for c in cand:
            if c.exists():
                imgs[other] = Image.open(c).convert("RGB")
                make_contact(imgs, cover_cfg["contact"], fonts,
                             ROOT / "preview" / "cover_v1_contact.jpg")
                break


if __name__ == "__main__":
    sys.exit(main())
