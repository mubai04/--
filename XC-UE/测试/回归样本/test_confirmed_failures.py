from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import uuid
import venv
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
执行层 = ROOT / "00_工程总控" / "工程执行层"
公共组件 = 执行层 / "公共组件"
L2工程 = 执行层 / "L2工程"
L3工程 = 执行层 / "L3工程"
for path in [公共组件, L2工程, L3工程]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from L2_99_接口判断 import 判断
from L2模型 import 失败输入
from L2读取 import L2路由规则路径
from 路由规则加载 import 加载路由规则
from 能力标准解析 import 解析规则
from 标准加载器 import 候选试验模式
from 退出码 import ExitCode


def _test_io_env(tmp_path: Path) -> dict[str, str]:
    token = tmp_path / "xcue-test-io-token.txt"
    token.write_text("XCUE_TEST_EXTERNAL_IO_TOKEN_V1", encoding="utf-8")
    return {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "XCUE_TEST_ALLOW_EXTERNAL_IO": "1",
        "XCUE_TEST_IO_TOKEN_FILE": str(token),
    }


def _失败包(path: Path, items: list[dict[str, object]]) -> None:
    payload = {
        "schema_version": "xcue.failure-packet/1.0",
        "pipeline_run_id": "pytest-m0",
        "stage_run_id": "pytest-m0-L1",
        "status": "SCREENING_REJECT",
        "failure_count": len(items),
        "items": items,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _失败项(name: str, failure_type: str, candidate: str, return_gate: str = "L1-02") -> dict[str, object]:
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
        "修复方向": "pytest 固化复现",
    }


def _运行L2(
    packet: Path,
    out_dir: Path,
    tmp_path: Path,
    *,
    with_lineage: bool = True,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(L2工程 / "L2运行入口.py"),
        "--failure-packet",
        str(packet),
        "--run-id",
        "pytest-M0-L2-" + uuid.uuid4().hex[:8],
        "--out-dir",
        str(out_dir),
        "--standard-mode",
        候选试验模式,
    ]
    if with_lineage:
        command.extend(
            [
                "--pipeline-run-id",
                "pytest-m0",
                "--stage-run-id",
                "pytest-m0-L2",
            ]
        )
    return subprocess.run(
        command,
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        env=_test_io_env(tmp_path),
        timeout=30,
    )


def test_unified_entry_tp001_default_invocation_should_succeed_without_unrecognized_standard_mode():
    result = subprocess.run(
        [
            sys.executable,
            str(执行层 / "统一运行入口.py"),
            "--target",
            "TP-001",
            "--run-id",
            "pytest-M0-TP001-" + uuid.uuid4().hex[:8],
        ],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == int(ExitCode.OK), result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["returncode"] == int(ExitCode.OK)


def test_l2_empty_json_input_should_be_rejected(tmp_path: Path):
    packet = tmp_path / "空失败包.json"
    out_dir = tmp_path / "第二层"
    packet.write_text("{}", encoding="utf-8")
    result = _运行L2(packet, out_dir, tmp_path, with_lineage=False)
    combined = result.stdout + result.stderr
    assert result.returncode == int(ExitCode.INPUT_INVALID)
    payload = json.loads(result.stderr)
    assert payload["error_code"] == "INPUT_INVALID"
    assert payload["message"]
    assert payload["stage"] == "L2"
    assert "Traceback" not in combined
    assert not (out_dir / "修复报告.json").exists()
    assert not any(out_dir.glob("*.json")) if out_dir.exists() else True


def test_l3_empty_json_input_should_be_rejected(tmp_path: Path):
    report = tmp_path / "空L2报告.json"
    out_dir = tmp_path / "第三层"
    report.write_text("{}", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(L3工程 / "L3运行入口.py"),
            "--l2-report",
            str(report),
            "--project-harness",
            "70_测试项目/TP-001_CleanHarness_IR_Runtime",
            "--run-id",
            "pytest-M0-L3-" + uuid.uuid4().hex[:8],
            "--out-dir",
            str(out_dir),
            "--standard-mode",
            候选试验模式,
        ],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        env=_test_io_env(tmp_path),
        timeout=30,
    )
    combined = result.stdout + result.stderr
    assert result.returncode == int(ExitCode.INPUT_INVALID)
    payload = json.loads(result.stderr)
    assert payload["error_code"] == "INPUT_INVALID"
    assert payload["message"]
    assert payload["stage"] == "L3"
    assert "Traceback" not in combined
    assert not (out_dir / "执行报告.json").exists()
    assert not (out_dir / "任务包.json").exists()
    assert not any(out_dir.glob("*.json")) if out_dir.exists() else True


def test_corrupt_json_input_should_return_structured_error_without_traceback(tmp_path: Path):
    packet = tmp_path / "损坏失败包.json"
    out_dir = tmp_path / "第二层"
    packet.write_text("{", encoding="utf-8")
    result = _运行L2(packet, out_dir, tmp_path)
    combined = result.stdout + result.stderr
    assert result.returncode == int(ExitCode.INPUT_INVALID)
    assert "Traceback" not in combined
    payload = json.loads(result.stderr)
    assert payload["error_code"] == "INPUT_INVALID"
    assert payload["message"]
    assert payload["stage"] == "L2"
    assert payload["error"]
    assert not (out_dir / "修复报告.json").exists()
    assert not any(out_dir.glob("*.json")) if out_dir.exists() else True


def test_sixty_four_character_pipeline_id_should_not_leave_running_manifest():
    run_id = "P" * 64
    running_dir = ROOT / "运行记录" / run_id
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(执行层 / "统一运行入口.py"),
                "--target",
                "PIPELINE",
                "--chapter",
                "70_测试项目/TP-001_CleanHarness_IR_Runtime/chapters/ch01.md",
                "--project",
                "pytest-M0",
                "--run-id",
                run_id,
                "--standard-mode",
                候选试验模式,
            ],
            cwd=str(ROOT),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=30,
        )
        manifest = running_dir / "流水线清单.json"
        assert result.returncode != int(ExitCode.OK)
        assert not manifest.exists() or json.loads(manifest.read_text(encoding="utf-8"))["status"] != "RUNNING"
    finally:
        if running_dir.exists():
            shutil.rmtree(running_dir)


def test_reusing_same_l1_run_id_should_preserve_previous_report_attempt(tmp_path: Path):
    out_dir = tmp_path / "L1报告"
    run_id = "pytest-M0-L1-" + uuid.uuid4().hex[:8]
    entry = 执行层 / "L1工程" / "L1运行入口.py"
    chapter = ROOT / "70_测试项目" / "TP-001_CleanHarness_IR_Runtime" / "chapters" / "_candidates" / "ch01_candidate_RUN-20260621-002.md"
    base_cmd = [
        sys.executable,
        str(entry),
        "--chapter",
        str(chapter),
        "--run-id",
        run_id,
        "--out-dir",
        str(out_dir),
        "--standard-mode",
        候选试验模式,
    ]
    first = subprocess.run(
        [*base_cmd, "--project", "TP-001"],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        env=_test_io_env(tmp_path),
        timeout=30,
    )
    assert (out_dir / f"{run_id}.json").exists(), first.stderr
    second = subprocess.run(
        [*base_cmd, "--project", "TP-001"],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        env=_test_io_env(tmp_path),
        timeout=30,
    )
    assert second.returncode == int(ExitCode.INPUT_INVALID)
    retained = json.loads((out_dir / f"{run_id}.json").read_text(encoding="utf-8"))
    assert retained["项目"] == "TP-001"


def test_mixed_valid_and_out_of_scope_l2_items_should_still_emit_valid_fix(tmp_path: Path):
    packet = tmp_path / "混合失败包.json"
    out_dir = tmp_path / "第二层"
    _失败包(
        packet,
        [
            _失败项("入口弱", "入口弱", "L2-05"),
            _失败项("运营越界", "外部运营", "外部运营层"),
        ],
    )
    result = _运行L2(packet, out_dir, tmp_path)
    assert result.returncode == int(ExitCode.OK), result.stderr
    report = json.loads((out_dir / "修复报告.json").read_text(encoding="utf-8"))
    assert len(report["修复单"]) == 1
    assert report["阻断项"]


def test_l2_structured_route_rules_control_interface_decision():
    item = 失败输入(
        来源闸门="L1-03",
        名称="入口弱",
        状态="风险",
        说明="入口弱",
        证据=[],
        严重级别="warning",
        失败类型="入口弱",
        候选模块="",
        回流验收位置="L1-02",
        修复方向="pytest 固化复现",
    )
    assert 判断(item, None).主候选模块 != "L2-05"
    rules = 解析规则({})
    rules.路由规则集 = 加载路由规则(L2路由规则路径(ROOT))
    judgement = 判断(item, rules)
    assert judgement.主候选模块 == "L2-05"
    assert judgement.route_rule_id == "L2-ROUTE-005"
    assert judgement.route_rule_version
    assert len(judgement.route_rule_hash) == 64


def test_l2_six_ability_forbidden_items_should_enter_runtime(tmp_path: Path):
    from L2读取 import 读L2标准

    standards = 读L2标准(ROOT, 候选试验模式)
    rules = 解析规则(standards)
    counts = {module: len(rule.禁止项) for module, rule in rules.能力规则.items()}
    assert all(count > 0 for count in counts.values()), counts

    packet = tmp_path / "禁止输入失败包.json"
    out_dir = tmp_path / "第二层"
    _失败包(packet, [_失败项("正文全文", "叙事失败", "L2-01")])
    result = _运行L2(packet, out_dir, tmp_path)
    assert result.returncode == int(ExitCode.BLOCKED), result.stderr
    report = json.loads((out_dir / "修复报告.json").read_text(encoding="utf-8"))
    assert report["修复单"] == []
    assert report["阻断项"][0]["接口失败类型"] == "L2_FORBIDDEN"
    assert "正文全文" in report["阻断项"][0]["判断依据"]


def test_built_wheel_should_import_xc_ue_package(tmp_path: Path):
    wheelhouse = tmp_path / "wheelhouse"
    build = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            str(ROOT),
            "--no-deps",
            "--no-build-isolation",
            "-w",
            str(wheelhouse),
        ],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=120,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    wheels = sorted(wheelhouse.glob("xc_ue-*.whl"))
    assert len(wheels) == 1

    with zipfile.ZipFile(wheels[0]) as wheel:
        names = set(wheel.namelist())
    assert "xc_ue/__init__.py" in names
    assert "xc_ue/cli.py" in names
    assert any(name.endswith(".dist-info/METADATA") for name in names)

    venv_dir = tmp_path / "clean-venv"
    venv.EnvBuilder(with_pip=True).create(venv_dir)
    venv_python = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    install = subprocess.run(
        [str(venv_python), "-m", "pip", "install", "--no-deps", str(wheels[0])],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=120,
    )
    assert install.returncode == 0, install.stdout + install.stderr

    imported = subprocess.run(
        [str(venv_python), "-c", "import xc_ue; print(xc_ue.__version__)"],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=30,
    )
    assert imported.returncode == 0, imported.stdout + imported.stderr
    assert imported.stdout.strip() == "0.0.0"

    module_help = subprocess.run(
        [str(venv_python), "-m", "xc_ue", "--help"],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=30,
    )
    assert module_help.returncode == 0, module_help.stdout + module_help.stderr
    assert "XC-UE" in module_help.stdout

    console_script = venv_dir / ("Scripts/xcue.exe" if os.name == "nt" else "bin/xcue")
    cli = subprocess.run(
        [str(console_script), "--health"],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=30,
    )
    assert cli.returncode == 0, cli.stdout + cli.stderr
    payload = json.loads(cli.stdout)
    assert payload["ok"] is True
    assert payload["package"] == "xc_ue"
