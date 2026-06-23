from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_PATH = ROOT / "00_工程总控" / "整改基线" / "PYTEST_EVIDENCE_2026-06-23.json"


def main() -> int:
    command = ["python", "-m", "pytest", "-q"]
    started_at = datetime.now().astimezone()
    start = time.perf_counter()
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    finished_at = datetime.now().astimezone()
    duration = time.perf_counter() - start
    payload = {
        "schema_version": "xcue.m0.pytest-evidence/1.0",
        "evidence_id": "M0-PYTEST-2026-06-23",
        "command": "python -m pytest -q",
        "cwd": str(ROOT),
        "started_at": started_at.isoformat(timespec="seconds"),
        "finished_at": finished_at.isoformat(timespec="seconds"),
        "duration_seconds": round(duration, 3),
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "static_baseline_policy": "not embedded in BASELINE_2026-06-23.json",
    }
    EVIDENCE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"returncode": result.returncode, "duration_seconds": round(duration, 3)}, ensure_ascii=False))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
