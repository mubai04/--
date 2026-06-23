from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIR = ROOT / "00_工程总控" / "整改基线"
BASELINE_PATH = BASELINE_DIR / "BASELINE_2026-06-23.json"
EVIDENCE_PATH = BASELINE_DIR / "PYTEST_EVIDENCE_2026-06-23.json"

EXCLUDED_DIR_NAMES = {
    ".git",
    ".pytest_cache",
    "__pycache__",
}

EXCLUDED_PREFIXES = (
    "00_工程总控/整改基线/",
    "90_日志/",
    "99_归档_不要索引/",
    "测试/回归样本/",
)

COUNTED_SUFFIXES = {
    ".py": "python",
    ".md": "markdown",
    ".json": "json",
}

RULE_PREFIXES = (
    "10_L0_总图层/",
    "20_L1_闸门层/",
    "30_L1.5_路由矩阵层/",
    "40_L2_正式能力层/",
    "50_L3_执行协议层/",
)


def _portable_rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _is_excluded(path: Path) -> bool:
    rel = _portable_rel(path)
    if any(part in EXCLUDED_DIR_NAMES for part in path.relative_to(ROOT).parts):
        return True
    return rel.startswith(EXCLUDED_PREFIXES)


def _iter_project_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if path.is_file() and not _is_excluded(path):
            files.append(path)
    return sorted(files, key=_portable_rel)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_hash(files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        rel = _portable_rel(path)
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(_sha256(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def _count_files(files: list[Path]) -> dict[str, int]:
    counts = {name: 0 for name in COUNTED_SUFFIXES.values()}
    for path in files:
        key = COUNTED_SUFFIXES.get(path.suffix.lower())
        if key:
            counts[key] += 1
    return counts


def _rule_hashes(files: list[Path]) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in files:
        rel = _portable_rel(path)
        if path.suffix.lower() == ".md" and rel.startswith(RULE_PREFIXES):
            result[rel] = _sha256(path)
    return result


def _test_files(files: list[Path]) -> list[str]:
    result: list[str] = []
    for path in files:
        name = path.name
        if path.suffix.lower() != ".py":
            continue
        if name.startswith("测试") or name.startswith("test_") or name.endswith("_test.py"):
            result.append(_portable_rel(path))
    return result


def build_baseline() -> dict[str, object]:
    files = _iter_project_files()
    test_files = _test_files(files)
    return {
        "schema_version": "xcue.m0.static-baseline/1.0",
        "baseline_id": "M0-01-BASELINE-2026-06-23",
        "created_date": "2026-06-23",
        "timezone": "Asia/Shanghai",
        "generation_policy": {
            "deterministic": True,
            "does_not_run_pytest": True,
            "runtime_test_results_are_external_evidence": _portable_rel(EVIDENCE_PATH),
            "excluded_from_effective_project_inventory": sorted(
                [*EXCLUDED_DIR_NAMES, *EXCLUDED_PREFIXES]
            ),
        },
        "file_counts": _count_files(files),
        "effective_project_file_count": len(files),
        "effective_project_manifest_sha256": _manifest_hash(files),
        "key_entry_paths": {
            "unified_entry": "00_工程总控/工程执行层/统一运行入口.py",
            "pipeline_entry": "00_工程总控/工程执行层/流水线运行.py",
            "l1_entry": "00_工程总控/工程执行层/L1工程/L1运行入口.py",
            "l2_entry": "00_工程总控/工程执行层/L2工程/L2运行入口.py",
            "l3_entry": "00_工程总控/工程执行层/L3工程/L3运行入口.py",
            "tp001_entry": "70_测试项目/TP-001_CleanHarness_IR_Runtime/engine/TP001运行入口.py",
        },
        "tests_static_inventory": {
            "pytest_testpaths": ["测试", "00_工程总控/工程执行层/测试"],
            "test_file_count": len(test_files),
            "test_files": test_files,
            "standard_command": "python -m pytest -q",
            "m0_regression_command": "python -m pytest -q 测试/回归样本/test_confirmed_failures.py",
            "runtime_result_excluded_from_static_baseline": True,
        },
        "known_failure_facts": [
            {
                "id": "R1-P0-01",
                "source": "XC-UE_全量整改计划书_v1.1_2026-06-23.md",
                "description": "统一入口公开 TP-001 必然失败路径；M0-02 固化为 strict xfail 回归样本。",
            }
        ],
        "reported_historical_pass_command": {
            "source": "XC-UE_深度盘查报告_2026-06-23.md",
            "command": "python -m pytest -q",
            "result_not_embedded": True,
        },
        "rule_file_hashes": _rule_hashes(files),
        "version_control": {
            "git_commit": _git_commit(),
            "fallback_archive_sha256": None if _git_commit() else _manifest_hash(files),
            "note": "当前目录不是 git 仓库时使用有效工程文件清单哈希作为归档指纹。",
        },
        "unconfirmed_environment_items": [
            "无 git 仓库元数据，无法确认 commit。",
            "运行耗时与通过数不写入静态基线，仅保存在独立 pytest 证据文件。",
        ],
    }


def main() -> int:
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    payload = build_baseline()
    BASELINE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(BASELINE_PATH.relative_to(ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
