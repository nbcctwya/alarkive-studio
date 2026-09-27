# -*- coding: utf-8 -*-
"""一次性生成 projects/demo005/timeline.yaml。

边界自动取字幕条目起点：每镜头 start=首条字幕起点（首镜头为 0），
end=下一镜头 start，末镜头覆盖到配音结束。只手工指定：字幕分组、素材、
in 点、类别、选片理由。
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
B = "B-roll/Landscape video"
AUDIO_END = 313.10  # 配音 313.03s，留 0.07s 余量

# (srt_entries, material, in, category, reason)
shots = [
    ([1, 2], f"{B}/People/Thinking/6930825-hd_1920_1080_25fps.mp4", 2.0, "Thinking", "'最优解不是设计出来的'：沉思开场点题"),
    ([3, 4], f"{B}/People/Working/8468351-hd_1366_720_25fps.mp4", 3.0, "Working", "'继续想，再想清楚一点'：伏案苦想"),
    ([5, 6], f"{B}/People/Studying/coverr-student-turning-the-pages-of-a-marketing-book-2770-1080p.mp4", 10.0, "Studying", "'开始前把最好的答案找出来'：翻书找答案"),
    ([7, 8], f"{B}/People/Thinking/7710872-hd_2048_1080_25fps.mp4", 6.0, "Thinking", "'复杂问题恰恰不是靠这样解决的'：转念"),
    ([9, 10], f"{B}/Technology/Computer/6754824-hd_1920_1080_25fps.mp4", 10.0, "Computer", "'迟迟找不到答案，不是想得不够多'：对屏苦思"),
    ([11], f"{B}/Abstract/Time/13622711_1920_1080_30fps.mp4", 30.0, "Time", "'不该靠想直接把答案设计出来'：空转，重句收束"),
    ([12], f"{B}/Technology/Lab/9574023-hd_2048_1080_25fps.mp4", 8.0, "Lab", "'最早意识到是做科研的时候'：实验室入场"),
    ([13, 14], f"{B}/People/Thinking/6931297-hd_1920_1080_25fps.mp4", 6.0, "Thinking", "'设计模型花很多时间去想，模块怎么接'：苦思"),
    ([15, 16], f"{B}/Technology/Lab/13822277_1920_1080_25fps.mp4", 2.0, "Lab", "'结构要不要加，参数怎么设'：实验操作"),
    ([17, 18], f"{B}/Technology/Computer/15254965_1920_1080_24fps.mp4", 3.0, "Computer", "'哪种方案理论上最合理/一直在做同一件事'：屏幕推演"),
    ([19], f"{B}/Technology/Lab/3192026-hd_1920_1080_25fps.mp4", 2.0, "Lab", "'靠自己判断直接设计出足够好的模型'：手工调试"),
    ([20], f"{B}/Business/Stock/coverr-a-broker-works-with-a-cryptocurrency-candlestick-chart-9867-1080p.mp4", 4.0, "Stock", "'实验做多了，打击直觉'：行情跳动，直觉失效"),
    ([21], f"{B}/Business/Finance/coverr-a-trader-looking-upset-because-of-a-failure-in-his-analyses-6797-1080p.mp4", 4.0, "Finance", "'漂亮的想法跑起来一塌糊涂'：交易员懊恼"),
    ([22], f"{B}/Things/Flower/16316121_1920_1080_25fps.mp4", 1.0, "Flower", "'不起眼的方案跑出更好的结果'：小花绽放"),
    ([23, 24, 25], f"{B}/People/Thinking/7719472-hd_2048_1080_25fps.mp4", 3.0, "Thinking", "'不是不够聪明，是大脑放错了位置'：自省"),
    ([26], f"{B}/Technology/Lab/8381327-hd_1920_1080_25fps.mp4", 3.0, "Lab", "'开始把科研实验自动化'：自动化实验装置"),
    ([27], f"{B}/Business/Finance/coverr-falling-coins-6164-1080p.mp4", 4.0, "Finance", "'不再押注某一个方案'：硬币散落，不再下注"),
    ([28, 29], f"{B}/Technology/Computer/6804117-hd_2048_1080_25fps.mp4", 15.0, "Computer", "'一次产生很多方案，批量跑实验'：多屏并行"),
    ([30, 31], f"{B}/Business/Company/coverr-putting-wood-on-a-machine-8859-1080p.mp4", 5.0, "Company", "'好的留下，差的淘汰'：机器筛除"),
    ([32], f"{B}/Abstract/Rise/12504761_1920_1080_30fps.mp4", 20.0, "Rise", "'表现好的方向继续产生新变化'：迭代上升"),
    ([33], f"{B}/People/Thinking/coverr-contemplative-young-woman-in-park-1080p.mp4", 8.0, "Thinking", "'慢慢地我发现一件很有意思的事'：若有所悟"),
    ([34], f"{B}/Art/Create/10474553-hd_1920_1080_30fps.mp4", 5.0, "Create", "'好模型不像我亲手设计的'：创作之手"),
    ([35], f"{B}/Things/Flower/6133066-hd_1920_1080_30fps.mp4", 6.0, "Flower", "'从一堆方案里自己长出来的'：生长意象"),
    ([36], f"{B}/People/Working/coverr-young-professional-on-the-move-1080p.mp4", 6.0, "Working", "'我的角色也发生了变化'：起身转场"),
    ([37, 38], f"{B}/Technology/Computer/6963744-hd_1920_1080_25fps.mp4", 7.0, "Computer", "'以前问最好的模型长什么样'：盯屏追问"),
    ([39, 40], f"{B}/Technology/Lab/9574023-hd_2048_1080_25fps.mp4", 12.0, "Lab", "'能不能设计一个系统让好模型自己冒出来'：实验系统运转"),
    ([41, 42], f"{B}/Art/Sculpture/12046450_1920_1080_25fps.mp4", 3.0, "Sculpture", "'两个问题看起来很像，其实不是一回事'：相似形制并置"),
    ([43], f"{B}/Art/Create/6607345-hd_1920_1080_25fps.mp4", 5.0, "Create", "'前者是在设计答案'：手绘图纸"),
    ([44], f"{B}/Technology/Computer/2958500-hd_2048_1080_24fps.mp4", 5.0, "Computer", "'后者是在设计产生答案的机制'：机制与代码"),
    ([45], f"{B}/City/Skyline/13459978_1920_1080_24fps.mp4", 10.0, "Skyline", "'真正复杂的问题，后者重要得多'：复杂都市"),
    ([46], f"{B}/Business/Stock/12984416_1920_1080_100fps.mp4", 15.0, "Stock", "'复杂意味着变量很多'：变量跳动"),
    ([47], f"{B}/Abstract/Time/16821228_1920_1080_50fps.mp4", 4.0, "Time", "'掌握的信息永远不完整'：流光残缺"),
    ([48], f"{B}/City/Street/coverr-west-broadway-street-6804-1080p.mp4", 4.0, "Street", "'进入现实才知道行不行'：走进真实街区"),
    ([49], f"{B}/People/Thinking/mixkit-closeup-of-young-woman-thinking-about-decision-15776-hd-ready.mp4", 1.0, "Thinking", "'可我们在生活里经常反过来'：迟疑"),
    ([50], f"{B}/People/Working/coverr-a-blonde-man-works-on-a-laptop-in-his-home-office-5380-1080p.mp4", 4.0, "Working", "'还没做内容就想清楚终极定位'：电脑前空想定位"),
    ([51], f"{B}/City/Subway/14746572_1920_1080_24fps.mp4", 6.0, "Subway", "'还没进行业就想判断未来十年走哪条路'：轨道分向"),
    ([52], f"{B}/Business/Company/6325848-hd_1920_1080_25fps.mp4", 8.0, "Company", "'还没做产品就想把用户需求推演完'：会议推演"),
    ([53], f"{B}/People/Thinking/coverr-writing-a-poem-outdoors-3529-1080p.mp4", 12.0, "Thinking", "'人生选择总想先找到确定答案'：写个不停"),
    ([54, 55], f"{B}/Abstract/Time/7033607-hd_1920_1080_25fps.mp4", 15.0, "Time", "'有些答案不存在于开始之前'：时间之问"),
    ([56], f"{B}/Abstract/Rise/8493720-hd_2048_1080_24fps.mp4", 10.0, "Rise", "'尝试反馈淘汰再尝试后才出现'：螺旋上升"),
    ([57, 58], f"{B}/People/Thinking/6931297-hd_1920_1080_25fps.mp4", 9.0, "Thinking", "'不是说思考不重要，更不是随便乱试'：澄清"),
    ([59, 60], f"{B}/City/Skyline/coverr-the-vessel-sky-view-5546-1080p.mp4", 4.0, "Skyline", "'你要开始区分两件事'：交错结构两分"),
    ([61], f"{B}/People/Working/coverr-the-sensory-screen-on-the-printer-machine-4383-1080p.mp4", 8.0, "Working", "'什么东西应该被你控制'：触控操作"),
    ([62], f"{B}/Nature/Ocean/2873484-hd_1920_1080_25fps.mp4", 2.0, "Ocean", "'什么东西应该交给演化'：自然之力"),
    ([63, 64], f"{B}/Things/Car/coverr-driving-a-mercedes-6097-1080p.mp4", 2.0, "Car", "'控制方向，控制底线'：驾驶握盘"),
    ([65], f"{B}/Art/Create/7230987-hd_1920_1080_25fps.mp4", 4.0, "Create", "'控制什么样的结果值得留下'：创作取舍"),
    ([66], f"{B}/Technology/Lab/8381327-hd_1920_1080_25fps.mp4", 7.0, "Lab", "'控制系统有没有真获得反馈'：读取实验数据"),
    ([67, 68], f"{B}/Nature/Sky/14365680_1920_1080_30fps.mp4", 10.0, "Sky", "'不必提前控制最终答案长成什么样'：天空留白"),
    ([69], f"{B}/Abstract/Rise/8934036-hd_1920_1080_25fps.mp4", 30.0, "Rise", "'我把这种思路叫作演化控制定律'：命名时刻"),
    ([70, 71], f"{B}/People/Thinking/mixkit-face-of-a-young-pensive-woman-on-a-purple-background-33353-hd-ready.mp4", 2.0, "Thinking", "'不要总想着直接设计答案'：面部特写"),
    ([72], f"{B}/Technology/Computer/15029080_1920_1080_25fps.mp4", 24.0, "Computer", "'设计一个能筛出答案的系统'：系统界面"),
    ([73, 74], f"{B}/People/Thinking/6930825-hd_1920_1080_25fps.mp4", 12.0, "Thinking", "'最好的方向不是坐在那里想出来的'：静坐无用"),
    ([75], f"{B}/City/Street/17696797-hd_1920_1080_30fps.mp4", 8.0, "Street", "'进入真实世界被一点点筛出来'：人潮淘洗"),
    ([76], f"{B}/Business/Company/7252809-hd_1920_1080_25fps.mp4", 4.0, "Company", "'再次遇到很复杂的问题'：职场难题"),
    ([77, 78], f"{B}/People/Studying/coverr-student-studying-in-a-coffee-shop-7986-1080p.mp4", 5.0, "Studying", "'少问一句最好的答案到底是什么'：放下追问"),
    ([79, 80], f"{B}/Art/Create/3246281-hd_1920_1080_25fps.mp4", 5.0, "Create", "'多问一句，能不能先建立一个机制'：动手搭建"),
    ([81, 82], f"{B}/Nature/Ocean/1414758-hd_1920_1080_25fps.mp4", 15.0, "Ocean", "'让不同的答案出现，让现实帮我筛选'：海浪淘洗"),
    ([83], f"{B}/Things/Flower/13600108_1920_1080_25fps.mp4", 6.0, "Flower", "'让更好的那个慢慢长出来'：花朵生长"),
    ([84, 85, 86], f"{B}/City/Subway/coverr-woman-waiting-for-the-subway-3892-1080p.mp4", 3.0, "Subway", "'想了很久却迟迟没有真正开始'：站台等待"),
    ([87, 88], f"{B}/People/Thinking/6913273-hd_1920_1080_25fps.mp4", 12.0, "Thinking", "'你缺的并不是更好的答案'：点醒"),
    ([89, 90], f"{B}/Nature/Ocean/6666455-uhd_2732_1318_30fps.mp4", 2.0, "Ocean", "'让答案自己浮现出来的系统'：浮现出水面，收尾"),
]


def load_srt():
    srt = (ROOT / "projects/demo005/subtitle/demo005.srt").read_text(encoding="utf-8")
    starts, texts = {}, {}
    for m in re.finditer(r"(\d+)\n(\d+):(\d+):(\d+),(\d+) --> [\d:,]+\n(.+?)(?=\n\n|\Z)",
                         srt, re.S):
        idx = int(m.group(1))
        starts[idx] = int(m.group(2)) * 3600 + int(m.group(3)) * 60 \
            + int(m.group(4)) + int(m.group(5)) / 1000
        texts[idx] = m.group(6).strip().replace("\n", " ")
    return starts, texts


def main():
    starts, texts = load_srt()
    # 边界：首镜头 0.0，其余=首条字幕起点；末尾覆盖到配音结束
    bounds = [0.0] + [starts[s[0][0]] for s in shots[1:]] + [AUDIO_END]

    index = json.loads((ROOT / "assets/broll_index.json").read_text(encoding="utf-8"))
    out = ["project: demo005", "audio_duration: 313.03",
           f"total_shots: {len(shots)}", "coverage:", "- 0.0", f"- {AUDIO_END}",
           "shots:"]
    prev_cat = None
    for i, ((entries, mat, tin, cat, reason), st, en) in enumerate(
            zip(shots, bounds, bounds[1:]), 1):
        assert cat != prev_cat, f"镜头{i} 与前一同类: {cat}"
        prev_cat = cat
        st, en = round(st, 2), round(en, 2)
        dur = round(en - st, 2)
        tout = round(tin + dur, 2)
        rel = mat.split("Landscape video/")[-1]
        mat_d = index[rel]["duration"]
        if tout > mat_d + 0.05:
            tin = round(max(0.0, mat_d - 0.1 - dur), 2)
            tout = round(tin + dur, 2)
            print(f"[fix] 镜头{i} in 改为 {tin}（素材 {mat_d}s）")
        srt_text = " / ".join(texts[e] for e in entries)
        out.append(f"- seq: {i}")
        out.append(f"  start: {st}")
        out.append(f"  end: {en}")
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
    p = ROOT / "projects/demo005/timeline.yaml"
    p.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"[ok] {p}  {len(shots)} 镜头，覆盖 0–{AUDIO_END}s")


if __name__ == "__main__":
    main()
