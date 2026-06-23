#!/usr/bin/env python3
"""TP-001 minimal engineering runner.

This runner turns the Markdown file network into a small executable loop:
read declared sources, run deterministic gate checks, and write reports.
It does not edit IR, chapters, tests, or system-layer files.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Check:
    gate: str
    name: str
    status: str
    evidence: str
    severity: str = "info"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def nonspace_len(text: str) -> int:
    return len(re.findall(r"\S", text))


def has_any(text: str, terms: Iterable[str]) -> bool:
    return any(term in text for term in terms)


def has_all(text: str, terms: Iterable[str]) -> bool:
    return all(term in text for term in terms)


def status_from_bool(value: bool) -> str:
    return "pass" if value else "fail"


def load_rules(path: Path) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"Missing rules file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_sources(candidate: Path) -> dict[str, str]:
    sources = {
        "manifest": ROOT / "MANIFEST_文件权限与真源表.md",
        "ir00": ROOT / "IR" / "IR-00_项目索引.md",
        "ir01": ROOT / "IR" / "IR-01_立项卡.md",
        "ir02": ROOT / "IR" / "IR-02_世界约束.md",
        "ir03": ROOT / "IR" / "IR-03_角色动机表.md",
        "ir04": ROOT / "IR" / "IR-04_事件链.md",
        "ir05": ROOT / "IR" / "IR-05_章节目标表.md",
        "ir06": ROOT / "IR" / "IR-06_读者预期表.md",
        "ir07": ROOT / "IR" / "IR-07_发布状态表.md",
        "ir08": ROOT / "IR" / "IR-08_状态快照.md",
        "ir99": ROOT / "IR" / "IR-99_输入完整性检查.md",
        "candidate": candidate,
        "formal_ch01": ROOT / "chapters" / "ch01.md",
    }
    missing = [str(path.relative_to(ROOT)) for path in sources.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required files: " + ", ".join(missing))
    return {name: read_text(path) for name, path in sources.items()}


def match_terms(text: str, terms: list[str], mode: str) -> bool:
    if mode == "all":
        return has_all(text, terms)
    if mode == "any":
        return has_any(text, terms)
    raise ValueError(f"Unsupported rule mode: {mode}")


def run_checks(sources: dict[str, str], candidate_path: Path, rules: dict[str, object]) -> list[Check]:
    checks: list[Check] = []
    candidate = sources["candidate"]
    all_ir = "\n".join(sources[name] for name in sources if name.startswith("ir"))

    checks.append(Check(
        "ENGINE",
        "candidate_exists",
        status_from_bool(candidate_path.exists()),
        str(candidate_path.relative_to(ROOT)),
    ))
    checks.append(Check(
        "ENGINE",
        "formal_ch01_not_overwritten",
        status_from_bool("在这里写第一章正文。" in sources["formal_ch01"]),
        "formal chapters/ch01.md still contains placeholder text",
    ))
    checks.append(Check(
        "ENGINE",
        "images_not_truth_source",
        status_from_bool("图片" in sources["manifest"] and "不是真源" in sources["manifest"]),
        "MANIFEST states image assets are expression layer, not truth source",
    ))

    for term in rules["ir_terms"]:
        checks.append(Check(
            "IR",
            f"contains_{term}",
            status_from_bool(term in all_ir),
            f"term={term}",
        ))

    count = nonspace_len(candidate)
    length_rule = rules["candidate_length"]
    min_len = int(length_rule["min_nonspace_chars"])
    max_len = int(length_rule["max_nonspace_chars"])
    length_ok = min_len <= count <= max_len
    checks.append(Check(
        str(length_rule["gate"]),
        str(length_rule["name"]),
        status_from_bool(length_ok),
        f"nonspace_chars={count}; expected={min_len}..{max_len}",
        "error" if not length_ok else "info",
    ))

    for rule in rules["text_gates"]:
        terms = list(rule["terms"])
        mode = str(rule.get("mode", "any"))
        ok = match_terms(candidate, terms, mode)
        evidence = f"mode={mode}; terms=" + " / ".join(terms)
        checks.append(Check(str(rule["gate"]), str(rule["name"]), status_from_bool(ok), evidence, "error" if not ok else "info"))

    forbidden = {
        "legacy_as_input": "_legacy_root_inputs",
        "auto_merge_formal": "自动覆盖 `chapters/ch01.md`",
    }
    checks.append(Check(
        "BOUNDARY",
        "candidate_declares_no_auto_overwrite",
        status_from_bool("不得自动覆盖 `chapters/ch01.md`" in candidate),
        "candidate header declares no formal overwrite",
    ))
    for name, term in forbidden.items():
        # References in the header are allowed when used as prohibition, not as input.
        ok = term not in candidate or "不得自动覆盖" in candidate
        checks.append(Check("BOUNDARY", name, status_from_bool(ok), f"term={term}"))

    return checks


def summarize(checks: list[Check]) -> dict[str, object]:
    failed = [check for check in checks if check.status != "pass"]
    by_gate: dict[str, dict[str, int]] = {}
    for check in checks:
        gate = by_gate.setdefault(check.gate, {"pass": 0, "fail": 0})
        gate[check.status] = gate.get(check.status, 0) + 1
    return {
        "status": "pass" if not failed else "fail",
        "total": len(checks),
        "failed": len(failed),
        "by_gate": by_gate,
    }


def write_reports(run_id: str, candidate: Path, checks: list[Check]) -> tuple[Path, Path]:
    reports_dir = ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)
    summary = summarize(checks)
    payload = {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "project": "TP-001",
        "candidate": str(candidate.relative_to(ROOT)),
        "summary": summary,
        "checks": [asdict(check) for check in checks],
    }

    json_path = reports_dir / f"{run_id}.json"
    md_path = reports_dir / f"{run_id}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# {run_id} 工程运行报告",
        "",
        f"- 项目：TP-001",
        f"- 候选正文：`{candidate.relative_to(ROOT)}`",
        f"- 总状态：{summary['status']}",
        f"- 检查数：{summary['total']}",
        f"- 失败数：{summary['failed']}",
        "",
        "## Gate Summary",
        "",
        "| Gate | Pass | Fail |",
        "|---|---:|---:|",
    ]
    for gate, counts in summary["by_gate"].items():
        lines.append(f"| {gate} | {counts.get('pass', 0)} | {counts.get('fail', 0)} |")
    lines.extend(["", "## Checks", "", "| Gate | Check | Status | Evidence |", "|---|---|---|---|"])
    for check in checks:
        evidence = check.evidence.replace("|", "/")
        lines.append(f"| {check.gate} | {check.name} | {check.status} | {evidence} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run TP-001 engineering checks.")
    parser.add_argument(
        "--candidate",
        default="chapters/_candidates/ch01_candidate_RUN-20260621-002.md",
        help="Candidate chapter path relative to project root.",
    )
    parser.add_argument("--run-id", default=None, help="Report id. Defaults to timestamped id.")
    parser.add_argument(
        "--rules",
        default="engine/rules_tp001_v0.1.json",
        help="Rule config path relative to project root.",
    )
    args = parser.parse_args()

    candidate = (ROOT / args.candidate).resolve()
    if ROOT not in candidate.parents:
        raise ValueError("Candidate must stay inside TP-001 project root.")
    rules_path = (ROOT / args.rules).resolve()
    if ROOT not in rules_path.parents:
        raise ValueError("Rules file must stay inside TP-001 project root.")

    run_id = args.run_id or "ENGINE-RUN-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    rules = load_rules(rules_path)
    sources = load_sources(candidate)
    checks = run_checks(sources, candidate, rules)
    json_path, md_path = write_reports(run_id, candidate, checks)
    summary = summarize(checks)
    print(json.dumps({
        "run_id": run_id,
        "status": summary["status"],
        "json_report": str(json_path.relative_to(ROOT)),
        "markdown_report": str(md_path.relative_to(ROOT)),
    }, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
