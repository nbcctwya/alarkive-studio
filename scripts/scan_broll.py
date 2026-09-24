# -*- coding: utf-8 -*-
"""扫描 B-roll 素材库，生成素材索引（时长/fps/分辨率），结果缓存为 JSON。

索引为全库共享（项目无关），默认输出 assets/broll_index.json：
  python scripts/scan_broll.py                       # 增量扫描到默认共享位置
  python scripts/scan_broll.py --output <其他路径>   # 自定义输出

已存在的索引条目直接复用（增量扫描，新素材才探测）。
"""
import argparse
import json
import sys
from pathlib import Path

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent.parent
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
DEFAULT_INDEX = ROOT / "assets" / "broll_index.json"


def probe(path: Path) -> dict | None:
    try:
        gen = imageio_ffmpeg.read_frames(str(path), pix_fmt="rgb24")
        meta = next(gen)
        gen.close()
        return {"duration": round(float(meta["duration"]), 2),
                "fps": float(meta["fps"]),
                "width": int(meta["size"][0]),
                "height": int(meta["size"][1])}
    except Exception as e:
        print(f"[warn] 探测失败 {path}: {e}", file=sys.stderr)
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--library", default=str(ROOT / "B-roll" / "Landscape video"))
    ap.add_argument("--output", default=str(DEFAULT_INDEX))
    args = ap.parse_args()

    lib = Path(args.library)
    out = Path(args.output)
    index = {}
    if out.exists():
        index = json.loads(out.read_text(encoding="utf-8"))

    files = sorted(p for p in lib.rglob("*") if p.suffix.lower() in VIDEO_EXT)
    new, cached = 0, 0
    for p in files:
        rel = p.relative_to(lib).as_posix()
        if rel in index:
            cached += 1
            continue
        info = probe(p)
        if info:
            info["category"] = str(Path(rel).parent).replace("\\", "/")
            info["filename"] = p.name
            index[rel] = info
            new += 1
            print(f"[scan] {rel}  {info['duration']}s  {info['width']}x{info['height']}")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(index, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(f"[ok] {out}  共 {len(index)} 条（新增 {new}，缓存命中 {cached}）")


if __name__ == "__main__":
    sys.exit(main())
