# alarkive-studio
Alarkive Studio — An automated content-to-video production pipeline for Alark知新录

## 日常使用流程

用户提供「文章标题 + 正文」即可，agent 负责整理文稿、标题排版和高亮词，并完成
配音、同步字幕、语义选片、标题帧、预览版/正式版视频、竖版/横版双封面。
总控脚本为 `scripts/produce.py`，下面的命令与中间选片环节由 agent 执行。

### 中英文制作

中文沿用当前规则：默认晓伊、云希备选，现有排版、素材轮换和成品规格保持不变。
未标记语言的历史项目按中文处理。用户可指定「中文版」「英文版」或「中英文各一版」，
agent 将每种语言放入独立项目，例如 `demo009` 与 `demo009_en`，避免音频、字幕、
时间线和封面相互覆盖。已有项目不能通过 `--language` 改成另一语言。

英文新项目的入口：

```powershell
.\.venv\Scripts\python.exe scripts/produce.py --id demo009_en --language en `
    --script path/to/english_script.txt `
    --title-lines "Make the World" "Your Playground" --highlight Playground
```

英文文稿由 agent 根据原意改写成适合朗读的自然英文；这条命令本身不自动翻译。
自然段保存为 `narration.txt`，字幕稿按完整单词和语义短句分行，通常每条约 6–12 个词，
以实际两行排版检查为准。正文中的数字和缩写要核对实际朗读与词时间戳。
英文字幕或标题放不下时会报错，先缩短标题或拆分字幕稿，再重新生成配音/字幕。

英文语言配置位于 `config/languages/en.yaml`。用户试听后偏好 Andrew 男声，
新英文项目默认 `en-US-AndrewNeural`，Ava 女声（`en-US-AvaNeural`）作为备选和
合成失败时的回退；两者使用正常语速（`+0%`）。英文标题、字幕按完整
单词换行，底部使用英文品牌文案；共享原有 Logo、配色、素材库和合成流程。
英文封面预览保存到 `preview/en/`，不替换中文预览。

中英文配音时长及语句边界不同，字幕和时间线需分别生成、校验。同一主题可以参考
相同的视觉构思；镜头时长按对应语言音轨重排，素材复用仍遵循下方的历史区间规则。
续跑英文项目时只需 `--id demo009_en`，流水线会读取该项目已保存的语言配置。

### 配音偏好

- 中文新项目默认使用晓伊（`zh-CN-XiaoyiNeural`），用户偏好其甜美的声音。
- 云希（`zh-CN-YunxiNeural`）保留为男声备选，也是晓伊合成失败时的回退音色。
- 两者都使用试听时的正常语速（`+0%`）。
- 中文项目中，用户说「这篇用云希」时，agent 先完成 init，再在首次 voice 步骤前将本期
  `meta.yaml` 的 `voice_primary` 设为 `zh-CN-YunxiNeural`，`voice_fallback` 设为
  `zh-CN-XiaoyiNeural`。未指定时沿用默认晓伊。
- 已有项目继续读取各自的配音配置；新的默认值只用于建项，不批量修改历史成品。
- 新一期可将自然段朗读稿保存为 `narration.txt`，在 `meta.yaml` 的 `script` 下设置
  `narration_file: narration.txt`。`script.file` 仍保存按字幕断行的正文；两者正文必须
  一致，标点和断行可以不同。未设置该字段的旧项目仍按原稿朗读。

### 运行环境（Windows PowerShell）

项目使用 `.venv` 中的 Python。`requirements.txt` 固定已验证的直接依赖版本，
其中 edge-tts 7.3.1 已用于成功生成试听；原系统的 7.2.8 曾出现合成接口 403。
由 agent 在首次准备环境时执行：

```powershell
python -m venv --system-site-packages .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

该环境复用机器已有的其他依赖，新安装的版本写入项目 `.venv`。后续统一使用
`.\.venv\Scripts\python.exe` 启动总控，其子步骤会继承同一个解释器。

### 第一步：建项并跑到选片前

```powershell
.\.venv\Scripts\python.exe scripts/produce.py --id demo002 --script path/to/script.txt `
    --title-lines "第一行" "第二行" "第三行" --highlight 关键词
```

依次执行 init（建 `projects/demo002/` 结构与 meta.yaml）→ voice（edge-tts 配音
mp3/wav + WordBoundary 同步字幕 srt）→ title（标题帧）→ timeline（先确保全库共享
素材索引 `assets/broll_index.json` 存在，然后发现 timeline.yaml 不存在，
打印选片指引并以退出码 2 停止——这是本步的正常终点）。

### 中间环节：语义选片（由 agent 完成，非自动规则）

agent 阅读 `projects/demo002/script.txt` 与素材索引，逐期语义判断选片，
手工编写 `projects/demo002/timeline.yaml`（格式与校验规则参照
`projects/demo001/timeline.yaml`：每镜头含 seq/start/end/duration/material/
in/out/category/srt_entries/reason，切换点对齐字幕边界、in/out 不超素材时长、
无连续同类别、总覆盖不短于配音时长）。

选片前先看候选素材缩略图，核实实际画面；目录分类只作筛选参考。写完时间线后，
再检查本期与历史各期的素材 in/out 区间，避免重复使用相同片段。近期素材如因语义
不可替代而复用，在镜头 `reason` 中记录原因。

选片策略（在语义贴合的基础上）：

1. **冷素材优先**：写 timeline 前先跑 `python scripts/broll_usage.py` 查看历史
   使用记录；同等语义下优先近期未使用的素材
   （`--cold 类别名` 可列出该类别下从未使用的素材）。
2. **强制轮换**：近两期已用过的素材，除非语义无可替代，否则换同类别其他素材；
   复用同一素材时必须取与历史不相交的 in/out 区段。
3. **负载均衡**：每期约 10–15% 的镜头（60 个镜头的片子即 6–9 个）走
   "非语义镜头"通道——从冷门类别按画面氛围/节奏挑选，放在过渡句、抽象句、
   排比句等语义宽容的位置，让常用话题选不到的素材也有出场机会。

### 第二步：跑完全部剩余步骤

```powershell
.\.venv\Scripts\python.exe scripts/produce.py --id demo002
```

流水线校验 timeline.yaml（覆盖连续、in/out 合法、字段齐全），通过后先自动生成
选片清单 `selected_broll/shot_list.jpg`（每镜头代表帧缩略图网格，供看图审片），
再执行 render（预览版 + 正式版 + 9:16 包装版视频）→ cover（双封面），
结尾打印产物总结表。

交付前对成品做完整音视频解码检查，并抽查开头、转折、长字幕和片尾。字幕应与
朗读稿正文一致，时间不能越过音频结尾；特别留意标点单独换行、裁字和片尾缺失。

### 主题插画封面

需要更强的主题表达时，agent 可用绘图工具在基础双封面上继续制作插画版：
先查看本期的横版和竖版，沿用深绿、奶油白、金色及 Alark 品牌元素，
再从正文提炼一个清晰的视觉意象。先完成横版，再以横版画风和原竖版为参考，
单独设计竖版构图。生成后核对中文标题、品牌文字、缩略图可读性及实际图像尺寸。

插画版另存为 `output/cover_horizontal_v2.png` 与 `output/cover_vertical_v2.png`；
已有 v2 时递增版本号。将参考图片、完整提示词、实际尺寸及检查结果记录在本期
`cover_v2_generation.json` 中。总控脚本的 `cover` 步骤仍生成基础 v1，插画版由 agent
调用绘图工具完成，供交付时选择。

### 断点续跑与常用选项

- 默认幂等：已有产物的步骤打印 `SKIP (exists)` 直接跳过（TTS 时间戳不可复现，
  配音存在绝不会重跑）。
- `--force`：强制重跑所有步骤。
- 已有项目只修改字幕排版或镜头时，用 `--only render --force` 重导视频。
  修改配音或文稿后，还需先同步字幕与时间线；避免直接用无 `--only` 的 `--force`
  重建项目，覆盖本期的配置。
- `--until STEP` / `--only STEP`：只跑到 / 只跑某一步
  （init / voice / title / timeline / render / cover）。

### 各步骤对应脚本与产物

| 步骤 | 脚本 | 主要产物（projects/\<id\>/ 下） |
|---|---|---|
| init | produce.py 内建 | title.txt、script.txt、meta.yaml |
| voice | scripts/make_voice.py | voice/\<id\>.mp3、.wav、subtitle/\<id\>.srt |
| title | scripts/render_title_frame.py | output/title_frame.png |
| timeline | agent 编写 + produce.py 校验 | timeline.yaml；素材索引为全库共享 assets/broll_index.json |
| shotlist | scripts/make_shot_list.py | selected_broll/shot_list.jpg（选片缩略图网格审片） |
| render | scripts/render_video.py | output/\<id\>_preview.mp4（540×664）、output/\<id\>_v1.mp4（1080×1328） |
| cover | scripts/generate_cover.py | output/cover_vertical_v1.png（1080×1440）、output/cover_horizontal_v1.png（1920×1080） |
