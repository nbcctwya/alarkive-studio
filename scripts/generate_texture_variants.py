# -*- coding: utf-8 -*-
"""Alark Frame v1.0 背景纹理探索：一次生成 A–H 共 8 个版本的 preview 供横向比较。

冻结约束：布局/文案/字体/Logo/签名/配色/分隔线一律不变。
实现方式：import 主脚本 generate_frame，仅 monkeypatch 其背景纹理函数
`make_textured_base`，Header/Footer 上所有固定元素走原渲染路径，一个像素不变。
纹理只作用于 Header/Footer 背景，中间 1080x608 黑色占位区保持纯黑。

输出：
  preview/frame_v1_A.png … preview/frame_v1_H.png   (1080x1328)
  preview/frame_v1_comparison.png                    (2 行 x 4 列对照图)

运行：python scripts/generate_texture_variants.py
"""
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

# 注意：E 版已转正为正式纹理（见 config/frame_v1.yaml 的 texture.contour，
# 由 scripts/generate_frame.py 生成正式资产）。本脚本保留用于复现 A–H 对照实验。

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import generate_frame as gf  # noqa: E402

BG = (0x0D, 0x3A, 0x2A)
SEED_SALT = "texture-variants-v1"


# ------------------------------------------------------------ 纹理工具

def _rng(tag: str, w: int, h: int, cfg: dict) -> random.Random:
    return random.Random(f'{cfg["texture"]["seed"]}-{SEED_SALT}-{tag}-{w}x{h}')


def _base(w: int, h: int) -> Image.Image:
    return Image.new("RGBA", (w, h), BG + (255,))


def _shift(delta: int) -> tuple:
    return tuple(max(0, min(255, c + delta)) for c in BG)


def _grain(img: Image.Image, rng: random.Random, alpha: int) -> Image.Image:
    """细颗粒：固定 seed 随机字节噪点，极低 alpha 叠加。"""
    w, h = img.size
    noise = Image.frombytes("L", (w, h), rng.randbytes(w * h))
    layer = Image.merge("RGBA", (noise, noise, noise,
                                 noise.point(lambda v: alpha)))
    return Image.alpha_composite(img, layer)


def _mottle(img: Image.Image, rng: random.Random, alpha: int, cells: int = 8) -> Image.Image:
    """大块柔和明暗斑驳：低分辨率噪点放大，模拟棉纸/光影的缓慢起伏。"""
    w, h = img.size
    sw, sh = max(2, w // (w // cells * cells) * cells // cells), None  # placeholder
    sw, sh = cells * 4, max(2, round(cells * 4 * h / w))
    small = Image.frombytes("L", (sw, sh), rng.randbytes(sw * sh))
    soft = small.resize((w, h), Image.BICUBIC)
    layer = Image.merge("RGBA", (soft, soft, soft,
                                 soft.point(lambda v: alpha)))
    return Image.alpha_composite(img, layer)


def _blobs(img: Image.Image, rng: random.Random, n: int, delta: int,
           blur_ratio: float) -> Image.Image:
    """不规则柔和墨团：随机椭圆 + 大半径高斯模糊，不形成具体形状。"""
    w, h = img.size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(n):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        rx, ry = rng.uniform(w * 0.18, w * 0.45), rng.uniform(h * 0.25, h * 0.7)
        delta_i = rng.choice([-1, 1]) * rng.uniform(delta * 0.5, delta)
        d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry),
                  fill=_shift(round(delta_i)) + (255,))
    layer = layer.filter(ImageFilter.GaussianBlur(max(w, h) * blur_ratio))
    return Image.alpha_composite(img, layer)


# ------------------------------------------------------------ A–H 纹理定义

def tex_A(w, h, cfg):  # 纯纸张颗粒：细颗粒 + 极轻大块斑驳（棉纸感）
    rng = _rng("A", w, h, cfg)
    img = _mottle(_base(w, h), rng, alpha=4, cells=8)
    return _grain(img, rng, alpha=7)


def tex_B(w, h, cfg):  # 墨雾：深绿里极淡的柔和墨团
    rng = _rng("B", w, h, cfg)
    img = _blobs(_base(w, h), rng, n=9, delta=8, blur_ratio=0.10)
    return _grain(img, rng, alpha=3)


def tex_C(w, h, cfg):  # 纸张 + 墨雾
    rng = _rng("C", w, h, cfg)
    img = _mottle(_base(w, h), rng, alpha=4, cells=8)
    img = _blobs(img, rng, n=7, delta=7, blur_ratio=0.11)
    return _grain(img, rng, alpha=6)


def tex_D(w, h, cfg):  # 抽象光影：上方柔光 + 底角暗部，棚拍背景感
    rng = _rng("D", w, h, cfg)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse((-w * 0.25, -h * 0.9, w * 0.85, h * 0.55), fill=_shift(9) + (255,))
    d.ellipse((w * 0.45, h * 0.75, w * 1.45, h * 1.9), fill=_shift(-8) + (255,))
    d.ellipse((-w * 0.5, h * 0.7, w * 0.35, h * 1.8), fill=_shift(-7) + (255,))
    layer = layer.filter(ImageFilter.GaussianBlur(max(w, h) * 0.14))
    return _grain(Image.alpha_composite(_base(w, h), layer), rng, alpha=3)


def tex_E(w, h, cfg):  # 等高线：平滑标量场的极淡拓扑线
    rng = _rng("E", w, h, cfg)
    field = Image.frombytes("L", (36, 14), rng.randbytes(36 * 14))
    field = field.resize((w // 2, h // 2), Image.BICUBIC)
    img = _base(w, h)
    for level in range(42, 220, 22):
        mask = field.point(lambda v, L=level: 255 if abs(v - L) <= 1 else 0)
        mask = mask.resize((w, h), Image.BILINEAR).filter(ImageFilter.GaussianBlur(1))
        line = Image.new("RGBA", (w, h), _shift(26) + (255,))
        img = Image.alpha_composite(
            img, Image.composite(line, Image.new("RGBA", (w, h), (0, 0, 0, 0)),
                                 mask.point(lambda v: v * 70 // 255)))
    return _grain(img, rng, alpha=3)


def tex_F(w, h, cfg):  # 细腻布纹：横竖细织纹 + 颗粒，极低 alpha
    rng = _rng("F", w, h, cfg)
    img = _base(w, h)
    for axis, gap, delta, alpha in ((0, 3, 6, 90), (1, 3, 6, 75)):
        mask = Image.new("L", (w, h), 0)
        md = ImageDraw.Draw(mask)
        if axis == 0:
            for y in range(0, h, gap):
                md.line((0, y, w, y), fill=alpha)
        else:
            for x in range(0, w, gap):
                md.line((x, 0, x, h), fill=alpha)
        img = Image.alpha_composite(
            img, Image.composite(Image.new("RGBA", (w, h), _shift(delta) + (255,)),
                                 Image.new("RGBA", (w, h), (0, 0, 0, 0)), mask))
    return _grain(img, rng, alpha=4)


def tex_G(w, h, cfg):  # 胶片颗粒 + 四周微弱暗角（仅作用于本区域，不影响黑色占位区）
    rng = _rng("G", w, h, cfg)
    img = _grain(_base(w, h), rng, alpha=6)
    sw, sh = 64, max(2, round(64 * h / w))
    vig = Image.new("L", (sw, sh), 0)
    px = vig.load()
    for yy in range(sh):
        for xx in range(sw):
            nx, ny = (xx / sw - 0.5) * 2, (yy / sh - 0.5) * 2
            d = (nx * nx + ny * ny) ** 0.5
            px[xx, yy] = round(26 * min(1, max(0, (d - 0.55) / 0.75)))
    vig = vig.resize((w, h), Image.BICUBIC)
    dark = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    return Image.alpha_composite(
        img, Image.composite(dark, Image.new("RGBA", (w, h), (0, 0, 0, 0)), vig))


def tex_H(w, h, cfg):  # 几乎纯色：极轻垂直明暗渐变 + 微颗粒
    rng = _rng("H", w, h, cfg)
    grad = Image.linear_gradient("L").resize((w, h))  # 顶部 0 -> 底部 255
    layer = Image.composite(Image.new("RGBA", (w, h), _shift(-3) + (255,)),
                            Image.new("RGBA", (w, h), _shift(3) + (255,)), grad)
    return _grain(Image.alpha_composite(_base(w, h), layer), rng, alpha=4)


VARIANTS = {"A": tex_A, "B": tex_B, "C": tex_C, "D": tex_D,
            "E": tex_E, "F": tex_F, "G": tex_G, "H": tex_H}

CREAM_TEXT_MIN = (190, 175, 145)  # 文字/Logo 掩码阈值（暖米白系）


def text_mask(img: Image.Image) -> set:
    """提取暖米白文字/Logo 像素集合，用于跨版本一致性 diff。"""
    rgb = img.convert("RGB")
    data = rgb.load()
    w, h = rgb.size
    out = set()
    for y in range(h):
        for x in range(w):
            r, g, b = data[x, y]
            if r > CREAM_TEXT_MIN[0] and g > CREAM_TEXT_MIN[1] and b > CREAM_TEXT_MIN[2]:
                out.add((x, y))
    return out


def main() -> None:
    import yaml
    with open(ROOT / "config" / "frame_v1.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    fonts = gf.FontBook(cfg["fonts"])
    cv = cfg["canvas"]
    broll_h = cv["broll_height"]

    previews: dict[str, Image.Image] = {}
    header_masks: dict[str, set] = {}
    footer_masks: dict[str, set] = {}

    for tag, fn in VARIANTS.items():
        gf.make_textured_base = fn  # 只替换背景纹理，冻结元素走原渲染路径
        header = gf.render_header(cfg, fonts)
        footer = gf.render_footer(cfg, fonts)
        preview = Image.new("RGBA", (cv["width"], cv["height"]),
                            gf.hex_rgba(cfg["broll"]["placeholder_color"]))
        preview.paste(header, (0, 0))
        preview.paste(footer, (0, cv["header_height"] + broll_h))
        out = ROOT / "preview" / f"frame_v1_{tag}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        preview.convert("RGB").save(out)
        previews[tag] = preview.convert("RGB")
        header_masks[tag] = text_mask(header)
        footer_masks[tag] = text_mask(footer)
        print(f"[ok] {out.relative_to(ROOT)}")

    # 一致性校验：以 A 版为基准 diff 文字/Logo 像素掩码
    # （纹理本身是深绿低亮度，不会触发暖米白掩码；差异应只来自文字边缘
    #   抗锯齿像素与不同底色的混合，数量极小）
    print("[diff] 文字/Logo 掩码与 A 版的差异像素数（抗锯齿边缘属预期）：")
    for tag in VARIANTS:
        hd = len(header_masks["A"] ^ header_masks[tag])
        fd = len(footer_masks["A"] ^ footer_masks[tag])
        print(f"  {tag}: header={hd}  footer={fd}")

    # 对照图：2 行 x 4 列，每格 540x664 + 44px 字母标注条带
    cell_w, cell_h, band = 540, 664, 44
    comp = Image.new("RGB", (cell_w * 4, (cell_h + band) * 2), (5, 5, 5))
    cd = ImageDraw.Draw(comp)
    label_font, _ = fonts.get("serif_en_bold", 28)
    for i, tag in enumerate(VARIANTS):
        col, row = i % 4, i // 4
        x0, y0 = col * cell_w, row * (cell_h + band)
        cell = previews[tag].resize((cell_w, cell_h), Image.LANCZOS)
        comp.paste(cell, (x0, y0 + band))
        cd.rectangle((x0, y0, x0 + cell_w - 1, y0 + band - 1), fill=(18, 32, 26))
        cd.text((x0 + cell_w // 2, y0 + band // 2), tag, font=label_font,
                fill=(243, 232, 210), anchor="mm")
    comp_out = ROOT / "preview" / "frame_v1_comparison.png"
    comp.save(comp_out)
    print(f"[ok] {comp_out.relative_to(ROOT)}  {comp.size[0]}x{comp.size[1]}")


if __name__ == "__main__":
    sys.exit(main())
