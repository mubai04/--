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


def _运行L2固定编号(packet: Path, out_dir: Path, env: dict[str, str], run_id: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "00_工程总控" / "工程执行层" / "L2工程" / "L2运行入口.py"),
            "--failure-packet",
            str(packet),
            "--run-id",
            run_id,
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


def _运行L2带规则文件(
    packet: Path,
    out_dir: Path,
    env: dict[str, str],
    rules_path: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "00_工程总控" / "工程执行层" / "L2工程" / "L2运行入口.py"),
            "--failure-packet",
            str(packet),
            "--run-id",
            "pytest-L2-a3-" + uuid.uuid4().hex[:8],
            "--out-dir",
            str(out_dir),
            "--pipeline-run-id",
            "pytest-pipeline",
            "--stage-run-id",
            "pytest-pipeline-L2",
            "--standard-mode",
            "CANDIDATE_TEST",
            "--ability-rules",
            str(rules_path),
        ],
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


def _读取运行报告(result: subprocess.CompletedProcess[str]) -> dict:
    payload = json.loads(result.stdout)
    return json.loads(Path(payload["report_json"]).read_text(encoding="utf-8"))


def _复制L2能力规则(root_case: Path) -> Path:
    source = ROOT / "00_工程总控" / "工程执行层" / "L2工程" / "ability_rules.json"
    target = root_case / "ability_rules.json"
    shutil.copyfile(source, target)
    return target


def _改写L205首条修复规则(path: Path, marker: str) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    first = payload["abilities"]["L2-05"]["failure_types"][0]
    first["repair_rules"] = [marker]
    first["acceptance"] = [marker + "-验收"]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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


def 测试L2同RunID任一既有产物存在时拒绝且不覆盖(root_case, test_io_env):
    packet = root_case / "失败包.json"
    out_dir = root_case / "第二层"
    run_id = "pytest-L2-fixed-" + uuid.uuid4().hex[:8]
    _写失败包(packet, [_失败项("入口弱", "入口弱", "L2-05")])

    first = _运行L2固定编号(packet, out_dir, test_io_env, run_id)
    assert first.returncode == int(ExitCode.OK), first.stderr
    json_path = out_dir / "修复报告.json"
    md_path = out_dir / "修复报告.md"
    assert json_path.exists()
    assert md_path.exists()
    before_json = _sha256(json_path)
    before_md = _sha256(md_path)
    before_files = sorted(path.relative_to(out_dir).as_posix() for path in out_dir.rglob("*") if path.is_file())

    second = _运行L2固定编号(packet, out_dir, test_io_env, run_id)

    assert second.returncode == int(ExitCode.INPUT_INVALID)
    payload = json.loads(second.stderr)
    assert payload["error_code"] == "INPUT_INVALID"
    assert _sha256(json_path) == before_json
    assert _sha256(md_path) == before_md
    after_files = sorted(path.relative_to(out_dir).as_posix() for path in out_dir.rglob("*") if path.is_file())
    assert after_files == before_files


@pytest.mark.parametrize("existing_name,forbidden_name", [("修复报告.json", "修复报告.md"), ("修复报告.md", "修复报告.json")])
def 测试L2任一单独既有产物存在时拒绝且不生成部分新文件(root_case, test_io_env, existing_name, forbidden_name):
    packet = root_case / "失败包.json"
    out_dir = root_case / "第二层"
    run_id = "pytest-L2-fixed-" + uuid.uuid4().hex[:8]
    _写失败包(packet, [_失败项("入口弱", "入口弱", "L2-05")])
    out_dir.mkdir(parents=True)
    existing = out_dir / existing_name
    forbidden = out_dir / forbidden_name
    existing.write_text("历史产物\n", encoding="utf-8")
    before_hash = _sha256(existing)

    result = _运行L2固定编号(packet, out_dir, test_io_env, run_id)

    assert result.returncode == int(ExitCode.INPUT_INVALID)
    payload = json.loads(result.stderr)
    assert payload["error_code"] == "INPUT_INVALID"
    assert _sha256(existing) == before_hash
    assert not forbidden.exists()


def 测试A3结构化能力规则改动会改变L2修复单(root_case, test_io_env):
    packet = root_case / "失败包.json"
    out_dir = root_case / "第二层"
    rules_path = _复制L2能力规则(root_case)
    marker = "A3-结构化规则动作-市场入口"
    _改写L205首条修复规则(rules_path, marker)
    _写失败包(packet, [_失败项("入口弱", "入口弱", "L2-05")])

    result = _运行L2带规则文件(packet, out_dir, test_io_env, rules_path)

    assert result.returncode == int(ExitCode.OK), result.stderr
    report = json.loads((out_dir / "修复报告.json").read_text(encoding="utf-8"))
    form = report["修复单"][0]
    assert marker in form["修复动作"]
    assert marker in form["标准动作"]
    assert form["规则编号"]
    assert form["规则依据"]


def 测试A3Markdown能力标准改动不改变L2运行行为(root_case, test_io_env):
    packet = root_case / "失败包.json"
    out_dir_a = root_case / "A" / "第二层"
    out_dir_b = root_case / "B" / "第二层"
    rules_path = _复制L2能力规则(root_case)
    _写失败包(packet, [_失败项("入口弱", "入口弱", "L2-05")])

    first = _运行L2带规则文件(packet, out_dir_a, test_io_env, rules_path)
    assert first.returncode == int(ExitCode.OK), first.stderr

    markdown_source = ROOT / "40_L2_正式能力层" / "L2-05_市场体验能力_v0.1.1_自检修正版.md"
    before = markdown_source.read_text(encoding="utf-8")
    try:
        markdown_source.write_text(before + "\n\n<!-- A3 pytest markdown mutation should not affect runtime rules -->\n", encoding="utf-8")
        second = _运行L2带规则文件(packet, out_dir_b, test_io_env, rules_path)
    finally:
        markdown_source.write_text(before, encoding="utf-8")

    assert second.returncode == int(ExitCode.OK), second.stderr
    report_a = json.loads((out_dir_a / "修复报告.json").read_text(encoding="utf-8"))
    report_b = json.loads((out_dir_b / "修复报告.json").read_text(encoding="utf-8"))
    assert report_a["修复单"] == report_b["修复单"]


def 测试A3结构化能力规则坏文件在写报告前失败(root_case, test_io_env):
    packet = root_case / "失败包.json"
    out_dir = root_case / "第二层"
    bad_rules = root_case / "bad_ability_rules.json"
    bad_rules.write_text('{"schema_version":"xcue.l2-ability-rules/1.0","abilities":{}}', encoding="utf-8")
    _写失败包(packet, [_失败项("入口弱", "入口弱", "L2-05")])

    result = _运行L2带规则文件(packet, out_dir, test_io_env, bad_rules)

    assert result.returncode == int(ExitCode.RULE_PARSE_FAILED)
    payload = json.loads(result.stderr)
    assert payload["error_code"] == "RULE_PARSE_FAILED"
    assert not (out_dir / "修复报告.json").exists()
    assert not (out_dir / "修复报告.md").exists()


def 测试A3结构化匹配关键词控制失败规则选择(root_case, test_io_env):
    packet = root_case / "失败包.json"
    out_dir = root_case / "第二层"
    rules_path = _复制L2能力规则(root_case)
    payload = json.loads(rules_path.read_text(encoding="utf-8"))
    for failure in payload["abilities"]["L2-05"]["failure_types"]:
        failure["signals"] = []
        failure["definition"] = ""
        failure["repair_rules"] = []
        failure["match_keywords"] = []
    first = payload["abilities"]["L2-05"]["failure_types"][0]
    first["match_keywords"] = ["A3独占失败"]
    first["repair_rules"] = ["A3独占结构化动作"]
    rules_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _写失败包(packet, [_失败项("A3独占失败", "A3独占失败", "L2-05")])

    result = _运行L2带规则文件(packet, out_dir, test_io_env, rules_path)

    assert result.returncode == int(ExitCode.OK), result.stderr
    report = json.loads((out_dir / "修复报告.json").read_text(encoding="utf-8"))
    form = report["修复单"][0]
    assert form["规则编号"] == "P1"
    assert form["标准动作"] == ["A3独占结构化动作"]
