from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from conftest import ROOT
from 退出码 import ExitCode


pytestmark = [pytest.mark.integration, pytest.mark.security]


执行层 = ROOT / "00_工程总控" / "工程执行层"
PRODUCTION_MODE_NOT_ELIGIBLE = 26


def _写章节(path: Path) -> None:
    path.write_text(
        "# A05 生产资格样本\n\n"
        "门外的雨声忽然停了。沈照把账册压进衣襟，听见巷尾传来第三次铜铃。\n\n"
        "他没有回头，只把灯吹灭。黑暗里有人低声问，今夜谁先付代价。\n",
        encoding="utf-8",
    )


def _写失败包(path: Path) -> None:
    payload = {
        "schema_version": "xcue.failure-packet/1.0",
        "pipeline_run_id": "pytest-a05",
        "stage_run_id": "pytest-a05-L1",
        "status": "SCREENING_REJECT",
        "failure_count": 1,
        "items": [
            {
                "闸门": "L1-03",
                "名称": "入口弱",
                "状态": "风险",
                "说明": "入口弱",
                "证据": [],
                "严重级别": "warning",
                "失败类型": "入口弱",
                "候选模块": "L2-05",
                "回流验收位置": "L1-02",
                "修复方向": "pytest A05",
            }
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _写L2报告(path: Path) -> None:
    payload = {
        "schema_version": "xcue.l2-report/1.0",
        "pipeline_run_id": "pytest-a05",
        "stage_run_id": "pytest-a05-L2",
        "status": "COMPLETED",
        "run_id": "pytest-L2",
        "输入文件": str(path.parent / "失败包.json"),
        "输入数量": 1,
        "方法声明": "pytest",
        "标准校验问题": [],
        "回流校验问题": [],
        "接口判断": [],
        "修复单": [
            {
                "修复单类型": "L2 能力修复单",
                "来源闸门": "L1-02",
                "接收模块": "L2-05",
                "输入问题": "入口弱",
                "主失败类型": "入口弱",
                "次失败类型": "",
                "修复动作": "规划修复动作",
                "修复产物": "任务包",
                "验收问题": "回到 L1-02 复验",
                "回流位置": "L1-02",
                "是否需要其他L2辅助": "否",
                "是否需要回L15重路由": "否",
                "最终状态": "回原闸门复验",
                "rule_id": "L2-05:pytest-rule",
                "rule_version": "pytest",
                "rule_hash": "a" * 64,
            }
        ],
        "阻断项": [],
        "复验目标": [],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _run(cmd: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        env=env,
        timeout=30,
    )


def _assert_production_rejected(result: subprocess.CompletedProcess[str], stage: str, out_dir: Path) -> None:
    assert result.returncode == PRODUCTION_MODE_NOT_ELIGIBLE, result.stdout + result.stderr
    payload = json.loads(result.stderr)
    assert payload["error_code"] == "PRODUCTION_MODE_NOT_ELIGIBLE"
    assert payload["reason"] == "CANDIDATE_RULES_ONLY"
    assert payload["requested_mode"] == "PRODUCTION"
    assert payload["effective_mode"] is None
    assert payload["eligible"] is False
    assert payload["entrypoint"] == stage
    assert payload["error"]["details"]["entrypoint"] == stage
    assert not list(out_dir.glob("*.json")) if out_dir.exists() else True


def 测试A05_直接L1生产模式候选规则被统一拒绝(root_case, test_io_env):
    chapter = root_case / "chapter.md"
    out_dir = root_case / "L1"
    _写章节(chapter)

    result = _run(
        [
            sys.executable,
            str(执行层 / "L1工程" / "L1运行入口.py"),
            "--chapter",
            str(chapter),
            "--out-dir",
            str(out_dir),
            "--run-id",
            "pytest-A05-L1-" + uuid.uuid4().hex[:8],
            "--standard-mode",
            "PRODUCTION",
        ],
        test_io_env,
    )

    _assert_production_rejected(result, "L1", out_dir)


def 测试A05_直接L2生产模式候选规则被统一拒绝(root_case, test_io_env):
    packet = root_case / "失败包.json"
    out_dir = root_case / "L2"
    _写失败包(packet)

    result = _run(
        [
            sys.executable,
            str(执行层 / "L2工程" / "L2运行入口.py"),
            "--failure-packet",
            str(packet),
            "--out-dir",
            str(out_dir),
            "--run-id",
            "pytest-A05-L2-" + uuid.uuid4().hex[:8],
            "--pipeline-run-id",
            "pytest-a05",
            "--stage-run-id",
            "pytest-a05-L2",
            "--standard-mode",
            "PRODUCTION",
        ],
        test_io_env,
    )

    _assert_production_rejected(result, "L2", out_dir)


def 测试A05_直接L3生产模式候选规则被统一拒绝(root_case, test_io_env):
    l2_report = root_case / "修复报告.json"
    out_dir = root_case / "L3"
    _写L2报告(l2_report)

    result = _run(
        [
            sys.executable,
            str(执行层 / "L3工程" / "L3运行入口.py"),
            "--l2-report",
            str(l2_report),
            "--project-harness",
            str(ROOT / "70_测试项目" / "TP-001_CleanHarness_IR_Runtime"),
            "--out-dir",
            str(out_dir),
            "--run-id",
            "pytest-A05-L3-" + uuid.uuid4().hex[:8],
            "--pipeline-run-id",
            "pytest-a05",
            "--stage-run-id",
            "pytest-a05-L3",
            "--standard-mode",
            "PRODUCTION",
        ],
        test_io_env,
    )

    _assert_production_rejected(result, "L3", out_dir)


def 测试A05_统一流水线生产拒绝使用统一错误码(root_case):
    chapter = ROOT / "70_测试项目" / "TP-001_CleanHarness_IR_Runtime" / "chapters" / "ch01.md"
    run_id = "pytest-A05-PIPE-" + uuid.uuid4().hex[:8]

    result = _run(
        [
            sys.executable,
            str(执行层 / "统一运行入口.py"),
            "--target",
            "PIPELINE",
            "--chapter",
            str(chapter),
            "--project",
            "pytest",
            "--run-id",
            run_id,
            "--standard-mode",
            "PRODUCTION",
        ]
    )

    assert result.returncode == PRODUCTION_MODE_NOT_ELIGIBLE, result.stdout + result.stderr
    payload = json.loads(result.stderr)
    assert payload["error_code"] == "PRODUCTION_MODE_NOT_ELIGIBLE"
    assert payload["reason"] == "CANDIDATE_RULES_ONLY"
    assert not (ROOT / "运行记录" / run_id).exists()


def 测试A05_TP001统一入口生产模式也被统一拒绝():
    result = _run(
        [
            sys.executable,
            str(执行层 / "统一运行入口.py"),
            "--target",
            "TP-001",
            "--run-id",
            "pytest-A05-TP001-" + uuid.uuid4().hex[:8],
            "--standard-mode",
            "PRODUCTION",
        ]
    )

    assert result.returncode == PRODUCTION_MODE_NOT_ELIGIBLE, result.stdout + result.stderr
    payload = json.loads(result.stderr)
    assert payload["error_code"] == "PRODUCTION_MODE_NOT_ELIGIBLE"
    assert payload["reason"] == "CANDIDATE_RULES_ONLY"
    assert payload["entrypoint"] == "TP-001"


def 测试A05_非生产模式不被生产资格阻断(root_case, test_io_env):
    packet = root_case / "失败包.json"
    out_dir = root_case / "L2"
    _写失败包(packet)

    result = _run(
        [
            sys.executable,
            str(执行层 / "L2工程" / "L2运行入口.py"),
            "--failure-packet",
            str(packet),
            "--out-dir",
            str(out_dir),
            "--run-id",
            "pytest-A05-L2-CAND-" + uuid.uuid4().hex[:8],
            "--pipeline-run-id",
            "pytest-a05",
            "--stage-run-id",
            "pytest-a05-L2",
            "--standard-mode",
            "CANDIDATE_TEST",
        ],
        test_io_env,
    )

    assert result.returncode in {int(ExitCode.OK), int(ExitCode.BLOCKED)}, result.stderr
    payload = json.loads(result.stdout)
    assert payload["standard_mode"] == "CANDIDATE_TEST"
    assert payload["experimental_standard"] is True
    assert list(out_dir.glob("*.json"))


def 测试A05_伪造实验字段不能提升生产资格(root_case, test_io_env):
    packet = root_case / "失败包.json"
    out_dir = root_case / "L2"
    _写失败包(packet)
    env = {**test_io_env, "XCUE_EXPERIMENTAL_STANDARD": "false"}

    result = _run(
        [
            sys.executable,
            str(执行层 / "L2工程" / "L2运行入口.py"),
            "--failure-packet",
            str(packet),
            "--out-dir",
            str(out_dir),
            "--run-id",
            "pytest-A05-L2-FORGE-" + uuid.uuid4().hex[:8],
            "--pipeline-run-id",
            "pytest-a05",
            "--stage-run-id",
            "pytest-a05-L2",
            "--standard-mode",
            "PRODUCTION",
        ],
        env,
    )

    _assert_production_rejected(result, "L2", out_dir)
