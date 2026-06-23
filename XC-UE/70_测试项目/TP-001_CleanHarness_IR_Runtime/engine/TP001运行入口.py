#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINE_DIR = Path(__file__).resolve().parent


def load_module(name: str, filename: str):
    path = ENGINE_DIR / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


模型 = load_module("TP001模型", "TP001模型.py")
读取 = load_module("TP001读取", "TP001读取.py")
检查 = load_module("检查", "检查.py")
报告 = load_module("TP001报告", "TP001报告.py")


def main() -> int:
    parser = argparse.ArgumentParser(description="运行 TP-001 工程检查。")
    parser.add_argument(
        "--candidate",
        default="chapters/_candidates/ch01_candidate_RUN-20260621-002.md",
        help="候选正文路径，项目根目录相对路径。",
    )
    parser.add_argument(
        "--rules",
        default="engine/rules_tp001_v0.1.json",
        help="规则配置路径，项目根目录相对路径。",
    )
    parser.add_argument("--run-id", default=None, help="报告编号。")
    args = parser.parse_args()

    candidate = (ROOT / args.candidate).resolve()
    rules_path = (ROOT / args.rules).resolve()
    if ROOT not in candidate.parents:
        raise ValueError("Candidate must stay inside TP-001 project root.")
    if ROOT not in rules_path.parents:
        raise ValueError("Rules file must stay inside TP-001 project root.")

    run_id = args.run_id or "ENGINE-RUN-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    rules = 读取.load_rules(rules_path)
    sources = 读取.load_sources(candidate)
    checks = 检查.run_checks(sources, candidate, rules, ROOT, 模型.Check)
    json_path, md_path = 报告.write_reports(run_id, candidate, checks, ROOT)
    summary = 报告.summarize(checks)

    print(json.dumps({
        "run_id": run_id,
        "status": summary["status"],
        "json_report": str(json_path.relative_to(ROOT)),
        "markdown_report": str(md_path.relative_to(ROOT)),
    }, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
