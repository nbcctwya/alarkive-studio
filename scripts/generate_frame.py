# -*- coding: utf-8 -*-
"""Alark Frame v1.0 底图生成脚本。

读取 config/frame_v1.yaml，生成：
  - assets/generated/header_base.png   1080x440（含全部 Header 固定元素，不含动态主标题）
  - assets/generated/footer_base.png   1080x280（含全部 Footer 固定元素）
  - preview/frame_v1_preview.png       1080x1328（Header + 黑色 B-roll 占位 + Footer）

用法：python scripts/generate_frame.py [--config config/frame_v1.yaml]
所有纹理使用固定 seed，输出完全可重复。
"""
import argparse
import random
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent


# ------------------------------------------------------------ 基础工具

def hex_rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)


def shift_lightness(rgb: tuple[int, int, int], delta: int) -> tuple[int, int, int]:
    return tuple(max(0, min(255, c + delta)) for c in rgb)


class FontBook:
    """按 config.fonts 的角色候选链加载字体，记录实际命中的字体。"""

    def __init__(self, fonts_cfg: dict):
        self.cfg = fonts_cfg
        self._cache: dict[tuple[str, int], tuple[ImageFont.FreeTypeFont, int]] = {}
        self.used: dict[str, str] = {}

    def get(self, role: str, size: int) -> tuple[ImageFont.FreeTypeFont, int]:
        """返回 (font, stroke_width)。"""
        key = (role, size)
        if key in self._cache:
            return self._cache[key]
        last_err = None
        for cand in self.cfg[role]:
            path, index = cand["path"], cand.get("index", 0)
            try:
                font = ImageFont.truetype(path, size, index=index)
                stroke = int(cand.get("stroke_width", 0))
                self._cache[key] = (font, stroke)
                self.used.setdefault(role, f"{path} (index={index}, stroke={stroke})")
                return font, stroke
            except Exception as e:  # 字体不存在 -> 试下一个候选
                last_err = e
        raise RuntimeError(f"字体角色 {role!r} 的所有候选均加载失败: {last_err}")


class TextPen:
    """逐字符绘制带字距（tracking）的文本，支持左/右/居中对齐。"""

    def __init__(self, draw: ImageDraw.ImageDraw, fonts: FontBook):
        self.draw = draw
        self.fonts = fonts

    def width(self, text: str, role: str, size: int, tracking: int) -> float:
        font, stroke = self.fonts.get(role, size)
        w = sum(self.draw.textlength(ch, font=font) for ch in text)
        return w + tracking * max(0, len(text) - 1) + stroke * 2

    def write(self, text: str, x: int, y: int, *, role: str, size: int,
              tracking: int, fill: tuple, align: str = "left") -> None:
        font, stroke = self.fonts.get(role, size)
        if align != "left":
            total = self.width(text, role, size, tracking)
            if align == "right":
                x -= total
            elif align == "center":
                x -= total / 2
            else:
                raise ValueError(f"未知对齐方式: {align}")
        cx = x
        for ch in text:
            self.draw.text((cx, y), ch, font=font, fill=fill,
                           stroke_width=stroke, stroke_fill=fill)
            cx += self.draw.textlength(ch, font=font) + tracking


# ------------------------------------------------------------ 纹理（固定 seed）

def make_textured_base(width: int, height: int, cfg: dict) -> Image.Image:
    """E 版等高线纹理（自 generate_texture_variants.py 转正，逐像素一致）。"""
    bg_hex = cfg["colors"]["background"]
    tex = cfg["texture"]
    ct = tex["contour"]
    rng = random.Random(f'{tex["seed"]}-{tex["seed_salt"]}-{width}x{height}')

    base = Image.new("RGBA", (width, height), hex_rgba(bg_hex))
    bg_rgb = hex_rgba(bg_hex)[:3]

    # 平滑标量场：低分辨率随机场放大 -> 提取等值线作为极淡拓扑线
    fw, fh = ct["field_size"]
    field = Image.frombytes("L", (fw, fh), rng.randbytes(fw * fh))
    field = field.resize((width // 2, height // 2), Image.BICUBIC)
    line_color = shift_lightness(bg_rgb, ct["line_lighten"]) + (255,)
    lv = ct["levels"]
    for level in range(lv["start"], lv["stop"], lv["step"]):
        band = ct["band"]
        mask = field.point(lambda v, L=level: 255 if abs(v - L) <= band else 0)
        mask = mask.resize((width, height), Image.BILINEAR)
        mask = mask.filter(ImageFilter.GaussianBlur(ct["mask_blur"]))
        line = Image.new("RGBA", (width, height), line_color)
        base = Image.alpha_composite(
            base, Image.composite(line, Image.new("RGBA", (width, height), (0, 0, 0, 0)),
                                  mask.point(lambda v: v * ct["line_alpha"] // 255)))

    # 收尾细颗粒：固定 seed 随机字节 -> L 图 -> 极低 alpha 叠加
    noise = Image.frombytes("L", (width, height), rng.randbytes(width * height))
    noise_rgba = Image.merge("RGBA", (noise, noise, noise,
                                      noise.point(lambda v: tex["paper_noise_alpha"])))
    return Image.alpha_composite(base, noise_rgba)


# ------------------------------------------------------------ Header

def render_header(cfg: dict, fonts: FontBook) -> Image.Image:
    w, h = cfg["canvas"]["width"], cfg["canvas"]["header_height"]
    img = make_textured_base(w, h, cfg)
    draw = ImageDraw.Draw(img, "RGBA")
    pen = TextPen(draw, fonts)
    hc = cfg["header"]

    t = hc["top_text"]
    pen.write(t["text"], t["x"], t["y"], role=t["font"], size=t["size"],
              tracking=t["tracking"], fill=hex_rgba(t["color"], t["alpha"]))

    r = hc["left_rule"]
    draw.rectangle((r["x"], r["y_top"], r["x"] + r["width"] - 1, r["y_bottom"]),
                   fill=hex_rgba(r["color"], r["alpha"]))

    # 右上签名水印（固定品牌资产，不重新生成）
    sig_cfg = hc["signature"]
    sig = Image.open(ROOT / sig_cfg["file"]).convert("RGBA")
    ratio = sig_cfg["width"] / sig.width
    sig = sig.resize((sig_cfg["width"], round(sig.height * ratio)), Image.LANCZOS)
    alpha = sig.getchannel("A").point(lambda v: round(v * sig_cfg["opacity"]))
    sig.putalpha(alpha)
    img.alpha_composite(sig, (w - sig_cfg["margin_right"] - sig.width,
                              sig_cfg["margin_top"]))
    draw = ImageDraw.Draw(img, "RGBA")

    rl = hc["right_list"]
    y = rl["y_top"]
    for line in rl["lines"]:
        pen.write(line, rl["x_right"], y, role=rl["font"], size=rl["size"],
                  tracking=rl["tracking"], fill=hex_rgba(rl["color"], rl["alpha"]),
                  align=rl["align"])
        y += rl["line_height"]
    d = rl["dash"]
    y += d["gap"]
    draw.rectangle((rl["x_right"] - d["width"], y, rl["x_right"], y + d["height"] - 1),
                   fill=hex_rgba(d["color"], d["alpha"]))

    bl = hc["bottom_left"]
    n = len(bl["lines"])
    y = h - bl["y_bottom"] - bl["line_height"] * n
    for line in bl["lines"]:
        pen.write(line, bl["x"], y, role=bl["font"], size=bl["size"],
                  tracking=bl["tracking"], fill=hex_rgba(bl["color"], bl["alpha"]))
        y += bl["line_height"]

    # Header/B-roll 交界分隔线（属于 header_base 资产底缘）
    br = hc["bottom_rule"]
    draw.rectangle((0, h - br["height"], w, h - 1),
                   fill=hex_rgba(br["color"], br["alpha"]))

    return img


# ------------------------------------------------------------ Footer

def render_footer(cfg: dict, fonts: FontBook) -> Image.Image:
    w, h = cfg["canvas"]["width"], cfg["canvas"]["footer_height"]
    img = make_textured_base(w, h, cfg)
    draw = ImageDraw.Draw(img, "RGBA")
    pen = TextPen(draw, fonts)
    fc = cfg["footer"]

    # B-roll/Footer 交界分隔线（属于 footer_base 资产顶缘）
    tr = fc["top_rule"]
    draw.rectangle((0, 0, w, tr["height"] - 1),
                   fill=hex_rgba(tr["color"], tr["alpha"]))

    # 左侧圆形 Logo（固定品牌资产，不重新生成）
    lg = fc["logo"]
    logo = Image.open(ROOT / lg["file"]).convert("RGBA")
    logo = logo.resize((lg["size"], lg["size"]), Image.LANCZOS)
    img.alpha_composite(logo, (lg["x"], lg["y"]))
    draw = ImageDraw.Draw(img, "RGBA")

    dv = fc["divider"]
    draw.rectangle((dv["x"], dv["y_top"], dv["x"] + dv["width"] - 1, dv["y_bottom"]),
                   fill=hex_rgba(dv["color"], dv["alpha"]))

    # 刊名 "Alark知新录"：英文衬线 + 中文宋体，同一基线
    bn = fc["brand_name"]
    fill = hex_rgba(bn["color"])
    en_font, en_stroke = fonts.get(bn["en"]["font"], bn["en"]["size"])
    baseline = bn["y"] + bn["en"]["size"]
    x = bn["x"]
    for ch in bn["en"]["text"]:
        draw.text((x, baseline), ch, font=en_font, fill=fill, anchor="ls",
                  stroke_width=en_stroke, stroke_fill=fill)
        x += draw.textlength(ch, font=en_font) + bn["en"]["tracking"]
    x += bn["en_cn_gap"]
    cn_font, cn_stroke = fonts.get(bn["cn"]["font"], bn["cn"]["size"])
    for ch in bn["cn"]["text"]:
        draw.text((x, baseline), ch, font=cn_font, fill=fill, anchor="ls",
                  stroke_width=cn_stroke, stroke_fill=fill)
        x += draw.textlength(ch, font=cn_font) + bn["cn"]["tracking"]

    s = fc["slogan"]
    pen.write(s["text"], s["x"], s["y"], role=s["font"], size=s["size"],
              tracking=s["tracking"], fill=hex_rgba(s["color"], s["alpha"]))

    rl = fc["right_list"]
    d = rl["dashes"]
    y = rl["y_top"]
    draw.rectangle((rl["x_right"] - d["width"], y, rl["x_right"], y + d["height"] - 1),
                   fill=hex_rgba(d["color"], d["alpha"]))
    y += d["height"] + d["gap"]
    for line in rl["lines"]:
        pen.write(line, rl["x_right"], y, role=rl["font"], size=rl["size"],
                  tracking=rl["tracking"], fill=hex_rgba(rl["color"], rl["alpha"]),
                  align=rl["align"])
        y += rl["line_height"]
    y += d["gap"]
    draw.rectangle((rl["x_right"] - d["width"], y, rl["x_right"], y + d["height"] - 1),
                   fill=hex_rgba(d["color"], d["alpha"]))

    bt = fc["bottom_text"]
    pen.write(bt["text"], w // 2, bt["y"], role=bt["font"], size=bt["size"],
              tracking=bt["tracking"], fill=hex_rgba(bt["color"], bt["alpha"]),
              align=bt["align"])

    return img


# ------------------------------------------------------------ 主流程

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "config" / "frame_v1.yaml"))
    args = ap.parse_args()

    with open(args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    fonts = FontBook(cfg["fonts"])
    cv = cfg["canvas"]

    header = render_header(cfg, fonts)
    footer = render_footer(cfg, fonts)

    # 预览图：Header + 黑色 B-roll 占位 + Footer（无标题/字幕/真实视频）
    broll_h = cv["broll_height"]
    preview = Image.new("RGBA", (cv["width"], cv["height"]),
                        hex_rgba(cfg["broll"]["placeholder_color"]))
    preview.paste(header, (0, 0))
    preview.paste(footer, (0, cv["header_height"] + broll_h))

    for key, img in (("header", header), ("footer", footer), ("preview", preview)):
        out = ROOT / cfg["output"][key]
        out.parent.mkdir(parents=True, exist_ok=True)
        img.convert("RGB").save(out)
        print(f"[ok] {out.relative_to(ROOT)}  {img.size[0]}x{img.size[1]}")

    print("[fonts] 实际命中：")
    for role, desc in fonts.used.items():
        print(f"  {role}: {desc}")


if __name__ == "__main__":
    sys.exit(main())
