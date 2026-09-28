# -*- coding: utf-8 -*-
"""一次性生成 projects/demo006/timeline.yaml。

边界自动取字幕条目起点：每镜头 start=首条字幕起点（首镜头为 0），
end=下一镜头 start，末镜头覆盖到配音结束。只手工指定：字幕分组、素材、
in 点、类别、选片理由。

本期执行选片三策略（见 README）：
- 冷素材优先：Sculpture/Music/Car/Dating/Drinking/Finance 大量启用未用素材；
- 强制轮换：demo004/demo005 用过的素材尽量避开，复用的取不相交区段；
- 负载均衡：过渡句/排比句放入约 20 个非语义镜头（雕塑=凝固、独酌=放下、
  驾驶=成本与速度等氛围匹配）。
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
B = "B-roll/Landscape video"
AUDIO_END = 691.0  # 配音 690.84s

# (srt_entries, material, in, category, reason)
shots = [
    ([1], f"{B}/Abstract/Rise/coverr-woman-lifts-her-arms-up-and-spins-6017-1080p.mp4", 4.0, "Rise", "'你可能早就可以重新开始了'：张开双臂，开场点题"),
    ([2], f"{B}/Abstract/Time/16821233_1920_1080_50fps.mp4", 4.0, "Time", "'一批早已过期的结论'：时间意象"),
    ([3], f"{B}/People/Physical training/6116178-hd_1920_1080_25fps.mp4", 1.0, "Physical training", "'我不会'：快切否定句"),
    ([4], f"{B}/Art/Sculpture/5814727-hd_1920_1080_25fps.mp4", 1.0, "Sculpture", "'太难了'：负载均衡，雕塑凝固感"),
    ([5], f"{B}/People/Working/coverr-colleagues-working-in-the-office-while-drinking-coffee-9268-1080p.mp4", 3.0, "Working", "'一个人做不了'：独坐工位"),
    ([6], f"{B}/Things/Car/14052141-hd_1920_1080_25fps.mp4", 1.0, "Car", "'这东西不值得折腾'：负载均衡，快切"),
    ([7], f"{B}/City/Subway/coverr-entry-barrier-in-a-subway-station-2104-1080p.mp4", 4.0, "Subway", "'以后有条件再说'：闸机前的等待"),
    ([8, 9], f"{B}/People/Drinking/coverr-a-woman-drinking-coffee-from-a-mug-8513-1080p.mp4", 8.0, "Drinking", "'对自己说了很多年，忘了怎么来的'：独酌自语"),
    ([10, 11], f"{B}/City/Skyline/12118126_1920_1080_30fps.mp4", 2.0, "Skyline", "'结论可能还是三年前五年前得出的'：城市变迁"),
    ([12], f"{B}/Technology/Computer/905049-hd_1920_1080_30fps.mp4", 1.0, "Computer", "'那时候的工具信息成本和今天不是一回事'：旧屏幕"),
    ([13], f"{B}/Technology/AI/8086707-hd_1920_1080_25fps.mp4", 12.0, "AI", "'可世界已经换了一套工具'：AI 意象"),
    ([14], f"{B}/Art/Sculpture/14743464_1920_1080_30fps.mp4", 1.0, "Sculpture", "'你的结论却一次都没更新过'：负载均衡，雕像=未更新"),
    ([15, 16], f"{B}/City/Skyline/12056886_1920_1080_24fps.mp4", 8.0, "Skyline", "'值得警惕的不是当年放弃了，而是世界已经变了'：天际线变化"),
    ([17], f"{B}/City/Street/coverr-a-street-on-a-rainy-day-3463-1080p.mp4", 5.0, "Street", "'你还在替过去的自己继续放弃'：雨天街头"),
    ([18], f"{B}/Nature/Ocean/6666283-uhd_2732_1318_30fps.mp4", 3.0, "Ocean", "'你可能早就可以重新开始了'：海浪重启"),
    ([19], f"{B}/People/Physical training/18573535-hd_1920_1080_25fps.mp4", 1.5, "Physical training", "'不是因为你突然变强了'：训练"),
    ([20], f"{B}/City/Skyline/coverr-new-york-city-skyline-4563-1080p.mp4", 3.0, "Skyline", "'世界偷偷把难度调低了'：城市全景"),
    ([21], f"{B}/Technology/Computer/4113236-hd_1280_720_25fps.mp4", 1.0, "Computer", "'以前你想做一个自己的小软件'：敲代码"),
    ([22], f"{B}/Art/Create/13815639_1920_1080_25fps.mp4", 6.0, "Create", "'你得学设计'：设计创作"),
    ([23], f"{B}/Technology/Computer/3147349-hd_1920_1080_25fps.mp4", 12.0, "Computer", "'学前端'：界面代码"),
    ([24], f"{B}/Business/Company/3201747-hd_1920_1080_25fps.mp4", 4.0, "Company", "'学后端'：机房式办公"),
    ([25], f"{B}/Technology/AI/6266247-hd_1920_1080_25fps.mp4", 2.0, "AI", "'研究服务器'：服务器/机器意象"),
    ([26], f"{B}/Business/Company/6562014-hd_1920_1080_25fps.mp4", 4.0, "Company", "'研究部署'：办公部署"),
    ([27], f"{B}/People/Studying/8478108-hd_1280_720_25fps.mp4", 20.0, "Studying", "'小想法背后几个月学习成本'：长时间学习"),
    ([28, 29, 30], f"{B}/People/Drinking/6760632-hd_1920_1080_25fps.mp4", 5.0, "Drinking", "'于是你想了想。算了。不值得。'：放下"),
    ([31], f"{B}/Art/Create/6911851-hd_1920_1080_25fps.mp4", 2.0, "Create", "'你想认真做视频也一样'：创作"),
    ([32], f"{B}/People/Working/coverr-timelapse-working-from-home-3951-1080p.mp4", 16.0, "Working", "'选题写稿找素材剪辑配音字幕封面'：工作延时"),
    ([33, 34], f"{B}/People/Physical training/4859756-hd_1920_1080_25fps.mp4", 4.0, "Physical training", "'全部压在一个人身上就变成巨大消耗'：负重训练"),
    ([35, 36], f"{B}/City/Street/coverr-man-taking-a-selfie-on-the-street-at-night-6100-1080p.mp4", 4.0, "Street", "'于是你又算了。很多事情其实都是这样。'：夜色街头"),
    ([37, 38], f"{B}/Business/Finance/6266250-hd_1920_1080_25fps.mp4", 10.0, "Finance", "'不是做不到，只是过去对普通人太贵了'：账本意象"),
    ([39], f"{B}/People/Drinking/7314877-hd_1920_1080_25fps.mp4", 2.0, "Drinking", "'这个贵不一定是钱'：负载均衡，独酌"),
    ([40, 41, 42], f"{B}/People/Physical training/4804784-hd_1920_1080_25fps.mp4", 4.0, "Physical training", "'是时间。是精力。是学习成本。'：精力消耗"),
    ([43], f"{B}/Business/Company/6339906-hd_1920_1080_30fps.mp4", 8.0, "Company", "'做成一件小事要提前掌握十件事'：多线并行"),
    ([44, 45], f"{B}/City/Street/coverr-posing-on-the-street-5214-1080p.mp4", 5.0, "Street", "'用一句简单的话盖过去：我不行'：街头人像"),
    ([46, 47, 48], f"{B}/Business/Finance/7693478-hd_1920_1080_25fps.mp4", 8.0, "Finance", "'这句话说错了，真正的意思是当时不划算'：算账"),
    ([49, 50], f"{B}/Technology/AI/8086707-hd_1920_1080_25fps.mp4", 15.0, "AI", "'这笔账正在被重新改写，最明显的变量就是AI'：AI 点题"),
    ([51], f"{B}/Technology/Computer/6754824-hd_1920_1080_25fps.mp4", 1.0, "Computer", "'很多人谈AI第一反应是提效'：屏幕效率"),
    ([52], f"{B}/People/Working/coverr-timelapse-working-from-home-3951-1080p.mp4", 22.0, "Working", "'以前两小时的工作现在二十分钟'：延时压缩"),
    ([53], f"{B}/Business/Company/6803584-hd_2048_1080_25fps.mp4", 20.0, "Company", "'以前五个人的活现在一个人'：办公室"),
    ([54, 55], f"{B}/Art/Sculpture/10370518-hd_1920_1080_24fps.mp4", 6.0, "Sculpture", "'如果只是做快一点就低估了它'：负载均衡，雕塑静观"),
    ([56], f"{B}/Things/Car/20153917-hd_1920_1080_24fps.mp4", 10.0, "Car", "'改变的不只是速度'：负载均衡，车与速度双关"),
    ([57], f"{B}/Abstract/Rise/coverr-thumbs-up-2196-1080p.mp4", 3.0, "Rise", "'连什么事情值得做都会开始变化'：肯定手势"),
    ([58, 59], f"{B}/People/Studying/coverr-student-turning-the-pages-of-a-marketing-book-2770-1080p.mp4", 20.0, "Studying", "'先说学习。以前学习陌生领域有个现实问题'：翻书"),
    ([60], f"{B}/City/Subway/coverr-reading-a-comic-whilst-waiting-for-the-subway-6247-1080p.mp4", 3.0, "Subway", "'你一定会卡住'：站台停滞"),
    ([61], f"{B}/People/Studying/coverr-studying-9024-1080p.mp4", 14.0, "Studying", "'一本书看到某一页突然看不懂了'：读书停顿"),
    ([62], f"{B}/Technology/Computer/16348844_1920_1080_25fps.mp4", 8.0, "Computer", "'一个视频听到某个概念没跟上'：看屏幕"),
    ([63, 64], f"{B}/People/Studying/mixkit-a-young-man-studying-in-the-library-14734-hd-ready.mp4", 8.0, "Studying", "'老师不会一直在旁边，作者不会停下来换五种方式解释'：图书馆自学"),
    ([65, 66], f"{B}/People/Walking/7580172-hd_1920_1080_25fps.mp4", 2.0, "Walking", "'学习不是结束在知识太难，而是结束在某个普通瞬间'：停下脚步"),
    ([67, 68, 69], f"{B}/People/Dating/coverr-outdoor-messaging-break-1080p.mp4", 4.0, "Dating", "'卡住了。懒得查了。算了。'：负载均衡，放下手机"),
    ([70], f"{B}/Nature/Sky/coverr-ski-resort-2528-1080p.mp4", 4.0, "Sky", "'可现在不一样'：开阔转场"),
    ([71], f"{B}/Technology/Computer/13814801_1920_1080_100fps.mp4", 6.0, "Computer", "'没听懂让AI换种方式解释'：屏幕交互"),
    ([72], f"{B}/Technology/AI/coverr-close-up-of-a-working-girl-3611-1080p.mp4", 6.0, "AI", "'还是不懂可以再简单一点'：人机协作"),
    ([73, 74, 75], f"{B}/People/Studying/8199405-hd_1920_1080_25fps.mp4", 14.0, "Studying", "'可以举例。可以类比。可以把前置知识补回来。'：补课"),
    ([76], f"{B}/Technology/AI/6266247-hd_1920_1080_25fps.mp4", 15.0, "AI", "'把理解说给它听，让它告诉你哪步想错了'：AI 对话"),
    ([77], f"{B}/People/Dating/8626905-hd_2048_1080_25fps.mp4", 10.0, "Dating", "'以前要找一个耐心又懂的人陪你掰开'：负载均衡，两人陪伴讨论"),
    ([78], f"{B}/Business/Finance/6266254-hd_1920_1080_25fps.mp4", 5.0, "Finance", "'成本正在无限接近于零'：数字账本"),
    ([79, 80], f"{B}/People/Thinking/7710872-hd_2048_1080_25fps.mp4", 1.0, "Thinking", "'注意。知识本身并没有突然变简单。'：强调停顿"),
    ([81], f"{B}/Nature/Ocean/7047319-uhd_2732_1318_30fps.mp4", 5.0, "Ocean", "'真正变便宜的是从不懂到懂之间的过程'：海面过渡"),
    ([82, 83], f"{B}/Abstract/Rise/12504761_1920_1080_30fps.mp4", 25.0, "Rise", "'学习方式已经变了。但变化还不止这些。'：上升过渡"),
    ([84, 85], f"{B}/People/Working/coverr-coworkers-arrive-at-the-office-9520-1080p.mp4", 6.0, "Working", "'再说工作。一个人能做多少事取决于掌握多少技能'：办公室入场"),
    ([86], f"{B}/Art/Create/13815639_1920_1080_25fps.mp4", 10.0, "Create", "'不会设计就找设计师'：设计"),
    ([87], f"{B}/Technology/Computer/2958500-hd_2048_1080_24fps.mp4", 1.0, "Computer", "'不会写代码就找程序员'：代码"),
    ([88], f"{B}/People/Working/coverr-the-sensory-screen-on-the-printer-machine-4383-1080p.mp4", 12.0, "Working", "'不会剪视频就找剪辑'：机器操作台"),
    ([89], f"{B}/Business/Finance/coverr-a-trader-performing-financial-analysis-of-cryptocurrency-using-a-phone-app-8914-1080p.mp4", 8.0, "Finance", "'不会分析数据就找另一个人'：数据分析"),
    ([90], f"{B}/Business/Company/3201747-hd_1920_1080_25fps.mp4", 3.0, "Company", "'想法进入现实前得先满足一堆条件'：办公筹备"),
    ([91, 92, 93, 94], f"{B}/People/Walking/12084451_1280_720_30fps.mp4", 35.0, "Walking", "'要么自己学。要么花钱。要么找人。要么组团队。'：奔波凑条件"),
    ([95, 96], f"{B}/Art/Sculpture/3051373-hd_1920_1080_24fps.mp4", 12.0, "Sculpture", "'很多想法甚至从没得到被证明的机会'：负载均衡，未完成的塑像"),
    ([97, 98], f"{B}/People/Thinking/coverr-writing-a-poem-outdoors-3529-1080p.mp4", 2.0, "Thinking", "'只是在脑子里待了一会儿，然后因为太麻烦消失了'：写写停停"),
    ([99], f"{B}/People/Physical training/12118260_1920_1080_30fps.mp4", 4.0, "Physical training", "'今天一个人第一次可以便宜地跨过技能边界'：跨越障碍"),
    ([100], f"{B}/Technology/Computer/6804117-hd_2048_1080_25fps.mp4", 20.0, "Computer", "'不懂代码也可以先把第一个版本跑起来'：运行界面"),
    ([101], f"{B}/Art/Create/10474553-hd_1920_1080_30fps.mp4", 10.0, "Create", "'不懂设计也可以先看到它大概长什么样'：画出草样"),
    ([102], f"{B}/Art/Music/8161409-hd_1920_1080_25fps.mp4", 1.0, "Music", "'不会剪辑也可以先让内容进入现实'：负载均衡，制作台"),
    ([103, 104], f"{B}/Art/Sculpture/13438686_1920_1080_30fps.mp4", 2.0, "Sculpture", "'它们当然未必专业，也未必成熟'：负载均衡，粗坯"),
    ([105, 106], f"{B}/People/Walking/17422809-hd_2048_1080_30fps.mp4", 25.0, "Walking", "'一个普通人，可以先开始了'：迈步"),
    ([107], f"{B}/People/Studying/coverr-pupils-studying-outdoors-6413-1080p.mp4", 10.0, "Studying", "'以前是先学会，才能开始做'：学生"),
    ([108, 109], f"{B}/People/Physical training/4867626-hd_1920_1080_25fps.mp4", 2.0, "Physical training", "'先开始做，然后在做的过程中学会'：边练边学"),
    ([110, 111], f"{B}/City/Skyline/coverr-new-york-city-skyline-2410-1080p.mp4", 4.0, "Skyline", "'顺序只换了一下位置，却决定多少想法能来到世界'：城市全景"),
    ([112, 113], f"{B}/Technology/AI/8086707-hd_1920_1080_25fps.mp4", 1.0, "AI", "'更大的变化：AI甚至在改变我们思考问题的方式'：AI 意象"),
    ([114, 115], f"{B}/People/Thinking/coverr-contemplative-young-woman-in-park-1080p.mp4", 1.0, "Thinking", "'一个模糊的念头出现在脑子里，觉得有点意思'：出神"),
    ([116, 117, 118], f"{B}/People/Drinking/8828286-hd_1920_1080_25fps.mp4", 4.0, "Drinking", "'但说不清楚。推不下去。也不知道哪里有漏洞。'：负载均衡，独酌卡壳"),
    ([119, 120], f"{B}/Abstract/Time/7033607-hd_1920_1080_25fps.mp4", 25.0, "Time", "'它在脑子里转几圈。消失了。'：时间消散"),
    ([121, 122], f"{B}/City/Street/coverr-girl-in-the-street-6721-1080p.mp4", 6.0, "Street", "'每天都有很多这样的念头，不是它们没有价值'：街头日常"),
    ([123], f"{B}/Art/Sculpture/13437709_1920_1080_25fps.mp4", 10.0, "Sculpture", "'把模糊直觉推成完整东西需要很高成本'：雕琢成形"),
    ([124], f"{B}/People/Drinking/6831306-hd_1920_1080_30fps.mp4", 6.0, "Drinking", "'你需要有人和你讨论'：负载均衡，对坐"),
    ([125], f"{B}/People/Studying/8478108-hd_1280_720_25fps.mp4", 30.0, "Studying", "'需要资料'：查资料"),
    ([126], f"{B}/People/Dating/10220169-hd_2048_1080_25fps.mp4", 8.0, "Dating", "'需要反驳'：负载均衡，两人交锋"),
    ([127], f"{B}/Business/Finance/coverr-a-trader-writing-something-in-a-notebook-7909-1080p.mp4", 5.0, "Finance", "'需要不断组织自己的语言'：书写组织"),
    ([128], f"{B}/Art/Create/6607345-hd_1920_1080_25fps.mp4", 10.0, "Create", "'还没成形的念头也可以被继续往下推'：创作推进"),
    ([129, 130, 131, 132, 133], f"{B}/Technology/Computer/15029080_1920_1080_25fps.mp4", 1.0, "Computer", "'让AI质疑它。反驳它。找漏洞。换角度。找类似思想。'：屏幕来回"),
    ([134], f"{B}/Technology/AI/coverr-ai-voice-4386-1080p.mp4", 7.0, "AI", "'你说得不清楚，它可以逼着你把它说清楚'：AI 语音"),
    ([135], f"{B}/Art/Music/6494232-hd_2048_1080_25fps.mp4", 10.0, "Music", "'只能存在十分钟的念头被推成清晰的观点'：负载均衡，旋律成形"),
    ([136], f"{B}/Art/Create/7230987-hd_1920_1080_25fps.mp4", 9.0, "Create", "'一个观点，再变成一篇文章'：写作"),
    ([137], f"{B}/Business/Company/7253096-hd_1920_1080_25fps.mp4", 4.0, "Company", "'一个产品'：产品讨论"),
    ([138], f"{B}/Technology/Lab/13822277_1920_1080_25fps.mp4", 1.0, "Lab", "'一个研究方向'：实验"),
    ([139], f"{B}/Art/Sculpture/15199954-hd_1920_1080_25fps.mp4", 4.0, "Sculpture", "'慢慢变成一套属于你自己的东西'：负载均衡，作品成形"),
    ([140, 141], f"{B}/People/Working/coverr-skateboarding-in-the-office-5473-1080p.mp4", 8.0, "Working", "'AI改变的已经不是某一个工作环节了'：办公室新玩法"),
    ([142], f"{B}/City/Street/mixkit-aerial-view-of-the-glass-corporate-buildings-of-a-big-49845-hd-ready.mp4", 8.0, "Street", "'改变一个人从想法到现实之间的距离'：俯瞰距离"),
    ([143, 144], f"{B}/City/Skyline/coverr-skyscrapers-in-new-york-2093-1080p.mp4", 3.0, "Skyline", "'值得关注的是一个普通人能力边界的变化'：摩天楼群"),
    ([145, 146, 147], f"{B}/City/Subway/mixkit-full-shot-of-a-train-in-tokyo-night-46122-hd-ready.mp4", 6.0, "Subway", "'以前：你会才能做，你不会就别碰'：夜列车"),
    ([148, 149], f"{B}/People/Walking/mixkit-girl-walks-bare-feet-in-golden-field-at-sunset-47673-hd-ready.mp4", 10.0, "Walking", "'你可以一边不会，一边开始'：边走边学"),
    ([150], f"{B}/City/Skyline/coverr-city-skyscrapers-471-1080p.mp4", 3.0, "Skyline", "'这两个世界，差别非常大'：仰视高楼"),
    ([151], f"{B}/People/Thinking/mixkit-closeup-of-young-woman-thinking-about-decision-15776-hd-ready.mp4", 7.0, "Thinking", "'但最有意思的问题也恰恰出现在这里'：特写转折"),
    ([152, 153, 154], f"{B}/City/Subway/coverr-subway-timelapse-7958-1080p.mp4", 2.0, "Subway", "'工具更新得非常快。世界更新得非常快。成本更新得非常快。'：地铁延时"),
    ([155], f"{B}/Art/Sculpture/16717305_1920_1080_25fps.mp4", 5.0, "Sculpture", "'人的判断，却更新得非常慢'：负载均衡，静止雕塑反差"),
    ([156, 157], f"{B}/People/Working/coverr-a-young-man-using-a-smartphone-at-work-5494-1080p.mp4", 4.5, "Working", "'我们会给手机更新系统，会给电脑更新软件'：刷手机"),
    ([158], f"{B}/Technology/Computer/13814801_1920_1080_100fps.mp4", 7.5, "Computer", "'应用版本太旧了，我们知道可能已经不能用了'：屏幕"),
    ([159], f"{B}/People/Thinking/coverr-flicking-through-a-notebook-outdoors-7787-1080p.mp4", 1.0, "Thinking", "'却很少检查自己脑子里的东西有没有过期'：翻旧笔记"),
    ([160, 161, 162], f"{B}/City/Street/coverr-stylish-woman-walking-down-the-street-1557-1080p.mp4", 6.0, "Street", "'什么适合我。什么不适合我。什么我能做。'：街头行走"),
    ([163, 164, 165], f"{B}/Business/Finance/coverr-many-old-coins-fall-on-a-heap-4647-1080p.mp4", 4.0, "Finance", "'什么我做不了。什么值得投入。什么最好放弃。'：硬币衡量"),
    ([166, 167], f"{B}/Art/Sculpture/7316620-hd_1920_1080_25fps.mp4", 6.0, "Sculpture", "'判断一旦形成就像写进身份里，几年都不再碰'：负载均衡，铸造成型"),
    ([168, 169, 170], f"{B}/City/Street/17696797-hd_1920_1080_30fps.mp4", 25.0, "Street", "'现实条件早变了，你还在执行旧世界的决定'：人潮惯性"),
    ([171, 172], f"{B}/People/Physical training/6116178-hd_1920_1080_25fps.mp4", 2.0, "Physical training", "'我不会。太麻烦。'：快切"),
    ([173], f"{B}/Things/Car/12396440_1920_1080_30fps.mp4", 4.0, "Car", "'一个人搞不定'：负载均衡，独自驾驶"),
    ([174, 175], f"{B}/People/Drinking/7423558-hd_1920_1080_30fps.mp4", 8.0, "Drinking", "'我没有条件。等以后再说。'：负载均衡，独酌推迟"),
    ([176], f"{B}/Abstract/Time/15100537_1920_1080_30fps.mp4", 9.0, "Time", "'可这里面的有些话，可能早就已经过期了'：时间过期"),
    ([177, 178, 179, 180], f"{B}/People/Dating/coverr-tranquil-marina-walk-at-dusk-1080p.mp4", 6.0, "Dating", "'这并不是说当年的选择错了，当时放弃完全正确'：负载均衡，黄昏回望"),
    ([181], f"{B}/Things/Car/3066463-hd_2048_1080_24fps.mp4", 8.0, "Car", "'因为那个时候做这件事确实太贵太难'：负载均衡，行车成本"),
    ([182, 183], f"{B}/Business/Finance/coverr-a-trader-performing-financial-analysis-of-cryptocurrency-using-a-phone-app-and-laptop-9327-1080p.mp4", 8.0, "Finance", "'一百份成本换二十份收益，不做就是理性的'：算账"),
    ([184], f"{B}/Business/Stock/16425935_1920_1080_50fps.mp4", 9.0, "Stock", "'但如果几年以后它突然只需要十份成本呢'：行情突变"),
    ([185, 186], f"{B}/Abstract/Time/13622711_1920_1080_30fps.mp4", 40.0, "Time", "'成本从一百变成十了，你还拿着当年的账本'：旧时光"),
    ([187, 188], f"{B}/Nature/Ocean/8336026-hd_2048_1080_25fps.mp4", 3.0, "Ocean", "'过去正确的选择不代表今天还应该继续执行'：海浪翻篇"),
    ([189, 190], f"{B}/Business/Company/6803584-hd_2048_1080_25fps.mp4", 25.0, "Company", "'不只是未来需要重新规划，过去放弃过的也值得重新检查'：白板重议"),
    ([191, 192], f"{B}/Nature/Ocean/6624689-hd_1920_1080_25fps.mp4", 25.0, "Ocean", "'不是为了追回所有遗憾，更不是一切都可以重新来过'：海面平静"),
    ([193], f"{B}/People/Physical training/4859764-hd_1920_1080_25fps.mp4", 15.0, "Physical training", "'曾经阻挡你的条件，有一部分可能已经不存在了'：突破"),
    ([194, 195], f"{B}/People/Drinking/7314896-hd_1920_1080_25fps.mp4", 8.0, "Drinking", "'你不一定真的要重新开始。但你至少应该重新算一次。'：负载均衡，举杯斟酌"),
    ([196, 197], f"{B}/Business/Finance/7693478-hd_1920_1080_25fps.mp4", 16.0, "Finance", "'有些事情，当年太贵。现在呢。'：账本"),
    ([198, 199], f"{B}/People/Studying/8478108-hd_1280_720_25fps.mp4", 40.0, "Studying", "'有些东西，当年必须学会很多技能才能做。现在呢。'：学习"),
    ([200, 201], f"{B}/City/Skyline/13459978_1920_1080_24fps.mp4", 20.0, "Skyline", "'有些想法，当年一个人根本落不了地。现在呢。'：城市落地"),
    ([202, 203], f"{B}/People/Studying/coverr-studying-9024-1080p.mp4", 18.0, "Studying", "'有些问题，当年没人教你就只能卡在那里。现在呢。'：卡住的书页"),
    ([204, 205], f"{B}/Nature/Ocean/5982833-hd_1920_1080_24fps.mp4", 0.5, "Ocean", "'你过去放弃的很多事情，也许并不是因为你不行'：海面释然"),
    ([206, 207], f"{B}/Business/Finance/coverr-a-trader-performing-financial-analysis-of-cryptocurrency-using-a-phone-app-8914-1080p.mp4", 13.0, "Finance", "'现在成本变了。你该重新算一遍账了。'：重新计算"),
    ([208, 209], f"{B}/Art/Music/6722773-hd_2048_1080_25fps.mp4", 8.0, "Music", "'别急着想一个宏大的答案。只想一件事就够了。'：负载均衡，旋律收拢"),
    ([210], f"{B}/People/Dating/coverr-a-girl-taking-photos-of-her-boyfriend-5881-1080p.mp4", 5.0, "Dating", "'有没有什么东西，你曾经真的很想做'：负载均衡，拍照心愿"),
    ([211, 212, 213], f"{B}/People/Drinking/7314882-hd_1920_1080_25fps.mp4", 10.0, "Drinking", "'因为太难太贵太麻烦。你告诉自己。算了。'：放下酒杯"),
    ([214], f"{B}/Abstract/Time/16821239_1920_1080_50fps.mp4", 12.0, "Time", "'然后这一算了，就是很多年'：岁月流逝"),
    ([215], f"{B}/Abstract/Rise/8493720-hd_2048_1080_24fps.mp4", 2.0, "Rise", "'可如果今天重新开始'：晨光重启"),
    ([216], f"{B}/Things/Car/12396440_1920_1080_30fps.mp4", 7.0, "Car", "'工具，还是当年的工具吗'：负载均衡，车内视角"),
    ([217], f"{B}/City/Subway/coverr-entry-barrier-in-a-subway-station-2104-1080p.mp4", 7.0, "Subway", "'门槛，还是当年的门槛吗'：闸机=门槛"),
    ([218], f"{B}/City/Skyline/mixkit-tour-high-above-a-city-at-dusk-41375-hd-ready.mp4", 5.0, "Skyline", "'这个世界，还是当年的世界吗'：黄昏城市"),
    ([219, 220, 221], f"{B}/People/Thinking/coverr-friends-looking-on-an-iphone-7587-1080p.mp4", 10.0, "Thinking", "'最重要的是。你，还是当年的你吗。'：凝视追问"),
    ([222, 223, 224], f"{B}/Nature/Ocean/6624689-hd_1920_1080_25fps.mp4", 1.0, "Ocean", "'你为什么还要继续执行，当年的答案'：海面收束全片"),
]


def load_srt():
    srt = (ROOT / "projects/demo006/subtitle/demo006.srt").read_text(encoding="utf-8")
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
    bounds = [0.0] + [starts[s[0][0]] for s in shots[1:]] + [AUDIO_END]

    index = json.loads((ROOT / "assets/broll_index.json").read_text(encoding="utf-8"))
    out = ["project: demo006", "audio_duration: 690.84",
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
    p = ROOT / "projects/demo006/timeline.yaml"
    p.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"[ok] {p}  {len(shots)} 镜头，覆盖 0–{AUDIO_END}s")


if __name__ == "__main__":
    main()
