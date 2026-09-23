# -*- coding: utf-8 -*-
"""一次性品牌资产准备脚本（Alark Frame v1.0）。

生成 assets/brand/ 下的规范文件名资产：
  - logo_circle.png                由 Logo2.jpg 圆形裁剪 + 圆外透明化生成
  - alark_signature_chalk_white.png 由 Alark_signature_chalkwhite.png 复制生成

运行一次即可：python scripts/prepare_brand_assets.py
之后所有模板生成只读取规范文件名，不再依赖原始文件。
"""
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parent.parent
BRAND_DIR = ROOT / "assets" / "brand"

LOGO_SRC = BRAND_DIR / "Logo2.jpg"
LOGO_DST = BRAND_DIR / "logo_circle.png"
SIG_SRC = BRAND_DIR / "Alark_signature_chalkwhite.png"
SIG_DST = BRAND_DIR / "alark_signature_chalk_white.png"

# 圆形裁剪抗锯齿倍数（先大尺寸画蒙版再缩小）
MASK_SUPERSAMPLE = 4
# 检测到圆环外接圆后向内收的像素（去掉外缘 JPEG 黑色残边）
EDGE_INSET_PX = 3
# 判定“非黑角”的亮度阈值
NONBLACK_THRESHOLD = 24


def detect_circle_bbox(img: Image.Image) -> tuple[int, int, int, int]:
    """扫描非黑色像素的包围盒，作为圆环外缘边界。"""
    gray = ImageOps.grayscale(img)
    mask = gray.point(lambda v: 255 if v > NONBLACK_THRESHOLD else 0)
    bbox = mask.getbbox()
    if bbox is None:
        raise RuntimeError("未能在 Logo2.jpg 中检测到圆形 Logo 区域")
    return bbox


def make_logo_circle() -> None:
    img = Image.open(LOGO_SRC).convert("RGB")
    left, top, right, bottom = detect_circle_bbox(img)
    # 取包围盒中心与较短边，保证裁剪是正圆
    cx, cy = (left + right) / 2, (top + bottom) / 2
    radius = min(right - left, bottom - top) / 2 - EDGE_INSET_PX
    side = int(round(radius * 2))
    box = (
        int(round(cx - radius)),
        int(round(cy - radius)),
        int(round(cx - radius)) + side,
        int(round(cy - radius)) + side,
    )
    square = img.crop(box)

    # 超采样圆形蒙版 -> 抗锯齿透明边缘
    big = side * MASK_SUPERSAMPLE
    mask = Image.new("L", (big, big), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse((0, 0, big - 1, big - 1), fill=255)
    mask = mask.resize((side, side), Image.LANCZOS)

    out = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    out.paste(square.convert("RGBA"), (0, 0), mask)
    out.save(LOGO_DST)
    print(f"[ok] {LOGO_DST.relative_to(ROOT)}  {side}x{side}  裁剪盒={box}")


def make_signature() -> None:
    img = Image.open(SIG_SRC).convert("RGBA")
    img.save(SIG_DST)
    print(f"[ok] {SIG_DST.relative_to(ROOT)}  {img.size[0]}x{img.size[1]}  来源={SIG_SRC.name}")


if __name__ == "__main__":
    make_logo_circle()
    make_signature()
