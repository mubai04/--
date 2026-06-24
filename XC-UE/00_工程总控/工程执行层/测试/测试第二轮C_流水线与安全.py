from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from conftest import ROOT
from ProjectHarness运行校验 import 发现Harness
from 任务单校验 import 校验 as 校验任务单
from 安全路径 import resolve_inside_root, safe_id, safe_output_path
from 版本回滚校验 import 校验 as 校验版本
from L3模型 import L3执行任务
from 流水线运行 import _写清单, _最终判定, _缺产物状态, _运行阶段
from 结构校验 import 按结构文件校验
from 退出码 import ExitCode


pytestmark = pytest.mark.integration


def _任务() -> L3执行任务:
    return L3执行任务(
        执行编号="T-001",
        来源层="L2-01",
        来源文件=str(ROOT / "运行记录" / "R" / "第二层" / "修复报告.json"),
        ProjectHarness根="70_测试项目/TP-001_CleanHarness_IR_Runtime",
        任务类型="正文改写任务规划",
        输入材料="问题",
        IR输入=[],
        目标文件="运行记录/R/第三层/分项任务/T-001.md",
        禁止修改文件=[],
        修复方向="规划",
        修复产物要求="任务包",
        回流验收位置="L1-01",
        是否允许改正式正文="否",
        是否需要备份="不适用",
    )


def 测试流水线严重错误优先级不被L1退回掩盖():
    code, status = _最终判定([int(ExitCode.GATE_REJECTED), int(ExitCode.BLOCKED)])
    assert code == int(ExitCode.BLOCKED)
    assert status == "BLOCKED"
    code, status = _最终判定([int(ExitCode.GATE_REJECTED), int(ExitCode.SCHEMA_INVALID)])
    assert code == int(ExitCode.SCHEMA_INVALID)
    assert status == "FAILED_SCHEMA"
    code, status = _最终判定([int(ExitCode.NO_PRODUCTION_RULESET), int(ExitCode.GATE_REJECTED)])
    assert code == int(ExitCode.NO_PRODUCTION_RULESET)
    assert status == "NO_PRODUCTION_RULESET"


def 测试流水线专用错误终态清单符合Schema(root_case):
    manifest = {
        "schema_version": "xcue.pipeline-manifest/1.0",
        "pipeline_run_id": "pytest-pipeline",
        "created_at": "2026-06-23T00:00:00+08:00",
        "status": "FAILED",
        "input": {
            "original_path": "70_测试项目/TP-001_CleanHarness_IR_Runtime/chapters/ch01.md",
            "snapshot_path": "运行记录/pytest-pipeline/输入快照/章节正文.md",
            "sha256": "a" * 64,
        },
        "project": {
            "project_id": "TP-001",
            "project_root": "70_测试项目/TP-001_CleanHarness_IR_Runtime",
            "project_manifest": "70_测试项目/TP-001_CleanHarness_IR_Runtime/project.json",
            "content_root": "70_测试项目/TP-001_CleanHarness_IR_Runtime/chapters",
            "chapter_source": "70_测试项目/TP-001_CleanHarness_IR_Runtime/chapters/ch01.md",
            "entrypoint": "70_测试项目/TP-001_CleanHarness_IR_Runtime/engine/TP001运行入口.py",
            "entrypoint_type": "project",
            "source_scope": "repository",
        },
        "standards": {
            "source": "Markdown Front Matter",
            "combined_sha256": "b" * 64,
            "standard_mode": "CANDIDATE_TEST",
            "experimental_standard": True,
            "production_eligibility": {
                "requested_mode": "CANDIDATE_TEST",
                "effective_mode": "CANDIDATE_TEST",
                "eligible": True,
                "reason": "NON_PRODUCTION_MODE",
                "rule_source": "00_工程总控/工程执行层/L1工程/gate_rules.json",
                "entrypoint": "PIPELINE",
                "rules_status": "",
                "schema_version": "",
                "production_eligible": False,
                "experimental_standard": True,
                "project_identity": "pytest",
            },
            "records": [],
            "error": "pytest",
        },
        "stages": [],
        "final_status": "RULE_PARSE_FAILED",
        "final_exit_code": int(ExitCode.RULE_PARSE_FAILED),
    }
    path = root_case / "流水线清单.json"
    _写清单(path, manifest)
    assert json.loads(path.read_text(encoding="utf-8"))["final_status"] == "RULE_PARSE_FAILED"


def 测试当前没有生产规则FrontMatter():
    rule_files = [
        *ROOT.glob("10_L0_总图层/*.md"),
        *ROOT.glob("20_L1_闸门层/*.md"),
        *ROOT.glob("30_L1.5_路由矩阵层/*.md"),
        *ROOT.glob("40_L2_正式能力层/*.md"),
        *ROOT.glob("50_L3_执行协议层/*.md"),
    ]
    text = "\n".join(path.read_text(encoding="utf-8-sig") for path in rule_files)
    assert "允许作为真源: true" not in text


@pytest.mark.security
def 测试安全ID拒绝恶意输入():
    bad_values = [
        "../x",
        "../../x",
        "..\\x",
        "C:\\Windows\\System32",
        "C:relative",
        "\\\\server\\share",
        "/root/x",
        "/tmp/x",
        "a/b",
        "a\\b",
        "%2e%2e/",
        "．．/",
        "CON",
        "NUL.txt",
        "COM1",
        "x" * 65,
        "bad\x00id",
        "bad\nid",
        "bad ",
        "bad.",
        "a:b",
        "中文/编号",
        "semi;colon",
        "space id",
        "tab\tid",
        "LPT9",
        "AUX",
        "PRN",
        "混合\\separator",
        "ＣＯＮ",
    ]
    for value in bad_values:
        with pytest.raises(Exception):
            safe_id(value, "run_id")


@pytest.mark.security
def 测试安全ID接受中文英文并规范化():
    assert safe_id("正常-运行_001", "run_id") == "正常-运行_001"
    assert safe_id("中文运行编号", "run_id") == "中文运行编号"
    assert safe_id("ＡＢＣ-１２３", "run_id") == "ABC-123"


@pytest.mark.security
def 测试安全输出路径拒绝越界且不创建目录(root_case):
    before = set(root_case.iterdir())
    for value in [
        "../x",
        "..\\x",
        "C:\\Windows\\System32",
        "C:relative",
        "\\\\server\\share",
        "\\\\?\\C:\\Windows",
        "\\\\.\\NUL",
        "/tmp/x",
        "a/../b",
        "CON",
    ]:
        with pytest.raises(Exception):
            safe_output_path(root_case, value)
    assert set(root_case.iterdir()) == before
    assert safe_output_path(root_case, "正常/输出.json").relative_to(root_case)


@pytest.mark.security
def 测试符号链接逃逸被拒绝(root_case, tmp_path: Path):
    link = root_case / "link"
    if not hasattr(link, "symlink_to"):
        pytest.skip("当前平台不支持符号链接测试")
    try:
        link.symlink_to(tmp_path, target_is_directory=True)
    except OSError:
        pytest.skip("当前权限不允许创建符号链接")
    with pytest.raises(Exception):
        resolve_inside_root(root_case, link / "escape.txt")


def 测试L3任务规划不要求正文备份():
    task = _任务()
    assert 校验任务单(task) == []
    assert 校验版本(task) == []


def 测试L3任务规划禁止修改正式正文():
    task = _任务()
    task.是否允许改正式正文 = "是"
    assert 校验任务单(task)
    assert 校验版本(task)


def 测试Harness未显式指定时加载默认项目():
    harness = 发现Harness(ROOT, None)
    assert harness == ROOT / "70_测试项目" / "TP-001_CleanHarness_IR_Runtime"


def 测试缺必备产物使用专门状态():
    code, status, message = _缺产物状态("L2", [ROOT / "运行记录" / "RUN" / "第二层" / "修复报告.json"])
    assert code == int(ExitCode.INTERNAL_ERROR)
    assert status == "L2_OUTPUT_MISSING"
    assert "修复报告.json" in message


def 测试阶段超时写入失败语义(monkeypatch):
    import 流水线运行

    monkeypatch.setattr(流水线运行, "阶段超时秒", 1)
    result = _运行阶段([sys.executable, "-c", "import time; time.sleep(2)"], ROOT)
    assert result.returncode == int(ExitCode.INTERNAL_ERROR)
    assert "FAILED_TIMEOUT" in result.stderr


@pytest.mark.security
def 测试生产规则错误不创建运行目录且返回专用错误(tmp_path: Path):
    entry = ROOT / "00_工程总控" / "工程执行层" / "统一运行入口.py"
    chapter = ROOT / "70_测试项目" / "TP-001_CleanHarness_IR_Runtime" / "chapters" / "ch01.md"
    run_id = "pytest-无生产规则-" + uuid.uuid4().hex[:8]
    result = subprocess.run(
        [
            sys.executable,
            str(entry),
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
        ],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == int(ExitCode.PRODUCTION_MODE_NOT_ELIGIBLE)
    manifest_path = ROOT / "运行记录" / run_id / "流水线清单.json"
    assert not manifest_path.exists()
    assert not (ROOT / "运行记录" / run_id).exists()
    payload = json.loads(result.stderr)
    assert payload["error_code"] == "PRODUCTION_MODE_NOT_ELIGIBLE"
    assert payload["reason"] == "CANDIDATE_RULES_ONLY"
    assert payload["run_root_created"] is False


@pytest.mark.security
def 测试统一入口恶意运行编号失败且不创建目录():
    entry = ROOT / "00_工程总控" / "工程执行层" / "统一运行入口.py"
    chapter = ROOT / "70_测试项目" / "TP-001_CleanHarness_IR_Runtime" / "chapters" / "ch01.md"
    result = subprocess.run(
        [
            sys.executable,
            str(entry),
            "--target",
            "PIPELINE",
            "--chapter",
            str(chapter),
            "--project",
            "pytest",
            "--run-id",
            "../x",
        ],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == int(ExitCode.INPUT_INVALID)
    assert not (ROOT / "x").exists()


@pytest.mark.security
def 测试仅设置外部IO环境变量不会放宽CLI路径(tmp_path: Path):
    entry = ROOT / "00_工程总控" / "工程执行层" / "L1工程" / "L1运行入口.py"
    chapter = tmp_path / "outside.md"
    out_dir = tmp_path / "outside-out"
    chapter.write_text("# 外部样本\n\n这是一段外部临时正文。\n", encoding="utf-8")
    run_id = "pytest-env-bypass-" + uuid.uuid4().hex[:8]
    env = {**os.environ, "XCUE_TEST_ALLOW_EXTERNAL_IO": "1"}
    env.pop("XCUE_TEST_IO_TOKEN_FILE", None)
    result = subprocess.run(
        [
            sys.executable,
            str(entry),
            "--chapter",
            str(chapter),
            "--out-dir",
            str(out_dir),
            "--run-id",
            run_id,
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
    assert result.returncode == int(ExitCode.INPUT_INVALID)
    assert not (out_dir / f"{run_id}.json").exists()
