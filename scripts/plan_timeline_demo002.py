# -*- coding: utf-8 -*-
"""demo002 一次性选片：按语义计划生成 projects/demo002/timeline.yaml 并自检。

起点取 SRT 条目边界，终点 = 下一镜头起点；out = in + 镜头时长。
跑完即弃的脚手架，但保留备查（与 build_timeline.py 之于 demo001 同地位）。
"""
import json
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_timeline import parse_srt  # noqa: E402

LIB = "B-roll/Landscape video"
PLAN = [
    # 开场 0-20s 快切：解别人出的题
    ("1",     "City/Street/17696797-hd_1920_1080_30fps.mp4", 20.0, "'很多人一辈子'：街头人流，人群即众生"),
    ("2",     "People/Studying/mixkit-a-young-man-studying-in-the-library-14734-hd-ready.mp4", 3.0, "'上学老师出题'：图书馆答题"),
    ("3",     "City/Subway/14746572_1920_1080_24fps.mp4", 2.0, "'工作以后'：通勤地铁"),
    ("4",     "People/Working/coverr-a-team-prepares-for-a-business-meeting-169-1080p.mp4", 2.0, "'前辈告诉你这行怎么做'：团队会议（单句7s镜头偏长）"),
    # 擅长解题却忘了问
    ("5-6",   "Technology/Computer/15029080_1920_1080_25fps.mp4", 8.0, "'越来越擅长解决问题'：屏幕与代码"),
    ("7-9",   "People/Thinking/mixkit-closeup-of-young-woman-thinking-about-decision-15776-hd-ready.mp4", 1.0, "'这道题值得我解吗'：抉择特写"),
    # 咖啡店思想实验
    ("10-11", "Things/Coffee/12926088_1920_1080_30fps.mp4", 5.0, "'开一家咖啡店'：咖啡意象入场"),
    ("12-13", "City/Street/coverr-west-broadway-street-6804-1080p.mp4", 3.0, "'找铺面/装修'：街面店铺"),
    ("14-15", "Things/Coffee/14019843_1920_1080_60fps.mp4", 4.0, "'买咖啡机/进原料'：咖啡机特写"),
    ("16-17", "People/Drinking/6953393-hd_2048_1080_25fps.mp4", 10.0, "'做出来卖给顾客赚差价'：咖啡馆出品"),
    ("18-19", "People/Thinking/coverr-flicking-through-a-notebook-outdoors-7787-1080p.mp4", 3.0, "'听起来没问题/有意思的地方藏在这里'：翻笔记起疑"),
    ("20-21", "Things/Coffee/6758573-hd_1920_1080_24fps.mp4", 1.0, "'没思考就接受了答案'：咖啡特写伏笔"),
    # 谁说的（质疑排比，快节奏）
    ("22-23", "People/Thinking/6930825-hd_1920_1080_25fps.mp4", 5.0, "'谁说要租店/卖现磨'：质疑沉思"),
    ("24",    "People/Drinking/mixkit-woman-drinking-coffee-in-a-cafe-223-hd-ready.mp4", 2.0, "'顾客真正想要的是咖啡吗'：喝咖啡的人"),
    ("25",    "Business/Finance/coverr-calculating-expenses-on-smartphone-1080p.mp4", 4.0, "'谁规定靠差价赚钱'：算账"),
    # 顾客真正需要什么
    ("26",    "People/Drinking/coverr-woman-drinking-coffee-at-work-4127-1080p.mp4", 4.0, "'昏昏沉沉的人要的是清醒'：工作间隙喝咖啡"),
    ("27",    "People/Working/coverr-a-blonde-man-works-on-a-laptop-in-his-home-office-5380-1080p.mp4", 8.0, "'抱电脑坐一下午要的是空间'：长句单镜头(9.2s)"),
    ("28",    "People/Dating/mixkit-lady-cuddling-up-to-her-boyfriend-while-enjoying-coffee-in-45855-hd-ready.mp4", 3.0, "'两个朋友要的是聊天空间'：咖啡馆陪伴"),
    ("29",    "People/Drinking/coverr-pouring-wine-421-1080p.mp4", 4.0, "'仪式感与体面'：倒饮品特写"),
    # 事情完全变了
    ("30-31", "People/Thinking/6913273-hd_1920_1080_25fps.mp4", 5.0, "'咖啡不是唯一答案'：转换思路"),
    ("32",    "Technology/Computer/3147349-hd_1920_1080_25fps.mp4", 5.0, "'需要的是工作空间'：桌面电脑"),
    ("33",    "People/Drinking/6953393-hd_2048_1080_25fps.mp4", 20.0, "'为环境社交体验付钱'：咖啡馆社交（复用另一时段）"),
    # 理所当然只是重复太久
    ("34-35", "People/Thinking/coverr-contemplative-young-woman-in-park-1080p.mp4", 2.0, "'没那么理所当然'：公园沉思"),
    ("36",    "Abstract/Time/coverr-rush-hour-traffic-5496-1080p.mp4", 4.0, "'重复太久像规则'：车流人流重复"),
    ("37",    "City/Street/14393784_1920_1080_24fps.mp4", 8.0, "'不只做生意这样'：街头日常"),
    ("38-39", "People/Walking/17422809-hd_2048_1080_30fps.mp4", 5.0, "'对人生也这样/毕业找好工作'：人生路"),
    # 工作排比
    ("40",    "People/Working/coverr-timelapse-working-from-home-3951-1080p.mp4", 15.0, "'研究公司岗位升职跳槽'：工作延时（复用demo001素材另一时段）"),
    ("41-42", "People/Thinking/mixkit-face-of-a-young-pensive-woman-on-a-purple-background-33353-hd-ready.mp4", 0.5, "'我真正想从工作里得到什么'：面部沉思"),
    ("43-47", "Business/Finance/coverr-falling-coins-6164-1080p.mp4", 4.0, "'收入/成长/自由/身份/安全感'排比：硬币落下"),
    ("48",    "City/Street/13527249_1920_1080_25fps.mp4", 3.0, "'所有人都在找所以我也走'：街头人流从众"),
    # 买房
    ("49-50", "City/Skyline/13459978_1920_1080_24fps.mp4", 10.0, "'买房/首付利率地段学区'：楼宇森林"),
    ("51-52", "People/Thinking/6931297-hd_1920_1080_25fps.mp4", 4.0, "'真正想要的是一套房子吗'：自问"),
    ("53-55", "Business/Finance/coverr-a-man-counting-the-profit-from-an-investment-3954-1080p.mp4", 8.0, "'居住权/安全感/上岸证明'排比：清点资产"),
    # 自媒体
    ("56",    "Technology/Computer/6963744-hd_1920_1080_25fps.mp4", 2.0, "'做自媒体就应该追热点'：屏幕信息流"),
    ("57",    "People/Working/coverr-a-woman-working-on-her-computer-late-at-night-3699-1080p.mp4", 4.0, "'研究流量标题点击率'：深夜做内容"),
    ("58-59", "People/Thinking/coverr-friends-looking-on-an-iphone-7587-1080p.mp4", 6.0, "'观众为什么给你注意力'：看手机的人"),
    ("60-61", "Technology/Computer/6754824-hd_1920_1080_25fps.mp4", 8.0, "'问题变了答案全变'：屏幕工作"),
    # 困境：赛道拼命跑
    ("62-64", "Business/Finance/coverr-a-trader-looking-upset-because-of-a-failure-in-his-analyses-6797-1080p.mp4", 4.0, "'困境/恰恰因为太努力'：沮丧的交易员"),
    ("65",    "People/Working/coverr-colleagues-working-in-the-office-while-drinking-coffee-9268-1080p.mp4", 1.0, "'在规定范围里找最优解'：办公室忙碌"),
    ("66",    "Abstract/Time/coverr-blurry-rush-hour-4540-1080p.mp4", 5.0, "'给你赛道拼命跑'：模糊奔忙人流"),
    ("67",    "City/Subway/coverr-entry-barrier-in-a-subway-station-2104-1080p.mp4", 2.0, "'给你规则研究怎么赢'：闸机规则意象"),
    ("68",    "People/Working/coverr-close-up-of-a-man-talking-on-a-virtual-meeting-4792-1080p.mp4", 6.0, "'给你问题想尽办法找答案'：线上会议"),
    ("69-71", "People/Walking/coverr-walking-in-central-park-4412-1080p.mp4", 8.0, "'跑得很快却从没抬头看路通向哪里'：埋头走路"),
    # 对问题保持警惕
    ("72",    "People/Thinking/7710872-hd_2048_1080_25fps.mp4", 4.0, "'值得训练的不只是解题'：思考"),
    ("73-75", "Things/Coffee/12926088_1920_1080_30fps.mp4", 15.0, "'下次准备问应该怎么做时'：咖啡停顿（复用另一时段）"),
    ("76-77", "People/Thinking/coverr-flicking-through-a-notebook-outdoors-7787-1080p.mp4", 9.2, "'把理所当然一件件拿掉'：翻笔记剔除（复用另一时段）"),
    ("78-80", "People/Walking/mixkit-girl-walks-bare-feet-in-golden-field-at-sunset-47673-hd-ready.mp4", 5.0, "'没人告诉我该怎么做/我真正想要什么'：旷野独行"),
    ("81-82", "Abstract/Time/coverr-timelapse-of-grand-central-station-7681-1080p.mp4", 1.0, "'只是大家一直这么干'：车站恒常人流"),
    ("83",    "People/Working/coverr-workers-typing-and-closing-their-laptops-4953-1080p.mp4", 6.0, "'把标准答案全部拿走'：合上电脑"),
    ("84-85", "City/Street/coverr-a-man-walks-into-a-street-and-looks-around-confidently-492-1080p.mp4", 4.0, "'还会选同样的路吗'：街头环顾"),
    # 结尾升华
    ("86-87", "Abstract/Rise/coverr-woman-lifts-her-arms-up-and-spins-6017-1080p.mp4", 3.0, "'题目本身也可以换'：舒展举手，解放感"),
    ("88-89", "People/Thinking/7719472-hd_2048_1080_25fps.mp4", 2.0, "'一生只回答别人的问题'：沉思"),
    ("90-91", "City/Skyline/12056886_1920_1080_24fps.mp4", 8.0, "'别人画好的范围'：城市天际线"),
    ("92-93", "City/Subway/mixkit-full-shot-of-a-train-in-tokyo-night-46122-hd-ready.mp4", 5.0, "'最难挣脱的牢笼'：夜行列车，封闭感"),
    ("94-95", "Nature/Sky/14365680_1920_1080_30fps.mp4", 6.0, "'从没意识到自己一直在里面'：开阔天空收尾"),
]


def ids_of(spec):
    if "-" in spec:
        a, b = spec.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(spec)]


def main():
    project = ROOT / "projects" / "demo002"
    srt = {e["id"]: e for e in parse_srt(project / "subtitle" / "demo002.srt")}
    audio = 338.45

    shots = []
    for i, (spec, mat, tin, reason) in enumerate(PLAN):
        ids = ids_of(spec)
        start = 0.0 if i == 0 else srt[ids[0]]["start"]
        shots.append(dict(ids=ids, material=mat, tin=tin, reason=reason,
                          start=round(start, 2)))
    for i, sh in enumerate(shots):
        end = shots[i + 1]["start"] if i + 1 < len(shots) else round(audio + 0.32, 2)
        sh["end"] = end
        sh["duration"] = round(end - sh["start"], 2)
        sh["out"] = round(sh["tin"] + sh["duration"], 2)

    tl = {"project": "demo002", "audio_duration": audio,
          "total_shots": len(shots),
          "coverage": [shots[0]["start"], shots[-1]["end"]], "shots": []}
    for i, sh in enumerate(shots, 1):
        tl["shots"].append({
            "seq": i, "start": sh["start"], "end": sh["end"],
            "duration": sh["duration"], "material": f"{LIB}/{sh['material']}",
            "in": sh["tin"], "out": sh["out"],
            "category": sh["material"].split("/")[-2],
            "srt_entries": sh["ids"],
            "srt_text": " / ".join(srt[j]["text"] for j in sh["ids"]),
            "reason": sh["reason"]})
    (project / "timeline.yaml").write_text(
        yaml.safe_dump(tl, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"[ok] timeline.yaml  {len(shots)} 个镜头  覆盖 0~{shots[-1]['end']}s")

    # 自检：in/out 合法、无连续同类别、复用不重叠、节奏
    idx = json.load(open(ROOT / "assets" / "broll_index.json", encoding="utf-8"))
    errs, notes, seen = [], [], {}
    for i, sh in enumerate(shots, 1):
        dur = idx[sh["material"]]["duration"]
        if sh["out"] > dur + 0.01:
            errs.append(f"#{i} out {sh['out']} > 素材时长 {dur}")
        if i > 1 and shots[i - 2]["material"].split("/")[-2] == \
                sh["material"].split("/")[-2]:
            errs.append(f"#{i - 1} 与 #{i} 连续同类别")
        if sh["material"] in seen:
            pj, (pi, po) = seen[sh["material"]]
            if not (sh["out"] <= pi or sh["tin"] >= po):
                errs.append(f"#{i} 与 #{pj} 复用区间重叠")
        seen.setdefault(sh["material"], (i, (sh["tin"], sh["out"])))
        if sh["start"] < 20 and not (2.5 <= sh["duration"] <= 5.2):
            notes.append(f"#{i} 开场 {sh['duration']}s")
        elif sh["start"] >= 20 and not (5.0 <= sh["duration"] <= 9.5):
            notes.append(f"#{i} 正文 {sh['duration']}s（排比/长句例外）")
    print("[check] 硬错误:", errs or "无")
    print(f"[note] 节奏例外 {len(notes)} 处:")
    for n in notes:
        print("  ", n)
    print("[info] 类别分布:", dict(Counter(
        s["material"].split("/")[-2] for s in shots)))


if __name__ == "__main__":
    main()
