from __future__ import annotations

import json
import subprocess
import sys
import uuid
import hashlib
import shutil
from pathlib import Path

import pytest

from conftest import ROOT
from 退出码 import ExitCode


pytestmark = pytest.mark.integration


def _写L2报告(path: Path, forms: list[dict]) -> None:
    payload = {
        "schema_version": "xcue.l2-report/1.0",
        "pipeline_run_id": "pytest-pipeline",
        "stage_run_id": "pytest-pipeline-L2",
        "status": "COMPLETED",
        "run_id": "pytest-L2",
        "输入文件": str(path.parent / "失败包.json"),
        "输入数量": len(forms),
        "方法声明": "pytest",
        "标准校验问题": [],
        "回流校验问题": [],
        "接口判断": [],
        "修复单": forms,
        "阻断项": [],
        "复验目标": [],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _修复单(module: str = "L2-05", problem: str = "入口弱") -> dict:
    return {
        "修复单类型": "L2 能力修复单",
        "来源闸门": "L1-02",
        "接收模块": module,
        "输入问题": problem,
        "主失败类型": problem,
        "次失败类型": "",
        "修复动作": "规划修复动作",
        "修复产物": "任务包",
        "验收问题": "回到 L1-02 复验",
        "回流位置": "L1-02",
        "是否需要其他L2辅助": "否",
        "是否需要回L15重路由": "否",
        "最终状态": "回原闸门复验",
        "rule_id": f"{module}:pytest-rule",
        "rule_version": "pytest",
        "rule_hash": "a" * 64,
    }


def _运行L3(l2_report: Path, out_dir: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return _运行L3固定编号(l2_report, out_dir, env, "pytest-L3-" + uuid.uuid4().hex[:8])


def _运行L3固定编号(
    l2_report: Path,
    out_dir: Path,
    env: dict[str, str],
    run_id: str,
    protocol_rules: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd = [
            sys.executable,
            str(ROOT / "00_工程总控" / "工程执行层" / "L3工程" / "L3运行入口.py"),
            "--l2-report",
            str(l2_report),
            "--run-id",
            run_id,
            "--out-dir",
            str(out_dir),
            "--pipeline-run-id",
            "pytest-pipeline",
            "--stage-run-id",
            "pytest-pipeline-L3",
            "--standard-mode",
            "CANDIDATE_TEST",
            "--project-harness",
            str(ROOT / "70_测试项目" / "TP-001_CleanHarness_IR_Runtime"),
    ]
    if protocol_rules is not None:
        cmd.extend(["--protocol-rules", str(protocol_rules)])
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _复制L3协议规则(root_case: Path) -> Path:
    source = ROOT / "00_工程总控" / "工程执行层" / "L3工程" / "protocol_rules.json"
    target = root_case / "protocol_rules.json"
    shutil.copyfile(source, target)
    return target


def 测试L3非空修复报告生成任务包且无执行字段(root_case, test_io_env):
    l2_report = root_case / "第二层" / "修复报告.json"
    l2_report.parent.mkdir(parents=True)
    out_dir = root_case / "第三层"
    _写L2报告(l2_report, [_修复单()])
    result = _运行L3(l2_report, out_dir, test_io_env)
    assert result.returncode == int(ExitCode.OK), result.stderr
    report = json.loads((out_dir / "任务包.json").read_text(encoding="utf-8"))
    assert report["execution_mode"] == "TASK_PLANNING_ONLY"
    assert report["prose_modified"] is False
    output = report["执行输出"][0]
    history = report["任务单"][0]["状态历史"]
    after_states = [item["后状态"] for item in history]
    assert "TASK_PACKAGE_CREATED" in after_states
    assert "AWAITING_EXECUTOR" in after_states
    assert "EXECUTION_COMPLETED" not in after_states
    assert after_states == list(dict.fromkeys(after_states))
    assert all({"前状态", "后状态", "触发事件", "时间", "执行组件", "证据文件"} <= set(item) for item in history)
    for forbidden in ["实际修改文件", "候选产物", "备份文件", "diff摘要文件", "回填位置", "待复验闸门"]:
        assert forbidden not in output
    assert output["任务包文件"]
    assert output["复验入口"] == "L1-02"


def 测试L3部分任务不可执行不默认全批报废(root_case, test_io_env):
    l2_report = root_case / "第二层" / "修复报告.json"
    l2_report.parent.mkdir(parents=True)
    out_dir = root_case / "第三层"
    bad = _修复单("L2-05", "坏任务")
    bad["修复动作"] = ""
    _写L2报告(l2_report, [_修复单("L2-05", "好任务"), bad])
    result = _运行L3(l2_report, out_dir, test_io_env)
    assert result.returncode == int(ExitCode.OK), result.stderr
    report = json.loads((out_dir / "任务包.json").read_text(encoding="utf-8"))
    assert report["status"] == "AWAITING_EXECUTOR"
    assert len(report["阻断任务"]) == 1
    assert any(output["task_package_created"] for output in report["执行输出"])


def 测试L3同RunID任一既有产物存在时拒绝且不覆盖(root_case, test_io_env):
    l2_report = root_case / "第二层" / "修复报告.json"
    l2_report.parent.mkdir(parents=True)
    out_dir = root_case / "第三层"
    run_id = "pytest-L3-fixed-" + uuid.uuid4().hex[:8]
    _写L2报告(l2_report, [_修复单()])

    first = _运行L3固定编号(l2_report, out_dir, test_io_env, run_id)
    assert first.returncode == int(ExitCode.OK), first.stderr
    json_path = out_dir / "任务包.json"
    md_path = out_dir / "任务包.md"
    assert json_path.exists()
    assert md_path.exists()
    before_json = _sha256(json_path)
    before_md = _sha256(md_path)
    before_files = sorted(path.relative_to(out_dir).as_posix() for path in out_dir.rglob("*") if path.is_file())

    second = _运行L3固定编号(l2_report, out_dir, test_io_env, run_id)

    assert second.returncode == int(ExitCode.INPUT_INVALID)
    payload = json.loads(second.stderr)
    assert payload["error_code"] == "INPUT_INVALID"
    assert _sha256(json_path) == before_json
    assert _sha256(md_path) == before_md
    after_files = sorted(path.relative_to(out_dir).as_posix() for path in out_dir.rglob("*") if path.is_file())
    assert after_files == before_files


@pytest.mark.parametrize("existing_name,forbidden_name", [("任务包.json", "任务包.md"), ("任务包.md", "任务包.json")])
def 测试L3任一单独既有产物存在时拒绝且不生成部分新文件(root_case, test_io_env, existing_name, forbidden_name):
    l2_report = root_case / "第二层" / "修复报告.json"
    l2_report.parent.mkdir(parents=True)
    out_dir = root_case / "第三层"
    run_id = "pytest-L3-fixed-" + uuid.uuid4().hex[:8]
    _写L2报告(l2_report, [_修复单()])
    out_dir.mkdir(parents=True)
    existing = out_dir / existing_name
    forbidden = out_dir / forbidden_name
    existing.write_text("历史产物\n", encoding="utf-8")
    before_hash = _sha256(existing)

    result = _运行L3固定编号(l2_report, out_dir, test_io_env, run_id)

    assert result.returncode == int(ExitCode.INPUT_INVALID)
    payload = json.loads(result.stderr)
    assert payload["error_code"] == "INPUT_INVALID"
    assert _sha256(existing) == before_hash
    assert not forbidden.exists()


def 测试A3L3结构化协议规则改动会改变IR输入映射(root_case, test_io_env):
    l2_report = root_case / "第二层" / "修复报告.json"
    l2_report.parent.mkdir(parents=True)
    out_dir = root_case / "第三层"
    rules_path = _复制L3协议规则(root_case)
    payload = json.loads(rules_path.read_text(encoding="utf-8"))
    payload["ir_mapping"]["L2-05"] = ["IR-01_立项卡.md"]
    rules_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _写L2报告(l2_report, [_修复单("L2-05", "入口弱")])

    result = _运行L3固定编号(
        l2_report,
        out_dir,
        test_io_env,
        "pytest-L3-a3-" + uuid.uuid4().hex[:8],
        rules_path,
    )

    assert result.returncode == int(ExitCode.OK), result.stderr
    report = json.loads((out_dir / "任务包.json").read_text(encoding="utf-8"))
    task = report["任务单"][0]
    assert task["IR输入"] == ["70_测试项目/TP-001_CleanHarness_IR_Runtime/IR/IR-01_立项卡.md"]
    assert report["protocol_rule_version"] == payload["version"]
    assert len(report["protocol_rule_hash"]) == 64


def 测试A3L3Markdown协议改动不改变L3运行行为(root_case, test_io_env):
    l2_report = root_case / "第二层" / "修复报告.json"
    l2_report.parent.mkdir(parents=True)
    out_dir_a = root_case / "A" / "第三层"
    out_dir_b = root_case / "B" / "第三层"
    rules_path = _复制L3协议规则(root_case)
    _写L2报告(l2_report, [_修复单("L2-05", "入口弱")])

    first = _运行L3固定编号(
        l2_report,
        out_dir_a,
        test_io_env,
        "pytest-L3-a3-" + uuid.uuid4().hex[:8],
        rules_path,
    )
    assert first.returncode == int(ExitCode.OK), first.stderr

    markdown_source = ROOT / "50_L3_执行协议层" / "L3-06_IR输入映射协议_v0.1.2.md"
    before = markdown_source.read_text(encoding="utf-8")
    try:
        markdown_source.write_text(before + "\n\n<!-- A3-L3 pytest markdown mutation should not affect runtime rules -->\n", encoding="utf-8")
        second = _运行L3固定编号(
            l2_report,
            out_dir_b,
            test_io_env,
            "pytest-L3-a3-" + uuid.uuid4().hex[:8],
            rules_path,
        )
    finally:
        markdown_source.write_text(before, encoding="utf-8")

    assert second.returncode == int(ExitCode.OK), second.stderr
    report_a = json.loads((out_dir_a / "任务包.json").read_text(encoding="utf-8"))
    report_b = json.loads((out_dir_b / "任务包.json").read_text(encoding="utf-8"))
    assert report_a["任务单"][0]["IR输入"] == report_b["任务单"][0]["IR输入"]
    assert report_a["协议规则摘要"] == report_b["协议规则摘要"]


def 测试A3L3坏结构化协议规则在写报告前失败(root_case, test_io_env):
    l2_report = root_case / "第二层" / "修复报告.json"
    l2_report.parent.mkdir(parents=True)
    out_dir = root_case / "第三层"
    bad_rules = root_case / "bad_protocol_rules.json"
    bad_rules.write_text('{"schema_version":"xcue.l3-protocol-rules/1.0","protocol":{}}', encoding="utf-8")
    _写L2报告(l2_report, [_修复单("L2-05", "入口弱")])

    result = _运行L3固定编号(
        l2_report,
        out_dir,
        test_io_env,
        "pytest-L3-a3-" + uuid.uuid4().hex[:8],
        bad_rules,
    )

    assert result.returncode == int(ExitCode.RULE_PARSE_FAILED)
    payload = json.loads(result.stderr)
    assert payload["error_code"] == "RULE_PARSE_FAILED"
    assert not (out_dir / "任务包.json").exists()
    assert not (out_dir / "任务包.md").exists()
