# -*- coding: utf-8 -*-
"""一次性生成 projects/demo007/timeline.yaml。

边界自动取字幕条目起点。本期主题「答案早就来了，只是你不喜欢」，
感情段占比大：Dating 冷素材全部启用，Flower 承担幻想/失去隐喻，
Sculpture/Music 走负载均衡通道。
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
B = "B-roll/Landscape video"
AUDIO_END = 591.4  # 配音 591.29s

# (srt_entries, material, in, category, reason)
shots = [
    ([1], f"{B}/Things/Flower/coverr-rain-on-a-red-flower-6463-1080p.mp4", 2.0, "Flower", "'答案早就来了，只是你不喜欢'：雨中红花，答案早已在那里"),
    ([2, 3], f"{B}/People/Drinking/coverr-a-woman-drinking-coffee-from-a-mug-8513-1080p.mp4", 1.0, "Drinking", "'你不是想不明白，只是在等更喜欢的答案'：独酌发呆"),
    ([4, 5], f"{B}/People/Thinking/coverr-friends-looking-on-an-iphone-7587-1080p.mp4", 15.0, "Thinking", "'所以你查资料。问朋友。'：看手机找人问"),
    ([6, 7], f"{B}/City/Street/20242363-uhd_2732_1260_24fps.mp4", 1.0, "Street", "'刷帖子。看别人的经历。'：街头人流，别人的生活"),
    ([8], f"{B}/Art/Sculpture/12045537_1920_1080_30fps.mp4", 3.0, "Sculpture", "'同一件事你想了一遍又一遍'：负载均衡，反复打磨"),
    ([9, 10], f"{B}/People/Dating/coverr-a-guy-gently-stroking-his-girlfriend-s-hair-3750-1080p.mp4", 5.0, "Dating", "'今天觉得应该放下，明天又觉得也许还有机会'：感情摇摆"),
    ([11, 12, 13], f"{B}/City/Subway/coverr-entry-barrier-in-a-subway-station-2104-1080p.mp4", 0.5, "Subway", "'我再等等。等我彻底想明白了，再做决定。'：闸机前等待"),
    ([14, 15], f"{B}/Things/Flower/5235136-hd_1920_1080_25fps.mp4", 8.0, "Flower", "'可一个月过去了。三个月过去了。'：花期流转"),
    ([16], f"{B}/Abstract/Time/16821239_1920_1080_50fps.mp4", 1.0, "Time", "'甚至一年过去了。'：时间递进"),
    ([17, 18], f"{B}/People/Working/coverr-a-woman-laughing-while-working-at-night-in-her-office-6011-1080p.mp4", 6.0, "Working", "'新信息并没有增加多少，你却还在纠结同一个问题'：深夜还在想"),
    ([19], f"{B}/Things/Flower/12745682-hd_1920_1080_24fps.mp4", 1.5, "Flower", "'你真正缺的，也许已经不是答案了'：花已开"),
    ([20], f"{B}/Abstract/Time/14147958_1920_1080_30fps.mp4", 0.3, "Time", "'而是你不喜欢那个已经出现的答案'：题眼句，时间停顿"),
    ([21], f"{B}/City/Street/coverr-a-man-on-a-scooter-2122-1080p.mp4", 3.0, "Street", "'这种事情，在感情里特别常见'：过渡"),
    ([22, 23], f"{B}/People/Dating/8626905-hd_2048_1080_25fps.mp4", 20.0, "Dating", "'你明明知道一段关系已经不合适了。同样的问题反复出现。'：两人同处"),
    ([24, 25], f"{B}/People/Drinking/6831306-hd_1920_1080_30fps.mp4", 10.0, "Drinking", "'同样的话说了一遍又一遍。你越来越累。'：对坐疲惫"),
    ([26, 27], f"{B}/People/Physical training/4867626-hd_1920_1080_25fps.mp4", 0.3, "Physical training", "'对方也没有真的改变。可你还是会告诉自己。'：原地训练"),
    ([28, 29, 30, 31], f"{B}/People/Dating/coverr-a-loving-boyfriend-surprise-his-beautiful-girlfriend-with-a-gift-4057-1080p.mp4", 2.0, "Dating", "'再等等。也许状态不好。也许忙完这阵。也许再磨合一下。'：自我安慰的礼物"),
    ([32, 33], f"{B}/Art/Sculpture/15212893-hd_1920_1080_25fps.mp4", 1.0, "Sculpture", "'你以为在认真经营，其实只是在推迟承认'：负载均衡，精雕细琢"),
    ([34], f"{B}/Things/Flower/13404672_1920_1080_30fps.mp4", 4.0, "Flower", "'这段关系，也许真的不合适'：花落"),
    ([35, 36], f"{B}/People/Working/coverr-a-young-woman-drinking-a-hot-beverage-in-the-workplace-6414-1080p.mp4", 2.0, "Working", "'更明显的是，你喜欢一个并不喜欢你的人。其实没那么难判断。'：负载均衡，独坐"),
    ([37, 38], f"{B}/People/Dating/coverr-texting-by-the-marina-1080p.mp4", 3.0, "Dating", "'他很少主动找你。你不找他，他也不会找你。'：码头等消息"),
    ([39], f"{B}/Technology/Computer/16348844_1920_1080_25fps.mp4", 1.0, "Computer", "'回复越来越敷衍'：屏幕消息"),
    ([40], f"{B}/People/Drinking/8828286-hd_1920_1080_25fps.mp4", 1.0, "Drinking", "'你的情绪，对他来说似乎也没那么重要'：独酌冷落"),
    ([41, 42, 43], f"{B}/Art/Sculpture/8148654-hd_1920_1080_30fps.mp4", 4.0, "Sculpture", "'这些信号你不是看不见。恰恰相反。你看得非常清楚。'：负载均衡，凝视"),
    ([44, 45, 46], f"{B}/People/Dating/coverr-elegant-lady-texting-in-evening-cityscape-1080p.mp4", 3.0, "Dating", "'但你开始给它们找解释。他几个小时没回。可能真的很忙。'：夜里等回复"),
    ([47, 48, 49], f"{B}/Business/Company/6339906-hd_1920_1080_30fps.mp4", 1.0, "Company", "'他说话有点冷。也许只是不会表达。最近明显没那么主动。'：负载均衡，职场压力"),
    ([50], f"{B}/People/Drinking/6760632-hd_1920_1080_25fps.mp4", 11.0, "Drinking", "'可能只是压力太大'：独酌开脱"),
    ([51, 52, 53], f"{B}/People/Dating/coverr-loving-couple-kissing-on-a-date-free-stock-video-coverr-6097-1080p.mp4", 0.2, "Dating", "'只要对方偶尔主动一次。偶尔关心一句。偶尔给一点回应。'：偶尔的亲昵"),
    ([54], f"{B}/Things/Flower/13907999_1920_1080_60fps.mp4", 5.0, "Flower", "'前面所有的冷淡，好像一下又能被解释掉'：花又开了"),
    ([55, 56, 57], f"{B}/People/Dating/coverr-a-guy-taking-photos-of-his-girlfriend-in-a-park-on-his-smartphone-7498-1080p.mp4", 4.0, "Dating", "'你看。他还是在乎我的。但很多时候。'：镜头里的他"),
    ([58, 59, 60], f"{B}/Art/Sculpture/6711444-hd_1920_1080_25fps.mp4", 5.0, "Sculpture", "'你不是在给他的冷漠找借口，你是在给自己的幻想找借口'：负载均衡，幻想的构造"),
    ([61, 62], f"{B}/Things/Flower/16105711_1920_1080_25fps.mp4", 1.0, "Flower", "'你就不用承认那个最不想承认的事实。他可能就是没有那么喜欢你。'：花低头"),
    ([63, 64, 65, 66], f"{B}/Nature/Ocean/coverr-a-picnic-near-the-ocean-6972-1080p.mp4", 2.0, "Ocean", "'只要你承认它，你就必须失去一些东西。你失去的不只是这个人。'：海边空旷"),
    ([67, 68], f"{B}/Art/Music/7352118-uhd_2560_1080_25fps.mp4", 8.0, "Music", "'你还会失去那个也许有一天他会喜欢我的可能。失去那些偷偷想象过的未来。'：负载均衡，想象的旋律"),
    ([69], f"{B}/Art/Sculpture/20606541-hd_1920_1080_24fps.mp4", 4.0, "Sculpture", "'失去一个你在脑子里生活过很多遍，却从没真正发生过的人生'：负载均衡，未发生的人生"),
    ([70, 71, 72], f"{B}/People/Working/coverr-a-woman-laughing-while-working-at-night-in-her-office-6011-1080p.mp4", 1.0, "Working", "'所以你会继续等。继续猜。继续分析。'：深夜分析"),
    ([73], f"{B}/Technology/Computer/15029080_1920_1080_25fps.mp4", 10.0, "Computer", "'把一个本来很简单的信号，解释得越来越复杂'：屏幕信息"),
    ([74, 75], f"{B}/Things/Flower/5005943-hd_1280_720_30fps.mp4", 8.0, "Flower", "'不是因为现实真的那么复杂。而是因为简单的那个答案，太难接受了。'：花田"),
    ([76, 77, 78], f"{B}/People/Dating/8626905-hd_2048_1080_25fps.mp4", 18.0, "Dating", "'你有没有发现。这种时候，人还特别喜欢去问别人。你问第一个朋友。'：找朋友"),
    ([79, 80], f"{B}/City/Street/coverr-stylish-woman-walking-down-the-street-1557-1080p.mp4", 14.0, "Street", "'他说，算了吧。你不满意。'：街头走开"),
    ([81, 82, 83], f"{B}/People/Drinking/6831306-hd_1920_1080_30fps.mp4", 1.0, "Drinking", "'你又去问第二个。他说，我觉得他对你没什么意思。你还是不满意。'：对坐倾诉"),
    ([84, 85], f"{B}/People/Walking/14332511_1920_1080_30fps.mp4", 1.0, "Walking", "'于是你继续问第三个，第四个，第五个。直到终于有一个人告诉你。'：一个个问下去"),
    ([86, 87], f"{B}/Abstract/Time/16821233_1920_1080_50fps.mp4", 9.0, "Time", "'再等等吧。也许还有机会。'：等待的时间"),
    ([88, 89], f"{B}/People/Drinking/coverr-a-woman-drinking-coffee-from-a-mug-8513-1080p.mp4", 1.0, "Drinking", "'你一下就舒服了。可你这时候真的在寻找建议吗。'：负载均衡，自欺的松弛"),
    ([90], f"{B}/Art/Sculpture/9028971-hd_1920_1080_30fps.mp4", 10.0, "Sculpture", "'还是你一直在找一个人，批准你继续相信自己想相信的东西'：负载均衡"),
    ([91, 92, 93], f"{B}/Art/Music/19057431-hd_1920_1080_25fps.mp4", 3.0, "Music", "'这可能是很多长期纠结里，一个非常隐蔽的真相。我们嘴上说。我还没想明白。'：负载均衡"),
    ([94, 95], f"{B}/Things/Flower/5235136-hd_1920_1080_25fps.mp4", 1.0, "Flower", "'但有时候，我们真正想说的是。我还没找到一个我愿意接受的答案。'：花蕾"),
    ([96, 97], f"{B}/City/Subway/15937776_1920_1080_25fps.mp4", 9.0, "Subway", "'这件事当然不只发生在感情里。一份工作也是一样。'：地铁通勤"),
    ([98], f"{B}/People/Working/coverr-walking-to-work-office-corridor-stroll-1080p.mp4", 4.0, "Working", "'你可能早就知道，它继续做下去，大概率也不会变成你想要的样子'：办公室走廊"),
    ([99, 100, 101], f"{B}/People/Drinking/7314896-hd_1920_1080_25fps.mp4", 1.0, "Drinking", "'没有成长。没有期待。每天都在消耗。'：负载均衡，独酌消耗"),
    ([102, 103, 104, 105], f"{B}/Business/Company/6804659-hd_2048_1080_25fps.mp4", 1.0, "Company", "'可你还是会告诉自己。再待半年看看。也许换个领导就好了。也许年底能升职。'：办公室期待"),
    ([106], f"{B}/Business/Stock/16425935_1920_1080_50fps.mp4", 14.0, "Stock", "'也许明年行情会变'：行情"),
    ([107, 108, 109, 110], f"{B}/Business/Finance/coverr-a-trader-making-a-call-with-his-smartphone-1580-1080p.mp4", 5.0, "Finance", "'你是在等待新的信息。还是在等待一个转机，替你免掉那个痛苦的决定'：等电话"),
    ([111, 112, 113], f"{B}/Art/Sculpture/12045537_1920_1080_30fps.mp4", 0.5, "Sculpture", "'有时候更难承认的，甚至不是。我做不到。而是。'：负载均衡，转折"),
    ([114], f"{B}/Things/Flower/coverr-rain-on-a-red-flower-6463-1080p.mp4", 5.5, "Flower", "'我已经不想要了'：雨中花，呼应开场"),
    ([115, 116, 117, 118], f"{B}/People/Walking/12084451_1280_720_30fps.mp4", 42.0, "Walking", "'有些目标，你追了很多年。一开始是真的想要。可后来，人已经变了。想法也变了。'：长路"),
    ([119, 120], f"{B}/Things/Car/20153917-hd_1920_1080_24fps.mp4", 17.0, "Car", "'你慢慢发现，它好像没那么重要了。可你不敢停。'：继续行驶"),
    ([121], f"{B}/People/Physical training/4859764-hd_1920_1080_25fps.mp4", 22.0, "Physical training", "'因为你已经投入了太多'：投入的汗水"),
    ([122, 123, 124], f"{B}/Business/Finance/coverr-many-old-coins-fall-on-a-heap-4647-1080p.mp4", 1.0, "Finance", "'时间。精力。钱。'：硬币堆叠"),
    ([125], f"{B}/Art/Sculpture/9028971-hd_1920_1080_30fps.mp4", 17.0, "Sculpture", "'甚至你对自己的想象，都围绕着它建立起来了'：负载均衡，塑像=自我形象"),
    ([126, 127, 128], f"{B}/People/Physical training/4859447-hd_1920_1080_25fps.mp4", 1.0, "Physical training", "'所以你继续往前跑。不是因为终点还值得去。而是因为已经跑了太远'：继续跑"),
    ([129, 130, 131], f"{B}/Art/Music/10222213-hd_2048_1080_25fps.mp4", 20.0, "Music", "'真正难的不是没有答案，而是承认答案以后，你必须接受失去'：负载均衡，长音乐句"),
    ([132], f"{B}/Art/Sculpture/12045537_1920_1080_30fps.mp4", 7.0, "Sculpture", "'你要失去幻想'：负载均衡"),
    ([133, 134], f"{B}/People/Dating/8626905-hd_2048_1080_25fps.mp4", 23.7, "Dating", "'结束一段不合适的关系。你要失去那些依然舍不得的部分'：两人的余温"),
    ([135, 136], f"{B}/People/Working/coverr-coworkers-arrive-at-the-office-9520-1080p.mp4", 1.0, "Working", "'离开一份工作。你要失去现在的稳定'：办公室日常"),
    ([137, 138], f"{B}/Business/Finance/5981296-hd_2048_1080_25fps.mp4", 8.0, "Finance", "'放弃一个追了很多年的目标。你要接受过去的投入未必按原来的想象得到回报'：账本"),
    ([139, 140], f"{B}/City/Skyline/mixkit-clouds-covering-the-mountains-4695-hd-ready.mp4", 8.0, "Skyline", "'于是人就会本能地寻找一种第三种答案。能不能既离开，又什么都不失去'：负载均衡，云雾中的第三条路"),
    ([141], f"{B}/Abstract/Rise/12504761_1920_1080_30fps.mp4", 30.0, "Rise", "'既重新开始，又保证过去完全没有浪费'：上升幻想"),
    ([142], f"{B}/People/Drinking/7423558-hd_1920_1080_30fps.mp4", 1.0, "Drinking", "'既得到新的生活，又保留旧生活里所有的安全感'：负载均衡，旧日安稳"),
    ([143], f"{B}/Things/Flower/5005943-hd_1280_720_30fps.mp4", 17.0, "Flower", "'既接受他现在不喜欢我，又保留以后他一定会喜欢我的可能'：花的可能"),
    ([144, 145, 146], f"{B}/Abstract/Time/13622711_1920_1080_30fps.mp4", 52.0, "Time", "'可很多真正重要的问题。根本没有这种选项。你不是还没找到。'：时间否定"),
    ([147, 148, 149], f"{B}/Things/Flower/2895664-hd_1920_1080_24fps.mp4", 40.0, "Flower", "'它压根就不存在。所以你才会一直纠结。因为你真正想要的，可能不是一个更好的答案'：花田长镜"),
    ([150], f"{B}/Business/Finance/coverr-crypto-wallet-5213-1080p.mp4", 3.0, "Finance", "'而是一个不用付代价的答案'：代价"),
    ([151, 152], f"{B}/People/Drinking/6760632-hd_1920_1080_25fps.mp4", 1.0, "Drinking", "'但现实很少给这种答案。有些人不会因为你足够真诚，就突然喜欢上你'：负载均衡，独酌清醒"),
    ([153], f"{B}/City/Street/coverr-a-street-on-a-rainy-day-3463-1080p.mp4", 9.5, "Street", "'有些关系不会因为你再忍半年，就自动变得合适'：雨天"),
    ([154], f"{B}/People/Walking/7580172-hd_1920_1080_25fps.mp4", 11.0, "Walking", "'有些路也不会因为你已经走了很远，就突然通向你真正想去的地方'：走远路"),
    ([155], f"{B}/Things/Flower/13404672_1920_1080_30fps.mp4", 0.5, "Flower", "'有些答案，也不会因为你等得足够久，就变成你喜欢的样子'：等不开的花"),
    ([156, 157], f"{B}/People/Studying/coverr-student-turning-the-pages-of-a-marketing-book-2770-1080p.mp4", 1.0, "Studying", "'但这里其实有一个很实用的判断方法。以后，如果你发现自己对同一件事已经反复想了很久'：翻开书"),
    ([158, 159], f"{B}/Technology/Computer/6804117-hd_2048_1080_25fps.mp4", 1.0, "Computer", "'先别急着再问一个人。也别急着再搜一篇文章'：停下搜索"),
    ([160, 161], f"{B}/City/Street/coverr-stylish-woman-walking-down-the-street-1557-1080p.mp4", 0.5, "Street", "'先问自己三个问题。第一个。'：街头停步"),
    ([162, 163, 164], f"{B}/Business/Finance/5981296-hd_2048_1080_25fps.mp4", 0.5, "Finance", "'最近还有新的信息进入吗。如果答案是有。那你继续思考，当然有意义'：查账"),
    ([165, 166, 167], f"{B}/Abstract/Time/7033607-hd_1920_1080_25fps.mp4", 1.0, "Time", "'但如果这件事已经几个月没有出现真正的新信息。你只是把旧的信息翻来覆去地重新排列。那就问第二个问题'：循环"),
    ([168, 169, 170, 171, 172, 173], f"{B}/City/Skyline/mixkit-ocean-waves-bursting-on-the-shore-of-the-coast-4078-hd-ready.mp4", 15.0, "Skyline", "'假设接下来一个月，什么都不会发生。没有转机。没有奇迹。没有新的信号。没有谁突然改变。那我会怎么选'：负载均衡，海岸空镜"),
    ([174, 175], f"{B}/Nature/Sky/14365680_1920_1080_30fps.mp4", 1.0, "Sky", "'这个问题会把很多你一直寄托在未来的幻想暂时拿掉。很多时候，答案会突然变得清楚'：云开"),
    ([176, 177, 178], f"{B}/Art/Sculpture/8148654-hd_1920_1080_30fps.mp4", 0.5, "Sculpture", "'然后是第三个问题。也是最重要的一个。如果这个答案已经不会改变。'：负载均衡，凝视"),
    ([179], f"{B}/Things/Flower/coverr-man-holding-a-red-flower-8060-1080p.mp4", 8.0, "Flower", "'我最不愿意接受的，到底是什么'：手中红花"),
    ([180], f"{B}/People/Drinking/7314877-hd_1920_1080_25fps.mp4", 4.8, "Drinking", "'是舍不得'：独酌"),
    ([181], f"{B}/People/Physical training/6116178-hd_1920_1080_25fps.mp4", 0.3, "Physical training", "'是不甘心'：发力"),
    ([182], f"{B}/Business/Finance/6266254-hd_1920_1080_25fps.mp4", 10.5, "Finance", "'是沉没成本'：账本"),
    ([183], f"{B}/City/Subway/coverr-woman-waiting-for-the-subway-3892-1080p.mp4", 0.5, "Subway", "'是害怕重新开始'：站台"),
    ([184], f"{B}/City/Street/coverr-girl-in-the-street-6721-1080p.mp4", 12.5, "Street", "'是害怕别人怎么看'：街头目光"),
    ([185, 186], f"{B}/People/Thinking/coverr-friends-looking-on-an-iphone-7587-1080p.mp4", 0.5, "Thinking", "'还是你不愿意承认。那个曾经无比确定的自己，也可能判断错了'：面对屏幕"),
    ([187, 188, 189, 190], f"{B}/Art/Music/8568656-hd_2048_1080_25fps.mp4", 12.0, "Music", "'到这里，问题才真正开始变得有价值。因为你终于不再围着答案打转。你开始看见。到底是什么东西，让你一直不肯接受答案'：负载均衡，顿悟如旋律"),
    ([191, 192, 193, 194], f"{B}/Abstract/Rise/7310193-uhd_2732_1318_30fps.mp4", 0.5, "Rise", "'有些人想了几年都没有想明白的问题。可能在某一刻突然就通了。不是因为他终于获得了一条神奇的新信息。而是因为他终于愿意承认'：光亮"),
    ([195], f"{B}/Things/Flower/coverr-purple-flowers-in-the-grass-6561-1080p.mp4", 4.0, "Flower", "'自己其实早就知道了什么'：草地上早已开着的花"),
    ([196, 197, 198], f"{B}/People/Thinking/coverr-writing-a-poem-outdoors-3529-1080p.mp4", 0.5, "Thinking", "'所以以后，当你又开始对一件事情反复纠结。别只问。我是不是还没想明白'：停笔"),
    ([199], f"{B}/Abstract/Time/15100537_1920_1080_30fps.mp4", 0.5, "Time", "'换一个问题'：流转"),
    ([200], f"{B}/City/Street/coverr-man-taking-a-selfie-on-the-street-at-night-6100-1080p.mp4", 9.5, "Street", "'我到底是真的不知道'：夜色自问"),
    ([201], f"{B}/People/Drinking/7314896-hd_1920_1080_25fps.mp4", 16.0, "Drinking", "'还是我只是不愿意接受'：独酌"),
    ([202, 203, 204], f"{B}/Business/Finance/coverr-giving-cashier-a-credit-card-9719-1080p.mp4", 5.0, "Finance", "'因为有些问题。真正需要停止的，不是思考。而是你和现实之间，那场永远不会结束的讨价还价'：柜台结账=讨价还价"),
    ([205, 206, 207], f"{B}/Abstract/Time/16821233_1920_1080_50fps.mp4", 0.5, "Time", "'到了最后。有些答案之所以让人痛苦。不是因为它来得太晚'：时间"),
    ([208], f"{B}/People/Thinking/mixkit-face-of-a-young-pensive-woman-on-a-purple-background-33353-hd-ready.mp4", 0.5, "Thinking", "'恰恰是因为'：面部特写，停顿"),
    ([209], f"{B}/Things/Flower/coverr-rain-on-a-red-flower-6463-1080p.mp4", 0.5, "Flower", "'它早就来了'：雨中红花第三次出现，首尾闭环"),
    ([210], f"{B}/Nature/Sky/coverr-ski-resort-2528-1080p.mp4", 7.0, "Sky", "'只是'：空镜留白一拍"),
    ([211], f"{B}/Nature/Ocean/coverr-a-picnic-near-the-ocean-6972-1080p.mp4", 3.0, "Ocean", "'你不喜欢'：海边收尾，余韵"),
]


def load_srt():
    srt = (ROOT / "projects/demo007/subtitle/demo007.srt").read_text(encoding="utf-8")
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
    out = ["project: demo007", "audio_duration: 591.29",
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
    p = ROOT / "projects/demo007/timeline.yaml"
    p.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"[ok] {p}  {len(shots)} 镜头，覆盖 0–{AUDIO_END}s")


if __name__ == "__main__":
    main()
