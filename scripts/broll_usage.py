# -*- coding: utf-8 -*-
"""统计各期 timeline.yaml 的素材使用记录，供选片时执行「冷素材优先 / 强制轮换」。

用法：
  python scripts/broll_usage.py            # 概览：各类别覆盖率 + 热门素材
  python scripts/broll_usage.py --cold Art/Sculpture   # 列出某类别下的冷门（未用）素材

选片约定（见 README「中间环节：语义选片」）：
- 冷素材优先：同等语义下优先近期未使用的素材；
- 强制轮换：近两期已用过的素材，除非语义无可替代，否则换同类别其他素材；
  复用时必须取与历史不相交的 in/out 区段；
- 负载均衡：每期约 10–15% 的镜头（60 个镜头的片子即 6–9 个）走非语义通道，
  从冷门类别按画面氛围/节奏挑选，放在过渡句、排比句等语义宽容的位置。
"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "assets" / "broll_index.json"


def collect_usage():
    """返回 {素材 rel 路径: [使用它的项目 id, ...]}（键统一为索引的大小写）。"""
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    lower2key = {k.lower(): k for k in index}
    usage = defaultdict(list)
    for p in sorted((ROOT / "projects").glob("*/timeline.yaml")):
        pid = p.parent.name
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        for s in (data or {}).get("shots", []):
            rel = s["material"].split("Landscape video/")[-1]
            key = lower2key.get(rel.lower())
            if key is None:
                print(f"[warn] {pid} 引用了索引外素材: {rel}")
                continue
            if pid not in usage[key]:
                usage[key].append(pid)
    return index, usage


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cold", metavar="类别", default=None,
                    help="列出该类别下从未使用的素材（如 Art/Sculpture）")
    ap.add_argument("--top", type=int, default=15, help="热门素材显示条数")
    args = ap.parse_args()

    index, usage = collect_usage()
    used = set(usage)

    if args.cold:
        cold = [k for k, v in index.items()
                if v["category"] == args.cold and k not in used]
        print(f"{args.cold} 未使用素材 {len(cold)} 条：")
        for k in sorted(cold):
            v = index[k]
            print(f"  {v['duration']:6.1f}s  {v['width']}x{v['height']}  {k}")
        return

    projects = sorted({pid for ids in usage.values() for pid in ids})
    print(f"已统计 {len(projects)} 期（{', '.join(projects)}）")
    print(f"索引 {len(index)} 条，已使用 {len(used)} 条"
          f"（{len(used) / len(index):.0%}），未使用 {len(index) - len(used)} 条\n")

    cat_total = Counter(v["category"] for v in index.values())
    cat_used = Counter(index[k]["category"] for k in used)
    print("各类别覆盖率（已用/总数）：")
    for c in sorted(cat_total):
        u, t = cat_used[c], cat_total[c]
        print(f"  {u:2d}/{t:2d}  {u / t:4.0%}  {c}")

    print(f"\n热门素材（被 {len(projects)} 期中的多期使用，前 {args.top} 条）：")
    hot = sorted(usage.items(), key=lambda kv: -len(kv[1]))
    for k, ids in hot[: args.top]:
        if len(ids) < 2:
            break
        print(f"  {len(ids)}期  {k}  <- {', '.join(ids)}")


if __name__ == "__main__":
    main()
