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


ROOT = Path(__file__).resolve().parents[3]
L1_ENTRY = ROOT / "00_工程总控" / "工程执行层" / "L1工程" / "L1运行入口.py"


def main() -> int:
    parser = argparse.ArgumentParser(description="已废止正文检测入口：兼容转发到 L1 工程。")
    parser.add_argument("--chapter", default=None, help="待检测正文 Markdown 路径。")
    parser.add_argument("--run-id", default=None, help="报告编号。")
    parser.add_argument("--project", default="《修士死后，都会变成秘境》", help="项目名。")
    parser.add_argument("--standard-mode", default="PRODUCTION", choices=["PRODUCTION", "CANDIDATE_TEST"], help="标准加载模式。")
    args, extra = parser.parse_known_args()

    run_id = args.run_id or "正文检测_COMPAT"
    cmd = [
        sys.executable,
        str(L1_ENTRY),
        "--run-id",
        run_id,
        "--project",
        args.project,
        "--standard-mode",
        args.standard_mode,
        *extra,
    ]
    if args.chapter:
        cmd.extend(["--chapter", args.chapter])

    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(cmd, cwd=str(ROOT), text=True, encoding="utf-8", capture_output=True, env=env)
    payload = {
        "deprecated": True,
        "warning": "正文检测入口已废止，当前调用已转发到 L1 工程。",
        "forwarded_to": str(L1_ENTRY.relative_to(ROOT)),
        "returncode": result.returncode,
        "stdout": (result.stdout or "").strip(),
        "stderr": (result.stderr or "").strip(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
