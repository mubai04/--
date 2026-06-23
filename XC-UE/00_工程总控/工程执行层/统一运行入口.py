#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "公共组件"))

from 流水线运行 import 运行流水线
from 标准加载器 import 候选试验模式, 生产模式
from 安全路径 import resolve_inside_root, safe_id
from 工程异常 import 输入错误


TARGETS = {
    "L1": {
        "cwd": ROOT,
        "entry": ROOT / "00_工程总控" / "工程执行层" / "L1工程" / "L1运行入口.py",
        "default_run_id": "L1_RUN-UNIFIED",
        "forward_args": {"chapter", "project", "standard_mode"},
    },
    "正文检测": {
        "cwd": ROOT,
        "entry": ROOT / "00_工程总控" / "工程执行层" / "正文检测" / "正文检测运行入口.py",
        "default_run_id": "正文检测_COMPAT-RUN-UNIFIED",
        "forward_args": {"chapter", "project", "standard_mode"},
    },
    "TP-001": {
        "cwd": ROOT / "70_测试项目" / "TP-001_CleanHarness_IR_Runtime",
        "entry": ROOT / "70_测试项目" / "TP-001_CleanHarness_IR_Runtime" / "engine" / "TP001运行入口.py",
        "default_run_id": "ENGINE-RUN-UNIFIED-TP001",
        "forward_args": set(),
    },
    "L2": {
        "cwd": ROOT,
        "entry": ROOT / "00_工程总控" / "工程执行层" / "L2工程" / "L2运行入口.py",
        "default_run_id": "L2_RUN-UNIFIED",
        "forward_args": {"standard_mode"},
    },
    "L3": {
        "cwd": ROOT,
        "entry": ROOT / "00_工程总控" / "工程执行层" / "L3工程" / "L3运行入口.py",
        "default_run_id": "L3_RUN-UNIFIED",
        "forward_args": {"standard_mode"},
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description="XC-UE 统一工程执行入口。")
    parser.add_argument("--target", required=True, choices=sorted([*TARGETS, "PIPELINE"]), help="运行目标。")
    parser.add_argument("--run-id", default=None, help="报告编号。")
    parser.add_argument("--chapter", default=None, help="PIPELINE 使用的章节正文路径。")
    parser.add_argument("--project", default="未命名项目", help="PIPELINE 使用的项目名。")
    parser.add_argument("--standard-mode", default=候选试验模式, choices=[生产模式, 候选试验模式], help="标准加载模式。")
    args, extra = parser.parse_known_args()

    try:
        chapter_arg = args.chapter
        if chapter_arg:
            chapter_arg = str(resolve_inside_root(ROOT, chapter_arg))
        run_id_arg = safe_id(args.run_id, "run_id") if args.run_id else None
    except 输入错误 as exc:
        print(json.dumps({"error": str(exc), "exit_code": 20}, ensure_ascii=False), file=sys.stderr)
        return 20

    if args.target == "PIPELINE":
        if not chapter_arg:
            print(json.dumps({"error": "PIPELINE 需要 --chapter"}, ensure_ascii=False), file=sys.stderr)
            return 20
        return 运行流水线(Path(chapter_arg), args.project, run_id_arg, args.standard_mode)

    target = TARGETS[args.target]
    forward_args = target["forward_args"]

    if chapter_arg and "chapter" in forward_args:
        extra = ["--chapter", chapter_arg, *extra]
    if args.project != "未命名项目" and "project" in forward_args:
        extra = ["--project", args.project, *extra]
    if "standard_mode" in forward_args:
        extra = ["--standard-mode", args.standard_mode, *extra]

    entry = target["entry"]
    cwd = target["cwd"]
    run_id = run_id_arg or target["default_run_id"]

    if not entry.exists():
        raise FileNotFoundError(f"Missing target entry: {entry}")

    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    cmd = [sys.executable, str(entry), "--run-id", run_id, *extra]
    result = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, env=env)

    payload = {
        "target": args.target,
        "entry": str(entry.relative_to(ROOT)),
        "cwd": str(cwd.relative_to(ROOT)),
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
