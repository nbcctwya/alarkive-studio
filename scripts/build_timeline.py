# -*- coding: utf-8 -*-
"""Demo 001 第二阶段：按字幕时间轴 + 文案语义选择 B-roll，生成 timeline.yaml。

选片规则（用户指定）：
  - 开头前 20s 镜头约 3~5s；正文约 6~9s（语义排比段允许例外，见控制台 [note]）
  - 切换点尽量对齐字幕条目边界（允许跨 1-2 条字幕一个镜头）
  - 避免连续同类别镜头；允许同素材不同时间段复用（in/out 区间不得完全重叠）
  - 总时长覆盖配音全长（略长收尾）
  - 不复制、不修改任何原始 B-roll 文件

自检：覆盖无空洞无重叠 / in-out 不超素材时长 / 复用区间不重叠 / 类别不连续重复。

用法：python scripts/build_timeline.py --project projects/demo001
"""
import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LIB = "B-roll/Landscape video"

# (覆盖字幕条目范围, 素材相对路径, in, out, 选择理由, [可选] 显式起点)
# 起点默认取所覆盖首条字幕的开始时间；相邻镜头首尾相接，终点 = 下一镜头起点。
PLAN = [
    # ---- 开场（前 20s，3~5s 快切）----
    ("1",     "people/studying/coverr-student-studying-in-a-coffee-shop-7986-1080p.mp4",
     2.0, 5.9, "开场'努力教育'：咖啡馆里学习的学生"),
    ("2",     "people/working/coverr-timelapse-working-from-home-3951-1080p.mp4",
     5.0, 10.0, "'认真读书努力工作'：居家办公延时，忙碌感"),
    ("3",     "people/studying/coverr-student-turning-the-pages-of-a-marketing-book-2770-1080p.mp4",
     6.0, 8.7, "'错觉'：翻书特写，承接学习意象"),
    ("4",     "people/working/coverr-a-girl-working-at-her-desk-drinking-coffee-2548-1080p.mp4",
     3.0, 7.0, "'努力就会越来越好'：伏案工作的日常画面"),
    # ---- 正文 ----
    ("5",     "city/street/17696797-hd_1920_1080_30fps.mp4",
     10.0, 17.9, "'同样努力人生不同'：街头人流，人群对照感"),
    ("6",     "people/working/coverr-a-woman-working-on-her-computer-late-at-night-3699-1080p.mp4",
     2.0, 7.3, "'每天工作十几小时停在原地'：深夜加班"),
    ("7",     "people/thinking/coverr-contemplative-young-woman-in-park-1080p.mp4",
     2.0, 8.2, "'没那么忙却走得更远'：公园里若有所思"),
    ("8-9",   "city/street/coverr-a-man-walks-into-a-street-and-looks-around-confidently-492-1080p.mp4",
     3.0, 9.4, "'努力放在哪里'：走入街头环顾，方向感"),
    ("10-11", "people/walking/coverr-walking-in-central-park-4412-1080p.mp4",
     3.0, 12.0, "'走多快vs通向哪里'：公园行走，路的意象"),
    ("12",    "business/finance/coverr-new-york-stock-exchange-5368-1080p.mp4",
     4.0, 8.8, "'选择什么行业'：纽交所，行业象征"),
    ("13",    "people/working/coverr-a-team-prepares-for-a-business-meeting-169-1080p.mp4",
     2.0, 8.2, "'选择什么工作、接触的人'：团队会议准备"),
    ("14",    "people/studying/mixkit-a-young-man-studying-in-the-library-14734-hd-ready.mp4",
     4.0, 12.7, "'下班后刷视频还是学技能'：图书馆学习"),
    ("15-16", "people/working/coverr-workers-typing-and-closing-their-laptops-4953-1080p.mp4",
     2.0, 8.8, "'完成别人交给的任务'：敲键盘合电脑"),
    ("17",    "people/studying/coverr-studying-9024-1080p.mp4",
     8.0, 15.6, "'积累可带走的技能作品'：专注学习"),
    ("18-19", "people/thinking/coverr-flicking-through-a-notebook-outdoors-7787-1080p.mp4",
     3.0, 10.4, "'短期都忙/长期积累不同'：户外翻笔记本"),
    ("20-21", "people/walking/mixkit-girl-walks-bare-feet-in-golden-field-at-sunset-47673-hd-ready.mp4",
     4.0, 10.2, "'影响不会立刻出现'：夕阳田野行走，时间感"),
    ("22",    "city/street/coverr-a-street-on-a-rainy-day-3463-1080p.mp4",
     2.0, 6.7, "'选错方向不马上付出代价'：雨街，隐忧氛围"),
    ("23",    "city/subway/coverr-subway-timelapse-7958-1080p.mp4",
     2.0, 6.8, "'每天浪费一小时'：地铁延时，时间流逝"),
    ("24-25", "people/working/coverr-a-man-comes-into-his-office-3446-1080p.mp4",
     8.0, 17.2, "'留在没成长空间的环境/时间放大差异'：走进办公室"),
    ("26a",   "city/skyline/mixkit-tour-high-above-a-city-at-dusk-41375-hd-ready.mp4",
     3.0, 9.3, "'一三五年后差距显现'：黄昏城市高空，格局拉开"),
    ("26b",   "people/thinking/coverr-writing-a-poem-outdoors-3529-1080p.mp4",
     6.0, 12.3, "'结果早在过去被写下'：户外书写，'写下'具象化", 124.10),
    ("27-28", "people/working/mixkit-mechanic-repairing-a-car-engine-4716-hd-ready.mp4",
     1.0, 8.7, "'努力重要/没有执行只是想法'：修车，执行力意象"),
    ("29",    "people/studying/coverr-looking-through-a-music-book-1693-1080p.mp4",
     10.0, 18.8, "'先选择值得长期投入的事'：专注研读"),
    ("30",    "business/finance/mixkit-the-stock-market-trend-on-screen-9607-hd-ready.mp4",
     3.0, 6.4, "'方向正确形成复利'：行情上扬曲线"),
    ("31",    "city/subway/coverr-subway-departing-138-1080p.mp4",
     1.5, 7.0, "'方向错误越走越远'：列车驶离"),
    ("32",    "people/thinking/mixkit-closeup-of-young-woman-thinking-about-decision-15776-hd-ready.mp4",
     1.0, 5.8, "'更值得反复思考的问题'：抉择特写"),
    ("33",    "city/skyline/12118126_1920_1080_30fps.mp4",
     2.0, 6.4, "'三年后还有价值吗'：城市天际线，时间尺度"),
    ("34",    "people/walking/17422809-hd_2048_1080_30fps.mp4",
     10.0, 15.3, "'离开平台还能用吗'：行走移动，离开与迁移"),
    ("35",    "people/thinking/mixkit-face-of-a-young-pensive-woman-on-a-purple-background-33353-hd-ready.mp4",
     0.5, 7.9, "'消耗自己还是更多选择'：沉思面部特写"),
    ("36",    "city/street/coverr-stylish-woman-walking-down-the-street-1557-1080p.mp4",
     5.0, 11.2, "'重要选择不是惊天动地的决定'：日常街头"),
    ("37",    "people/studying/coverr-student-studying-in-a-coffee-shop-7986-1080p.mp4",
     9.0, 16.9, "'把时间交给什么、学习什么'：复用开场素材另一时段，首尾呼应"),
    ("38-39", "nature/sky/coverr-cloudy-sky-2765-1080p.mp4",
     4.0, 7.7, "'努力决定速度/选择决定方向'：云层天空，情绪扬升"),
    ("40",    "city/skyline/14840560_1920_1080_24fps.mp4",
     10.0, 17.2, "结尾'时间放大差距'：大气天际线收尾"),
]

AUDIO_TAIL = 0.32  # 结尾比配音略长一点收尾


def parse_srt(path: Path) -> list[dict]:
    entries = []
    for block in path.read_text(encoding="utf-8").strip().split("\n\n"):
        lines = block.split("\n")
        st, en = lines[1].split(" --> ")
        def ms(ts):
            h, m, rest = ts.split(":")
            s, msec = rest.split(",")
            return (int(h) * 3600 + int(m) * 60 + int(s)) * 1000 + int(msec)
        entries.append({"id": int(lines[0]), "start": ms(st) / 1000,
                        "end": ms(en) / 1000, "text": lines[2]})
    return entries


def entry_range(spec: str) -> list[int]:
    """'8-9' -> [8,9]；'26a' -> [26]；'26' -> [26]。"""
    spec = spec.rstrip("ab")
    if "-" in spec:
        a, b = spec.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(spec)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=str(ROOT / "projects" / "demo001"))
    args = ap.parse_args()
    project = Path(args.project)

    with open(project / "meta.yaml", encoding="utf-8") as f:
        meta = yaml.safe_load(f)
    audio_dur = float(meta["voice"]["duration_sec"])
    srt = {e["id"]: e for e in parse_srt(project / meta["subtitle"]["file"])}
    lib = json.loads((project / "selected_broll" / "library_index.json")
                     .read_text(encoding="utf-8"))

    # 展开 shot list：起点 = 首条覆盖字幕的开始（或显式覆盖），终点 = 下一镜头起点
    shots = []
    for i, item in enumerate(PLAN):
        spec, rel, tin, tout, reason = item[:5]
        explicit_start = item[5] if len(item) > 5 else None
        ids = entry_range(spec)
        start = explicit_start if explicit_start is not None else (
            0.0 if i == 0 else srt[ids[0]]["start"])
        shots.append({"ids": ids, "material": rel, "in": tin, "out": tout,
                      "reason": reason, "start": round(start, 2)})
    for i, sh in enumerate(shots):
        end = shots[i + 1]["start"] if i + 1 < len(shots) \
            else round(audio_dur + AUDIO_TAIL, 2)
        sh["end"] = end
        sh["duration"] = round(end - sh["start"], 2)
        sh["out"] = round(sh["in"] + sh["duration"], 2)  # 素材出点对齐镜头时长

    # ---------------- 自检 ----------------
    errors, notes = [], []
    for i, sh in enumerate(shots):
        if i and abs(sh["start"] - shots[i - 1]["end"]) > 0.01:
            errors.append(f"镜头{i + 1} 与前一镜头有空洞/重叠")
        mat = lib.get(sh["material"])
        if mat is None:
            errors.append(f"镜头{i + 1} 素材不在索引: {sh['material']}")
        elif sh["out"] > mat["duration"] + 0.01:
            errors.append(f"镜头{i + 1} out={sh['out']} 超出素材时长 {mat['duration']}")
        if sh["start"] < 20 and not (2.5 <= sh["duration"] <= 5.2):
            notes.append(f"镜头{i + 1} 开场段时长 {sh['duration']}s 偏离 3~5s")
        elif sh["start"] >= 20 and not (5.0 <= sh["duration"] <= 9.5):
            notes.append(f"镜头{i + 1} 正文段时长 {sh['duration']}s 偏离 6~9s（语义排比段例外）")
        if i and shots[i - 1]["material"].rsplit("/", 2)[-2] == \
                  sh["material"].rsplit("/", 2)[-2]:
            errors.append(f"镜头{i} 与 {i + 1} 连续同类别")
    seen = {}
    for i, sh in enumerate(shots):
        if sh["material"] in seen:
            j, (pi, po) = seen[sh["material"]]
            if not (sh["out"] <= pi or sh["in"] >= po):
                errors.append(f"镜头{i + 1} 与镜头{j + 1} 复用素材区间重叠")
        seen.setdefault(sh["material"], (i, (sh["in"], sh["out"])))
    if shots[-1]["end"] < audio_dur:
        errors.append("镜头总时长未覆盖配音全长")

    # ---------------- 输出 ----------------
    timeline = {"project": "demo001", "audio_duration": audio_dur,
                "total_shots": len(shots),
                "coverage": [shots[0]["start"], shots[-1]["end"]],
                "shots": []}
    for i, sh in enumerate(shots, 1):
        timeline["shots"].append({
            "seq": i, "start": sh["start"], "end": sh["end"],
            "duration": sh["duration"],
            "material": f"{LIB}/{sh['material']}",
            "in": sh["in"], "out": sh["out"],
            "category": sh["material"].rsplit("/", 2)[-2],
            "srt_entries": sh["ids"],
            "srt_text": " / ".join(srt[j]["text"] for j in sh["ids"]),
            "reason": sh["reason"],
        })
    out = project / "timeline.yaml"
    out.write_text(yaml.safe_dump(timeline, allow_unicode=True, sort_keys=False),
                   encoding="utf-8")

    print(f"{'#':>2} | {'时间段':>17} | {'时长':>5} | {'类别':>18} | "
          f"{'素材':<52} | 对应字幕")
    for i, sh in enumerate(shots, 1):
        cat = sh["material"].rsplit("/", 2)[-2]
        name = Path(sh["material"]).name[:52]
        ids = sh["ids"]
        rng = f"{ids[0]}" if len(ids) == 1 else f"{ids[0]}-{ids[-1]}"
        print(f"{i:>2} | {sh['start']:7.2f}-{sh['end']:7.2f} | "
              f"{sh['duration']:4.2f}s | {cat:>18} | {name:<52} | 条目{rng}")

    cats = {}
    for sh in shots:
        cats.setdefault(sh["material"].rsplit("/", 2)[-2], 0)
        cats[sh["material"].rsplit("/", 2)[-2]] += 1
    print(f"\n[ok] {out}")
    print(f"[info] 镜头总数={len(shots)}  覆盖 0~{shots[-1]['end']}s "
          f"(配音 {audio_dur}s)")
    print(f"[info] 类别分布: " + ", ".join(f"{k}x{v}" for k, v in sorted(cats.items())))
    for n in notes:
        print(f"[note] {n}")
    if errors:
        for e in errors:
            print(f"[ERROR] {e}")
        sys.exit(1)
    print("[check] 覆盖连续 / in-out 合法 / 复用不重叠 / 无连续同类别：全部通过")


if __name__ == "__main__":
    sys.exit(main())
