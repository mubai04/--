from __future__ import annotations

import json
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from conftest import ROOT
from 退出码 import ExitCode


pytestmark = pytest.mark.integration


def _写失败包(path: Path, items: list[dict]) -> None:
    payload = {
        "schema_version": "xcue.failure-packet/1.0",
        "pipeline_run_id": "pytest-pipeline",
        "stage_run_id": "pytest-pipeline-L1",
        "status": "SCREENING_REJECT",
        "failure_count": len(items),
        "items": items,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _失败项(name: str, failure_type: str, candidate: str, return_gate: str = "L1-02") -> dict:
    return {
        "闸门": "L1-03",
        "名称": name,
        "状态": "风险",
        "说明": name,
        "证据": [],
        "严重级别": "warning",
        "失败类型": failure_type,
        "候选模块": candidate,
        "回流验收位置": return_gate,
        "修复方向": "pytest 修复方向",
    }


def _运行L2(packet: Path, out_dir: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "00_工程总控" / "工程执行层" / "L2工程" / "L2运行入口.py"),
            "--failure-packet",
            str(packet),
            "--run-id",
            "pytest-L2-" + uuid.uuid4().hex[:8],
            "--out-dir",
            str(out_dir),
            "--pipeline-run-id",
            "pytest-pipeline",
            "--stage-run-id",
            "pytest-pipeline-L2",
            "--standard-mode",
            "CANDIDATE_TEST",
        ],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        env=env,
        timeout=30,
    )


def 测试L2普通失败生成修复单(root_case, test_io_env):
    packet = root_case / "失败包.json"
    out_dir = root_case / "第二层"
    _写失败包(packet, [_失败项("入口弱", "入口弱", "L2-05")])
    result = _运行L2(packet, out_dir, test_io_env)
    assert result.returncode == int(ExitCode.OK), result.stderr
    report = json.loads((out_dir / "修复报告.json").read_text(encoding="utf-8"))
    assert len(report["修复单"]) == 1
    assert report["阻断项"] == []


def 测试L2普通失败加派生复验项不全局阻断(root_case, test_io_env):
    packet = root_case / "失败包.json"
    out_dir = root_case / "第二层"
    _写失败包(
        packet,
        [
            _失败项("入口弱", "入口弱", "L2-05"),
            _失败项("投入意愿前置", "投入意愿不足", "回L1-02", "L1-02"),
        ],
    )
    result = _运行L2(packet, out_dir, test_io_env)
    assert result.returncode == int(ExitCode.OK), result.stderr
    report = json.loads((out_dir / "修复报告.json").read_text(encoding="utf-8"))
    assert len(report["修复单"]) == 1
    assert report["阻断项"] == []
    assert report["复验目标"][0]["最终状态"] == "派生复验"


def 测试L2只有派生复验项合法NOOP(root_case, test_io_env):
    packet = root_case / "失败包.json"
    out_dir = root_case / "第二层"
    _写失败包(packet, [_失败项("投入意愿前置", "投入意愿不足", "回L1-02", "L1-02")])
    result = _运行L2(packet, out_dir, test_io_env)
    assert result.returncode == int(ExitCode.OK), result.stderr
    report = json.loads((out_dir / "修复报告.json").read_text(encoding="utf-8"))
    assert report["修复单"] == []
    assert report["阻断项"] == []
    assert len(report["复验目标"]) == 1


def 测试L2真实越界仍然阻断(root_case, test_io_env):
    packet = root_case / "失败包.json"
    out_dir = root_case / "第二层"
    _写失败包(packet, [_失败项("运营越界", "外部运营", "外部运营层")])
    result = _运行L2(packet, out_dir, test_io_env)
    assert result.returncode == int(ExitCode.BLOCKED)
    report = json.loads((out_dir / "修复报告.json").read_text(encoding="utf-8"))
    assert report["阻断项"]
