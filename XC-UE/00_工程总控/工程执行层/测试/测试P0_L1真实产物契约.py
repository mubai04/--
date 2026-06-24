from __future__ import annotations

import json
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from conftest import ROOT, 执行层
from 结构校验 import 按结构文件校验
from 退出码 import ExitCode
from 标准加载器 import 候选试验模式


pytestmark = pytest.mark.integration

SCHEMA_DIR = 执行层 / "公共组件" / "结构定义"
L1_ENTRY = 执行层 / "L1工程" / "L1运行入口.py"
L2_ENTRY = 执行层 / "L2工程" / "L2运行入口.py"
UNIFIED_ENTRY = 执行层 / "统一运行入口.py"
CHAPTER = ROOT / "70_测试项目" / "TP-001_CleanHarness_IR_Runtime" / "chapters" / "ch01.md"


def _run(args: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=str(cwd),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        env=env,
        timeout=60,
    )


def _run_l1(out_dir: Path, run_id: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return _run(
        [
            str(L1_ENTRY),
            "--chapter",
            str(CHAPTER),
            "--project",
            "TP-001",
            "--run-id",
            run_id,
            "--out-dir",
            str(out_dir),
            "--standard-mode",
            候选试验模式,
        ],
        env=env,
    )


def test_p0_l1_real_report_and_failure_packet_match_schemas(tmp_path: Path, test_io_env: dict[str, str]):
    out_dir = tmp_path / "第一层"
    run_id = "pytest-p0-l1-" + uuid.uuid4().hex[:8]

    result = _run_l1(out_dir, run_id, test_io_env)

    assert result.returncode in {int(ExitCode.OK), int(ExitCode.GATE_REJECTED), int(ExitCode.REVIEW_REQUIRED)}, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    report = json.loads(Path(payload["report_json"]).read_text(encoding="utf-8"))
    packet = json.loads(Path(payload["failure_packet"]).read_text(encoding="utf-8"))
    按结构文件校验(report, SCHEMA_DIR / "第一层报告结构.json", "真实 L1 检测报告")
    按结构文件校验(packet, SCHEMA_DIR / "失败包结构.json", "真实 L1 失败包")
    assert report["pipeline_run_id"]
    assert report["stage_run_id"]
    assert packet["pipeline_run_id"]
    assert packet["stage_run_id"]


def test_p0_real_l1_failure_packet_is_consumed_by_l2(tmp_path: Path, test_io_env: dict[str, str]):
    l1_dir = tmp_path / "第一层"
    l2_dir = tmp_path / "第二层"
    run_id = "pytest-p0-l1-l2-" + uuid.uuid4().hex[:8]
    l1 = _run_l1(l1_dir, run_id, test_io_env)
    assert l1.returncode in {int(ExitCode.OK), int(ExitCode.GATE_REJECTED), int(ExitCode.REVIEW_REQUIRED)}, l1.stdout + l1.stderr
    packet = Path(json.loads(l1.stdout)["failure_packet"])

    l2 = _run(
        [
            str(L2_ENTRY),
            "--failure-packet",
            str(packet),
            "--run-id",
            run_id + "-L2",
            "--out-dir",
            str(l2_dir),
            "--pipeline-run-id",
            run_id,
            "--stage-run-id",
            run_id + "-L2",
            "--standard-mode",
            候选试验模式,
        ],
        env=test_io_env,
    )

    assert l2.returncode != int(ExitCode.INPUT_INVALID), l2.stdout + l2.stderr


def test_p0_tp001_candidate_pipeline_does_not_stop_at_failed_schema():
    run_id = "pytest-p0-pipe-" + uuid.uuid4().hex[:8]
    result = _run(
        [
            str(UNIFIED_ENTRY),
            "--target",
            "PIPELINE",
            "--project",
            "TP-001",
            "--run-id",
            run_id,
            "--standard-mode",
            候选试验模式,
        ]
    )

    manifest_path = ROOT / "运行记录" / run_id / "流水线清单.json"
    assert manifest_path.exists(), result.stdout + result.stderr
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["final_status"] != "FAILED_SCHEMA"
    assert any(stage["stage"] == "L2" for stage in manifest["stages"])
