from __future__ import annotations

import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from conftest import ROOT
from 退出码 import ExitCode
from 项目加载器 import 加载项目


pytestmark = pytest.mark.integration


ENTRY = ROOT / "00_工程总控" / "工程执行层" / "统一运行入口.py"
CHAPTER = ROOT / "70_测试项目" / "TP-001_CleanHarness_IR_Runtime" / "chapters" / "ch01.md"
L3_ENTRY = ROOT / "00_工程总控" / "工程执行层" / "L3工程" / "L3运行入口.py"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ENTRY), *args],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=30,
    )


def _registry(path: Path, *, default_project: str = "TP-001", projects: dict | None = None) -> Path:
    payload = {
        "schema_version": "xcue.project-registry/1.0",
        "default_project": default_project,
        "projects": projects
        if projects is not None
        else {
            "TP-001": {
                "project_root": "70_测试项目/TP-001_CleanHarness_IR_Runtime",
            }
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _stderr_payload(result: subprocess.CompletedProcess[str]) -> dict:
    return json.loads(result.stderr)


def _write_l2_report(path: Path) -> None:
    payload = {
        "schema_version": "xcue.l2-report/1.0",
        "pipeline_run_id": "pytest-loader",
        "stage_run_id": "pytest-loader-L2",
        "status": "COMPLETED",
        "run_id": "pytest-loader-L2",
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


def 测试默认项目和显式TP001流水线输入无效行为一致且不创建运行记录():
    default_run = "pytest-loader-default-" + uuid.uuid4().hex[:8]
    explicit_run = "pytest-loader-explicit-" + uuid.uuid4().hex[:8]
    base = [
        "--target",
        "PIPELINE",
        "--chapter",
        str(CHAPTER),
        "--standard-mode",
        "PRODUCTION",
    ]
    default_result = _run([*base, "--run-id", default_run])
    explicit_result = _run([*base, "--project", "TP-001", "--run-id", explicit_run])

    assert default_result.returncode == explicit_result.returncode == int(ExitCode.NO_PRODUCTION_RULESET)
    assert not (ROOT / "运行记录" / default_run).exists()
    assert not (ROOT / "运行记录" / explicit_run).exists()


def 测试L3未指定Harness时默认加载TP001项目(tmp_path: Path, test_io_env: dict[str, str]):
    l2_report = tmp_path / "第二层" / "修复报告.json"
    out_dir = tmp_path / "第三层"
    l2_report.parent.mkdir(parents=True)
    _write_l2_report(l2_report)
    result = subprocess.run(
        [
            sys.executable,
            str(L3_ENTRY),
            "--l2-report",
            str(l2_report),
            "--run-id",
            "pytest-loader-L3-" + uuid.uuid4().hex[:8],
            "--out-dir",
            str(out_dir),
            "--pipeline-run-id",
            "pytest-loader",
            "--stage-run-id",
            "pytest-loader-L3",
            "--standard-mode",
            "CANDIDATE_TEST",
        ],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        env=test_io_env,
        timeout=30,
    )
    assert result.returncode == int(ExitCode.OK), result.stderr
    report = json.loads((out_dir / "任务包.json").read_text(encoding="utf-8"))
    assert report["任务单"][0]["ProjectHarness根"] == "70_测试项目/TP-001_CleanHarness_IR_Runtime"


def 测试第二项目只改注册表即可被Loader加载(tmp_path: Path):
    project_root = ROOT / "运行记录" / ("pytest-TEST-002-" + uuid.uuid4().hex[:8])
    try:
        for name in ["IR", "chapters", "logs"]:
            (project_root / name).mkdir(parents=True)
        registry = _registry(
            tmp_path / "projects.json",
            default_project="TEST-002",
            projects={
                "TEST-002": {
                    "project_root": project_root.relative_to(ROOT).as_posix(),
                }
            },
        )

        project = 加载项目(ROOT, "TEST-002", registry)

        assert project.project_id == "TEST-002"
        assert project.project_root == project_root.resolve()
        assert project.relative_project_root.startswith("运行记录/pytest-TEST-002-")
    finally:
        if project_root.exists():
            shutil.rmtree(project_root)


def 测试未知项目返回结构化INPUT_INVALID且不创建运行记录():
    run_id = "pytest-loader-unknown-" + uuid.uuid4().hex[:8]
    result = _run(
        [
            "--target",
            "PIPELINE",
            "--chapter",
            str(CHAPTER),
            "--project",
            "UNKNOWN",
            "--run-id",
            run_id,
        ]
    )
    assert result.returncode == int(ExitCode.INPUT_INVALID)
    payload = _stderr_payload(result)
    assert payload["error_code"] == "INPUT_INVALID"
    assert not (ROOT / "运行记录" / run_id).exists()


def 测试缺失项目目录返回结构化INPUT_INVALID且不创建运行记录(tmp_path: Path):
    registry = _registry(
        tmp_path / "projects.json",
        projects={"TP-001": {"project_root": "70_测试项目/DOES_NOT_EXIST"}},
    )
    run_id = "pytest-loader-missing-" + uuid.uuid4().hex[:8]
    result = _run(
        [
            "--target",
            "PIPELINE",
            "--chapter",
            str(CHAPTER),
            "--run-id",
            run_id,
            "--project-registry",
            str(registry),
        ]
    )
    assert result.returncode == int(ExitCode.INPUT_INVALID)
    payload = _stderr_payload(result)
    assert payload["error_code"] == "INPUT_INVALID"
    assert not (ROOT / "运行记录" / run_id).exists()


def 测试项目根越界返回结构化INPUT_INVALID且不创建运行记录(tmp_path: Path):
    registry = _registry(
        tmp_path / "projects.json",
        projects={"TP-001": {"project_root": "../outside"}},
    )
    run_id = "pytest-loader-escape-" + uuid.uuid4().hex[:8]
    result = _run(
        [
            "--target",
            "PIPELINE",
            "--chapter",
            str(CHAPTER),
            "--run-id",
            run_id,
            "--project-registry",
            str(registry),
        ]
    )
    assert result.returncode == int(ExitCode.INPUT_INVALID)
    payload = _stderr_payload(result)
    assert payload["error_code"] == "INPUT_INVALID"
    assert not (ROOT / "运行记录" / run_id).exists()
