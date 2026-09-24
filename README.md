# alarkive-studio
Alarkive Studio — An automated content-to-video production pipeline for Alark知新录

## 日常使用流程

提供「文章标题 + 高亮词 + 正文 txt」，一条流水线产出：配音、同步字幕、标题帧、
预览版/正式版视频、竖版/横版双封面。总控脚本为 `scripts/produce.py`。

### 第一步：建项并跑到选片前

```bash
python scripts/produce.py --id demo002 --script path/to/script.txt \
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

### 第二步：跑完全部剩余步骤

```bash
python scripts/produce.py --id demo002
```

流水线校验 timeline.yaml（覆盖连续、in/out 合法、字段齐全），通过后先自动生成
选片清单 `selected_broll/shot_list.jpg`（每镜头代表帧缩略图网格，供看图审片），
再执行 render（预览版 + 正式版 + 9:16 包装版视频）→ cover（双封面），
结尾打印产物总结表。

### 断点续跑与常用选项

- 默认幂等：已有产物的步骤打印 `SKIP (exists)` 直接跳过（TTS 时间戳不可复现，
  配音存在绝不会重跑）。
- `--force`：强制重跑所有步骤。
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
