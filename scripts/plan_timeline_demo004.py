# -*- coding: utf-8 -*-
"""一次性生成 projects/demo004/timeline.yaml（含从 SRT 提取的 srt_text）。"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
B = "B-roll/Landscape video"

shots = [
    ([1, 2], 0.0, 6.12, f"{B}/People/Thinking/6930825-hd_1920_1080_25fps.mp4", 5.0, "Thinking", "'很多人总觉得'：托腮沉思，大众惯性开场"),
    ([3], 6.12, 10.40, f"{B}/People/Studying/8199405-hd_1920_1080_25fps.mp4", 6.0, "Studying", "'选什么专业'：伏案规划未来"),
    ([4], 10.40, 15.26, f"{B}/Business/Company/coverr-colleagues-come-to-the-office-5170-1080p.mp4", 3.0, "Company", "'找什么工作'：走进办公室"),
    ([5], 15.26, 19.58, f"{B}/People/Studying/coverr-studying-9024-1080p.mp4", 8.0, "Studying", "'学一项技能'：埋头做功课"),
    ([6], 19.58, 26.78, f"{B}/People/Physical training/7676730-hd_2048_1080_25fps.mp4", 6.0, "Physical training", "'健身先把计划全安排好'：健身房训练"),
    ([7, 8], 26.78, 30.33, f"{B}/People/Thinking/7710872-hd_2048_1080_25fps.mp4", 4.0, "Thinking", "'听起来很认真。但很多时候'：神情转折"),
    ([9, 10], 30.33, 37.49, f"{B}/Abstract/Time/13622711_1920_1080_30fps.mp4", 20.0, "Time", "'没开始所以永远想不清楚'：时间空转"),
    ([11, 13], 37.49, 45.83, f"{B}/Abstract/Rise/12504761_1920_1080_30fps.mp4", 10.0, "Rise", "'答案藏在开始之后'：上升光亮"),
    ([14, 15], 45.83, 52.93, f"{B}/People/Physical training/6296583-uhd_2560_1080_25fps.mp4", 3.0, "Physical training", "'研究跑步一个月，跑三次就知道'：跑起来"),
    ([16], 52.93, 58.53, f"{B}/Technology/Computer/3147349-hd_1920_1080_25fps.mp4", 6.0, "Computer", "'看几十篇帖子研究一座城市'：屏幕攻略"),
    ([17], 58.53, 64.15, f"{B}/City/Street/14393784_1920_1080_24fps.mp4", 8.0, "Street", "'在那里生活一个星期'：走进城市街区"),
    ([18, 19], 64.15, 69.53, f"{B}/People/Working/coverr-woman-working-from-home-9277-1080p.mp4", 3.0, "Working", "'这份工作是不是真正喜欢的'：居家办公出神"),
    ([20, 21], 69.53, 74.79, f"{B}/People/Thinking/coverr-contemplative-young-woman-in-park-1080p.mp4", 3.0, "Thinking", "'专业选错了/关系合不合适'：公园独思"),
    ([22, 23], 74.79, 81.00, f"{B}/Abstract/Time/16821239_1920_1080_50fps.mp4", 5.0, "Time", "'没有能提前推导的答案'：抽象流转"),
    ([24, 25], 81.00, 85.51, f"{B}/City/Street/coverr-a-man-walks-into-a-street-and-looks-around-confidently-492-1080p.mp4", 3.0, "Street", "'你缺的是真实反馈'：走入真实街头"),
    ([26, 27], 85.51, 90.55, f"{B}/People/Working/coverr-a-girl-working-at-her-desk-drinking-coffee-2548-1080p.mp4", 8.5, "Working", "'没真正做过，不知道会不会喜欢'：隔屏想象"),
    ([28, 29], 90.55, 95.96, f"{B}/People/Thinking/7719472-hd_2048_1080_25fps.mp4", 3.0, "Thinking", "'没经历过，不知道问题出在哪'：困惑"),
    ([30, 31], 95.96, 102.19, f"{B}/City/Subway/coverr-subway-arriving-in-nyc-4114-1080p.mp4", 5.0, "Subway", "'没走进去，信息都是别人告诉你的'：车未到站"),
    ([32], 102.19, 106.54, f"{B}/People/Thinking/mixkit-closeup-of-young-woman-thinking-about-decision-15776-hd-ready.mp4", 2.5, "Thinking", "'把不知道理解成还不能开始'：迟疑特写"),
    ([33, 35], 106.54, 111.44, f"{B}/Technology/Computer/16348844_1920_1080_25fps.mp4", 3.0, "Computer", "'继续搜索比较规划'：屏幕前打转"),
    ([36], 111.44, 115.69, f"{B}/People/Thinking/coverr-flicking-through-a-notebook-outdoors-7787-1080p.mp4", 3.0, "Thinking", "'找到足够确定的答案'：翻笔记找答案"),
    ([37, 38], 115.69, 121.38, f"{B}/Abstract/Rise/8934036-hd_1920_1080_25fps.mp4", 20.0, "Rise", "'答案要等你开始以后才会出现'：光亮渐起"),
    ([39, 40], 121.38, 126.60, f"{B}/Nature/Ocean/6624689-hd_1920_1080_25fps.mp4", 18.0, "Ocean", "'学游泳，岸上研究一百种姿势'：岸与海面"),
    ([41, 43], 126.60, 133.14, f"{B}/People/Physical training/8520072-uhd_2732_1122_25fps.mp4", 4.0, "Physical training", "'何时用力/为何下沉/呼吸不对'：身体发力与换气"),
    ([44], 133.14, 137.29, f"{B}/Nature/Ocean/15625685_1920_1080_60fps.mp4", 2.0, "Ocean", "'只有下水以后才会真正出现'：入水"),
    ([45, 46], 137.29, 141.73, f"{B}/Abstract/Rise/7310193-uhd_2732_1318_30fps.mp4", 6.0, "Rise", "'真正的学习从那一刻才开始'：启程"),
    ([47, 50], 141.73, 147.32, f"{B}/People/Physical training/4859447-hd_1920_1080_25fps.mp4", 6.0, "Physical training", "'先下水呛一口调整再游'：动作修正再来一次"),
    ([51, 52], 147.32, 154.50, f"{B}/Nature/Ocean/8303107-hd_2048_1080_25fps.mp4", 6.0, "Ocean", "'在水里一点点学会游泳'：水中前行"),
    ([53, 54], 154.50, 159.21, f"{B}/People/Thinking/6913273-hd_1920_1080_25fps.mp4", 10.0, "Thinking", "'生活并不像考试'：转念"),
    ([55], 159.21, 162.25, f"{B}/People/Studying/coverr-pupils-studying-outdoors-6413-1080p.mp4", 5.0, "Studying", "'考试先学会再作答'：学生作答"),
    ([56, 58], 162.25, 170.55, f"{B}/City/Street/13527249_1920_1080_25fps.mp4", 3.0, "Street", "'生活里你先作答，现实告诉你题目'：走入人海"),
    ([59, 61], 170.55, 177.42, f"{B}/People/Thinking/coverr-writing-a-poem-outdoors-3529-1080p.mp4", 8.0, "Thinking", "'想得很多却不变确定'：写写想想"),
    ([62], 177.42, 180.72, f"{B}/Technology/Computer/7140928-hd_1920_1080_24fps.mp4", 2.0, "Computer", "'用思考代替反馈'：对屏空想"),
    ([63, 64], 180.72, 187.46, f"{B}/People/Thinking/6931297-hd_1920_1080_25fps.mp4", 4.0, "Thinking", "'只能根据已经知道的东西去想'：困于脑中"),
    ([65, 66], 187.46, 194.15, f"{B}/Abstract/Rise/4927963-hd_2048_1080_30fps.mp4", 4.0, "Rise", "'改变判断的是你还不知道的东西'：破晓"),
    ([67, 68], 194.15, 200.95, f"{B}/People/Walking/14332511_1920_1080_30fps.mp4", 3.0, "Walking", "'走出去才会遇到它们'：迈步外出"),
    ([69, 70], 200.95, 207.15, f"{B}/Business/Company/7252818-hd_1920_1080_25fps.mp4", 3.0, "Company", "'不是把未来控制得越来越精确'：会议室精密规划"),
    ([71, 72], 207.15, 212.16, f"{B}/Nature/Sky/coverr-cloudy-sky-2765-1080p.mp4", 5.0, "Sky", "'有些东西本来就不可能提前知道'：云雾未知"),
    ([73, 74], 212.16, 216.71, f"{B}/People/Working/coverr-a-team-prepares-for-a-business-meeting-169-1080p.mp4", 2.0, "Working", "'该规划要规划，风险要考虑'：筹备会议"),
    ([75, 77], 216.71, 225.18, f"{B}/People/Walking/8055346-hd_1920_1080_30fps.mp4", 1.4, "Walking", "'计划给你一个可以开始的位置'：起步"),
    ([78], 225.18, 228.87, f"{B}/People/Thinking/mixkit-face-of-a-young-pensive-woman-on-a-purple-background-33353-hd-ready.mp4", 3.0, "Thinking", "'另一种能力'：凝神"),
    ([79, 80], 228.87, 233.22, f"{B}/City/Subway/coverr-subway-departing-138-1080p.mp4", 2.0, "Subway", "'现实和预想不一样，你能不能改'：列车变道离站"),
    ([81, 82], 233.22, 239.26, f"{B}/Art/Music/13527139_1920_1080_25fps.mp4", 1.0, "Music", "'学技能发现不适合就换'：练习一门手艺"),
    ([83, 84], 239.26, 245.06, f"{B}/Business/Company/6804659-hd_2048_1080_25fps.mp4", 5.0, "Company", "'行业和想象不同就重新选择'：办公室审视"),
    ([85, 86], 245.06, 250.00, f"{B}/People/Physical training/6115673-hd_1920_1080_25fps.mp4", 1.0, "Physical training", "'身体吃不消就调整'：训练中调整姿态"),
    ([87, 89], 250.00, 260.19, f"{B}/People/Thinking/coverr-a-sad-girl-standing-by-the-riverside-4752-1080p.mp4", 3.0, "Thinking", "'关系难受，不必逼自己证明当初没错'：河边低落"),
    ([90], 260.19, 263.01, f"{B}/People/Walking/12084451_1280_720_30fps.mp4", 25.0, "Walking", "'第一步走错并不可怕'：走错的一步"),
    ([91, 94], 263.01, 272.67, f"{B}/City/Street/17696797-hd_1920_1080_30fps.mp4", 55.0, "Street", "'明知错了还继续往前走'：人流中盲目前行"),
    ([95, 96], 272.67, 278.48, f"{B}/Abstract/Time/16821228_1920_1080_50fps.mp4", 12.0, "Time", "'可靠的不是一开始就选对'：时间流转"),
    ([97, 99], 278.48, 284.52, f"{B}/Nature/Mountain/coverr-overlooking-the-mountains-8002-1080p.mp4", 8.0, "Mountain", "'没选对也能根据现实修正'：登高远望"),
    ([100, 101], 284.52, 289.32, f"{B}/Abstract/Time/15100537_1920_1080_30fps.mp4", 3.0, "Time", "'两种能力看似像其实不同'：表象流转"),
    ([102, 103], 289.32, 293.97, f"{B}/Technology/Computer/15254965_1920_1080_24fps.mp4", 12.0, "Computer", "'提前控制一切'：控制台面"),
    ([104, 106], 293.97, 300.61, f"{B}/People/Walking/17422809-hd_2048_1080_30fps.mp4", 18.0, "Walking", "'预想不同能否及时改变'：行进中转向"),
    ([107], 300.61, 304.67, f"{B}/Business/Finance/coverr-calculating-expenses-on-smartphone-1080p.mp4", 5.0, "Finance", "'简单的问题里很好用'：按计算器"),
    ([108, 109], 304.67, 309.61, f"{B}/City/Skyline/14840560_1920_1080_24fps.mp4", 12.0, "Skyline", "'人生越复杂后者越重要'：复杂都市"),
    ([110, 112], 309.61, 316.61, f"{B}/People/Thinking/6913273-hd_1920_1080_25fps.mp4", 4.0, "Thinking", "'又因为没想清楚迟迟不敢开始'：犹豫"),
    ([113], 316.61, 319.22, f"{B}/Abstract/Time/14147958_1920_1080_30fps.mp4", 3.0, "Time", "'先问自己一句'：停顿一拍"),
    ([114, 115], 319.22, 324.81, f"{B}/People/Thinking/coverr-flicking-through-a-notebook-outdoors-7787-1080p.mp4", 9.0, "Thinking", "'真的需要现在就知道答案吗'：自问"),
    ([116, 117], 324.81, 331.00, f"{B}/People/Walking/mixkit-girl-walks-bare-feet-in-golden-field-at-sunset-47673-hd-ready.mp4", 6.0, "Walking", "'先走一步，看现实告诉我什么'：夕阳下迈步收尾"),
]


def load_srt_texts():
    srt = (ROOT / "projects/demo004/subtitle/demo004.srt").read_text(encoding="utf-8")
    texts = {}
    for m in re.finditer(r"(\d+)\n[\d:,]+ --> [\d:,]+\n(.+?)(?=\n\n|\Z)", srt, re.S):
        texts[int(m.group(1))] = m.group(2).strip().replace("\n", " ")
    return texts


def main():
    texts = load_srt_texts()
    out = ["project: demo004", "audio_duration: 330.94",
           f"total_shots: {len(shots)}", "coverage:", "- 0.0", "- 331.0", "shots:"]
    for i, (entries, st, en, mat, tin, cat, reason) in enumerate(shots, 1):
        dur = round(en - st, 2)
        tout = round(tin + dur, 2)
        srt_text = " / ".join(texts[e] for e in entries)
        out.append(f"- seq: {i}")
        out.append(f"  start: {round(st, 2)}")
        out.append(f"  end: {round(en, 2)}")
        out.append(f"  duration: {dur}")
        out.append(f"  material: {mat}")
        out.append(f"  in: {tin}")
        out.append(f"  out: {tout}")
        out.append(f"  category: {cat}")
        out.append("  srt_entries:")
        for e in entries:
            out.append(f"  - {e}")
        out.append(f"  srt_text: {json.dumps(srt_text, ensure_ascii=False)}")
        out.append(f"  reason: {json.dumps(reason, ensure_ascii=False)}")
    p = ROOT / "projects/demo004/timeline.yaml"
    p.write_text("\n".join(out) + "\n", encoding="utf-8")

    import yaml
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    cats = [s["category"] for s in data["shots"]]
    dup = [i + 1 for i in range(len(cats) - 1) if cats[i] == cats[i + 1]]
    print(f"[ok] {p}  {len(data['shots'])} 镜头  连续同类: {dup or '无'}")


if __name__ == "__main__":
    main()
