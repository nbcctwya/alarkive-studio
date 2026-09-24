# -*- coding: utf-8 -*-
"""Alark 一键生产总控流水线：标题+高亮+正文 -> 配音/字幕/标题帧/(选片)/视频/双封面。

使用方式（配合 agent 语义选片）：
  # 场景1：新项目，建项+配音字幕+标题帧，跑到 timeline 前停下（等 agent 选片）
  python scripts/produce.py --id demo002 --script path/to/script.txt \
      --title-lines "第一行" "第二行" "第三行" --highlight 关键词
  # 场景2：agent 写好 projects/<id>/timeline.yaml 后，跑完全部剩余步骤
  python scripts/produce.py --id demo002

选项：
  --force        强制重跑所有步骤（默认已有产物则跳过，断点续跑）
  --until STEP   只跑到某一步（init/voice/title/timeline/shotlist/render/cover）
  --only STEP    只跑某一步

timeline.yaml 不由本流水线生成：选片是逐期语义判断，由 agent 基于文案与
assets/broll_index.json（全库共享索引）编写；本流水线负责校验并在缺失时以退出码 2 停止。
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
STEPS = ["init", "voice", "title", "timeline", "shotlist", "render", "cover"]
EXIT_NO_TIMELINE = 2


def run(script: str, *script_args: str) -> None:
    cmd = [sys.executable, "-u", str(ROOT / "scripts" / script), *script_args]
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        sys.exit(f"[error] {script} {' '.join(script_args)} 失败，退出码 {r.returncode}")


class Pipeline:
    def __init__(self, args):
        self.pid = args.id
        self.project = ROOT / "projects" / self.pid
        self.args = args
        self.meta_path = self.project / "meta.yaml"

    # ---------------- 工具 ----------------
    def meta(self) -> dict:
        return yaml.safe_load(self.meta_path.read_text(encoding="utf-8"))

    def banner(self, step: str) -> None:
        print(f"\n{'=' * 60}\n  [{step}]\n{'=' * 60}", flush=True)

    @staticmethod
    def skip(msg: str) -> None:
        print(f"  SKIP (exists) {msg}", flush=True)

    # ---------------- 步骤 ----------------
    def step_init(self) -> None:
        a = self.args
        need = [self.project / "title.txt", self.project / "script.txt",
                self.meta_path]
        if all(p.exists() for p in need) and not a.force:
            self.skip("项目结构与关键文件")
            return
        if not a.script or not a.title_lines:
            sys.exit("[error] init 需要 --script 与 --title-lines（项目不存在时）")
        for d in ("voice", "subtitle", "selected_broll", "output"):
            (self.project / d).mkdir(parents=True, exist_ok=True)
        shutil_src = Path(a.script)
        (self.project / "script.txt").write_bytes(shutil_src.read_bytes())
        (self.project / "title.txt").write_text(
            "\n".join(a.title_lines) + "\n", encoding="utf-8")
        highlight = list(a.highlight or [])
        n_par = sum(1 for ln in (self.project / "script.txt")
                    .read_text(encoding="utf-8").splitlines() if ln.strip())
        meta = {
            "id": self.pid,
            "frame_version": "v1.0",
            "created": str(date.today()),
            "title": {"file": "title.txt", "lines": list(a.title_lines),
                      "highlight": highlight,
                      "highlight_color": "#D9AA54", "text_color": "#F3E8D2"},
            "cover": {"highlight": highlight},
            "script": {"file": "script.txt", "paragraph_count": n_par},
            "voice": {"engine": "edge-tts",
                      "voice_primary": "zh-CN-YunjianNeural",
                      "voice_fallback": "zh-CN-YunxiNeural",
                      "voice_used": None, "rate": "-4%",
                      "output_mp3": f"voice/{self.pid}.mp3",
                      "output_wav": f"voice/{self.pid}.wav",
                      "duration_sec": None},
            "subtitle": {"file": f"subtitle/{self.pid}.srt", "entries": None},
            "output": {"title_frame": "output/title_frame.png"},
            "broll": {"selected_dir": "selected_broll/"},
        }
        self.meta_path.write_text(yaml.safe_dump(meta, allow_unicode=True,
                                                 sort_keys=False), encoding="utf-8")
        print(f"  [ok] {self.project}（{n_par} 个非空段落）", flush=True)

    def step_voice(self) -> None:
        m = self.meta()
        vc = m["voice"]
        arts = [self.project / vc["output_mp3"], self.project / vc["output_wav"],
                self.project / m["subtitle"]["file"]]
        if all(p.exists() for p in arts) and not self.args.force:
            self.skip("配音 mp3/wav 与字幕 srt（TTS 时间戳不可复现，不重跑）")
            return
        run("make_voice.py", "--project", str(self.project))

    def step_title(self) -> None:
        out = self.project / self.meta()["output"]["title_frame"]
        if out.exists() and not self.args.force:
            self.skip("标题帧 title_frame.png")
            return
        run("render_title_frame.py", "--project", str(self.project))

    def step_timeline(self) -> None:
        index = ROOT / "assets" / "broll_index.json"  # 全库共享索引（项目无关）
        if not index.exists() or self.args.force:
            run("scan_broll.py", "--output", str(index))
        else:
            self.skip("素材索引 assets/broll_index.json")
        tl = self.project / "timeline.yaml"
        if not tl.exists():
            print(f"""
  [stop] timeline.yaml 不存在，流水线在此停止。
  选片需由 agent 基于文案语义逐期完成：
    1. 阅读 {self.project / 'script.txt'}
    2. 参考素材索引 {index}
    3. 编写 {tl}（格式参照 projects/demo001/timeline.yaml：
       每镜头 seq/start/end/duration/material/in/out/category/srt_entries/reason）
  写好后重新运行：python scripts/produce.py --id {self.pid}
""", flush=True)
            sys.exit(EXIT_NO_TIMELINE)
        self.validate_timeline(tl)

    def validate_timeline(self, tl: Path) -> None:
        m = self.meta()
        audio = float(m["voice"]["duration_sec"] or 0)
        data = yaml.safe_load(tl.read_text(encoding="utf-8"))
        shots = data.get("shots") or []
        if not shots:
            sys.exit("[error] timeline.yaml 无 shots")
        index = json.loads((ROOT / "assets" / "broll_index.json")
                           .read_text(encoding="utf-8"))
        prev_end, errors = 0.0, []
        for i, s in enumerate(shots, 1):
            for k in ("seq", "start", "end", "material", "in", "out", "category"):
                if k not in s:
                    errors.append(f"镜头{i} 缺字段 {k}")
            if abs(s["start"] - prev_end) > 0.05:
                errors.append(f"镜头{i} 起点 {s['start']} 与前一镜头终点 {prev_end} 断开")
            prev_end = s["end"]
            rel = s["material"].split("Landscape video/")[-1]
            mat = index.get(rel)
            if mat is None:
                errors.append(f"镜头{i} 素材不在索引: {rel}")
            elif s["out"] > mat["duration"] + 0.05:
                errors.append(f"镜头{i} out 超出素材时长 {mat['duration']}")
        if audio and prev_end < audio - 0.05:
            errors.append(f"镜头总覆盖 {prev_end}s 不足配音 {audio}s")
        if errors:
            for e in errors:
                print(f"  [ERROR] {e}")
            sys.exit("[error] timeline.yaml 校验失败，请修正后重跑")
        print(f"  [ok] timeline.yaml 校验通过（{len(shots)} 个镜头，"
              f"覆盖至 {prev_end}s）", flush=True)

    def step_shotlist(self) -> None:
        out = self.project / "selected_broll" / "shot_list.jpg"
        if out.exists() and not self.args.force:
            self.skip("选片清单 shot_list.jpg")
            return
        run("make_shot_list.py", "--project", str(self.project))

    def step_render(self) -> None:
        # render_video.py 输出文件名暂为 demo001_*（历史遗留），渲染后归位为 <id>_*
        want = {"preview": self.project / "output" / f"{self.pid}_preview.mp4",
                "final": self.project / "output" / f"{self.pid}_v1.mp4",
                "wrapped": self.project / "output" / f"{self.pid}_wrapped.mp4"}
        legacy = {"preview": self.project / "output" / "demo001_preview.mp4",
                  "final": self.project / "output" / "demo001_v1.mp4",
                  "wrapped": self.project / "output" / "demo001_wrapped.mp4"}
        for mode in ("preview", "final", "wrapped"):
            if want[mode].exists() and not self.args.force:
                self.skip(f"{mode} 版视频")
                continue
            run("render_video.py", "--project", str(self.project), "--mode", mode)
            if not want[mode].exists() and legacy[mode].exists():
                legacy[mode].rename(want[mode])
                print(f"  [ok] 归位 {legacy[mode].name} -> {want[mode].name}",
                      flush=True)

    def step_cover(self) -> None:
        arts = [self.project / "output" / "cover_vertical_v1.png",
                self.project / "output" / "cover_horizontal_v1.png"]
        if all(p.exists() for p in arts) and not self.args.force:
            self.skip("双封面")
            return
        run("generate_cover.py", "--project", str(self.project), "--mode", "both")

    # ---------------- 总结 ----------------
    def summary(self) -> None:
        print(f"\n{'=' * 60}\n  总结  {self.pid}\n{'=' * 60}")
        m = self.meta()
        dur = m["voice"].get("duration_sec")
        rows = [
            ("标题帧", "output/title_frame.png"),
            ("配音 mp3", m["voice"]["output_mp3"]),
            ("配音 wav", m["voice"]["output_wav"]),
            ("字幕 srt", m["subtitle"]["file"]),
            ("timeline", "timeline.yaml"),
            ("预览版视频", f"output/{self.pid}_preview.mp4"),
            ("正式版视频", f"output/{self.pid}_v1.mp4"),
            ("9:16 包装版", f"output/{self.pid}_wrapped.mp4"),
            ("竖版封面", "output/cover_vertical_v1.png"),
            ("横版封面", "output/cover_horizontal_v1.png"),
        ]
        for name, rel in rows:
            p = self.project / rel
            mark = "[ok]" if p.exists() else "[--]"
            print(f"  {mark} {name:<10} {rel}")
        tl = self.project / "timeline.yaml"
        if tl.exists():
            n = len(yaml.safe_load(tl.read_text(encoding="utf-8")).get("shots", []))
            print(f"  镜头数: {n}")
        if dur:
            print(f"  配音/视频时长: {dur:.2f}s ({int(dur // 60)}:{int(dur % 60):02d})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--script", default=None)
    ap.add_argument("--title-lines", nargs="+", default=None)
    ap.add_argument("--highlight", nargs="*", default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--until", choices=STEPS, default=None)
    ap.add_argument("--only", choices=STEPS, default=None)
    args = ap.parse_args()

    pipe = Pipeline(args)
    for step in STEPS:
        if args.only and step != args.only:
            continue
        pipe.banner(step)
        t0 = time.time()
        getattr(pipe, f"step_{step}")()
        print(f"  [{step}] 耗时 {time.time() - t0:.1f}s", flush=True)
        if args.until == step:
            print(f"\n[stop] 已到 --until {step}")
            break
    pipe.summary()


if __name__ == "__main__":
    sys.exit(main())
