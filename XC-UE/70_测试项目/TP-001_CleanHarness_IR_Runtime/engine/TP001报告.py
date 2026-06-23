from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path


def summarize(checks: list) -> dict[str, object]:
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


def write_reports(run_id: str, candidate: Path, checks: list, root: Path) -> tuple[Path, Path]:
    reports_dir = root / "reports"
    reports_dir.mkdir(exist_ok=True)
    summary = summarize(checks)
    payload = {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "project": "TP-001",
        "candidate": str(candidate.relative_to(root)),
        "summary": summary,
        "checks": [asdict(check) for check in checks],
    }

    json_path = reports_dir / f"{run_id}.json"
    md_path = reports_dir / f"{run_id}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# {run_id} 工程运行报告",
        "",
        "- 项目：TP-001",
        f"- 候选正文：`{candidate.relative_to(root)}`",
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
