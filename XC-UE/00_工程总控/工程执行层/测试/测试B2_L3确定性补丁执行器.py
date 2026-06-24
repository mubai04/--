from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from conftest import ROOT
from 退出码 import ExitCode


pytestmark = pytest.mark.integration

执行层 = ROOT / "00_工程总控" / "工程执行层"
L1入口 = 执行层 / "L1工程" / "L1运行入口.py"
L2入口 = 执行层 / "L2工程" / "L2运行入口.py"
统一入口 = 执行层 / "统一运行入口.py"
TP001正文 = ROOT / "70_测试项目" / "TP-001_CleanHarness_IR_Runtime" / "chapters" / "ch01.md"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _run(cmd: list[str], env: dict[str, str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        env={**env, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"},
        timeout=timeout,
    )


def _valid_chapter() -> str:
    paragraphs = [
        "# ch01",
        "",
        "雨夜的旧门忽然自己打开，许照看见门缝里压着一枚带血的钥匙，他立刻知道这不该出现在父亲留下的账册旁。",
        "因为城里的规矩写得很死：谁拿到钥匙，谁就必须在天亮前交出真正的名单，否则巡司会封掉整条巷子。",
        "脚步声从街口逼近，黑衣人已经追到门外，邻家的灯一盏盏熄灭，来不及解释的压力把他推到桌前。",
        "账册忽然裂开一层暗页，露出第二行名字，第一行正是许照自己，最后一行却写着一个已经死了三年的人。",
        "许照没有再等，他抬手把钥匙按进暗页的铜孔，决定赌一次，哪怕这意味着他会失去唯一能证明清白的证据。",
        "铜孔打开后，旧门后的影子第一次开口：真正要找名单的人不是巡司，而是父亲留下的最后一个同盟。",
        "这句话让许照明白，今晚的问题不是逃走，而是弄清楚谁把死人写回了名单。",
        "他转身推开门，血钥匙在掌心发烫，门外那群人同时停住，像是在等他自己走进陷阱。",
        "最后，他看见街尾还有第二扇门亮着，同一把钥匙正在那扇门里慢慢转动。",
    ]
    filler = (
        "许照把账册抱在怀里，反复确认每一个名字和门后的线索，"
        "他知道下一步必须在巡司抵达前找到第二扇门。"
    )
    paragraphs.extend([filler] * 60)
    return "\n\n".join(paragraphs) + "\n"


def _write_failure_packet(path: Path, chapter: Path, *, candidate: str = "L2-01") -> None:
    payload = {
        "schema_version": "xcue.failure-packet/1.0",
        "pipeline_run_id": "pytest-b2",
        "stage_run_id": "pytest-b2-L1",
        "status": "SCREENING_REJECT",
        "failure_count": 1,
        "items": [
            {
                "闸门": "L1-01",
                "名称": "有序叙事信号",
                "状态": "失败",
                "说明": "入口异常、规则压力、外部压力、升级、主动选择、章末新问题只识别到 3/6 类有序信号。",
                "证据": [{"段落": 3, "摘句": "在这里写第一章正文。"}],
                "严重级别": "error",
                "失败类型": "叙事失败",
                "候选模块": candidate,
                "回流验收位置": "L1-01",
                "修复方向": "事件链修正表 / 章节推进表",
            }
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _run_l2(packet: Path, out_dir: Path, env: dict[str, str]) -> Path:
    result = _run(
        [
            sys.executable,
            str(L2入口),
            "--failure-packet",
            str(packet),
            "--run-id",
            "pytest-B2-L2-" + uuid.uuid4().hex[:8],
            "--out-dir",
            str(out_dir),
            "--pipeline-run-id",
            "pytest-b2",
            "--stage-run-id",
            "pytest-b2-L2",
            "--standard-mode",
            "CANDIDATE_TEST",
        ],
        env,
    )
    assert result.returncode == int(ExitCode.OK), result.stdout + result.stderr
    return out_dir / "修复报告.json"


def _patch_strategy(
    chapter: Path,
    *,
    operation: str = "REPLACE",
    anchor: str = "在这里写第一章正文。",
    expected: str = "在这里写第一章正文。",
    replacement: str | None = None,
    insertion: str | None = None,
    position: str = "AFTER",
    eligible: bool = True,
    requires_generation: bool = False,
) -> dict[str, object]:
    new_text = replacement or _valid_chapter()
    return {
        "task_id": "B2-TASK-001",
        "project_id": "TP-001",
        "source_module": "L2-01",
        "target_file": str(chapter),
        "operation": operation,
        "anchor": anchor,
        "expected_text": expected,
        "replacement_text": new_text if operation == "REPLACE" else "",
        "append_text": insertion or "\n补丁追加文本包含突然、因为、追、决定、最后和下一步。\n",
        "position": position,
        "reason": "pytest B2 确定性补丁",
        "acceptance_conditions": ["重新运行 L1 后不再退回"],
        "risks": ["仅用于 TP-001 B2 垂直切片"],
        "automatic_execution_eligible": eligible,
        "requires_generative_completion": requires_generation,
    }


def _inject_strategies(l2_report: Path, strategies: list[dict[str, object]]) -> None:
    payload = json.loads(l2_report.read_text(encoding="utf-8"))
    assert payload["extensions"]["L2-01真实诊断"]
    payload["extensions"]["L2-01真实诊断"][0]["确定性候选策略"] = strategies
    l2_report.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _approval(plan: dict[str, object], *, status: str = "APPROVED", patch_sha256: str | None = None, source_sha256: str | None = None) -> dict[str, object]:
    return {
        "task_id": plan["task_id"],
        "project_id": plan["project_id"],
        "chapter_source": plan["chapter_source"],
        "source_sha256": source_sha256 or plan["source_sha256"],
        "patch_sha256": patch_sha256 or plan["patch_sha256"],
        "approver": "pytest",
        "approval_status": status,
        "approval_time": "2026-06-24T00:00:00+08:00",
    }


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _run_patch(
    l2_report: Path,
    out_dir: Path,
    env: dict[str, str],
    *,
    approval: Path | None = None,
    plan_only: bool = False,
    run_id: str | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(统一入口),
        "--target",
        "L3_PATCH",
        "--run-id",
        run_id or "pytest-B2-L3P-" + uuid.uuid4().hex[:8],
        "--standard-mode",
        "CANDIDATE_TEST",
        "--l2-report",
        str(l2_report),
        "--out-dir",
        str(out_dir),
    ]
    if approval:
        cmd.extend(["--approval", str(approval)])
    if plan_only:
        cmd.append("--plan-only")
    return _run(cmd, env, timeout=90)


def _prepare_l2_with_strategy(root_case: Path, env: dict[str, str], strategy: dict[str, object]) -> tuple[Path, Path]:
    chapter = Path(strategy["target_file"])
    packet = root_case / "第一层" / "失败包.json"
    l2_dir = root_case / "第二层"
    _write_failure_packet(packet, chapter)
    l2_report = _run_l2(packet, l2_dir, env)
    _inject_strategies(l2_report, [strategy])
    return chapter, l2_report


def test_b2_l201_outputs_structured_deterministic_strategy(root_case, test_io_env):
    chapter = root_case / "ch01.md"
    chapter.write_text(TP001正文.read_text(encoding="utf-8"), encoding="utf-8")
    packet = root_case / "第一层" / "失败包.json"
    _write_failure_packet(packet, chapter)

    l2_report = _run_l2(packet, root_case / "第二层", test_io_env)
    payload = json.loads(l2_report.read_text(encoding="utf-8"))
    diagnosis = payload["extensions"]["L2-01真实诊断"][0]

    strategy = diagnosis["确定性候选策略"][0]
    assert strategy["source_module"] == "L2-01"
    assert strategy["operation"] in {"REPLACE", "APPEND"}
    for field in [
        "task_id",
        "project_id",
        "target_file",
        "anchor",
        "expected_text",
        "reason",
        "acceptance_conditions",
        "risks",
        "automatic_execution_eligible",
    ]:
        assert strategy[field]
    assert strategy["requires_generative_completion"] is False


def test_b2_plan_requires_approval_and_preserves_formal_text(root_case, test_io_env):
    chapter = root_case / "ch01.md"
    chapter.write_text(TP001正文.read_text(encoding="utf-8"), encoding="utf-8")
    before = _sha256(chapter)
    _chapter, l2_report = _prepare_l2_with_strategy(root_case, test_io_env, _patch_strategy(chapter))

    plan_result = _run_patch(l2_report, root_case / "第三层", test_io_env, plan_only=True)
    assert plan_result.returncode == int(ExitCode.OK), plan_result.stdout + plan_result.stderr
    plan_report = json.loads((root_case / "第三层" / "补丁审计.json").read_text(encoding="utf-8"))
    assert plan_report["execution_mode"] == "PATCH_EXECUTION"
    assert plan_report["status"] == "PENDING_APPROVAL"
    assert plan_report["正式正文保持不变"] is True
    assert _sha256(chapter) == before
    assert not Path(plan_report["候选正文"]).exists()

    denied = _run_patch(l2_report, root_case / "未审批执行", test_io_env)
    assert denied.returncode == int(ExitCode.BLOCKED)
    payload = json.loads(denied.stderr)
    assert payload["error_code"] == "APPROVAL_REQUIRED"
    assert _sha256(chapter) == before


def test_b2_approved_replace_generates_candidate_diff_revalidation_and_audit(root_case, test_io_env):
    chapter = root_case / "ch01.md"
    chapter.write_text(TP001正文.read_text(encoding="utf-8"), encoding="utf-8")
    formal_before = _sha256(chapter)
    _chapter, l2_report = _prepare_l2_with_strategy(root_case, test_io_env, _patch_strategy(chapter))
    out_dir = root_case / "第三层"
    plan_result = _run_patch(l2_report, out_dir, test_io_env, plan_only=True)
    assert plan_result.returncode == int(ExitCode.OK), plan_result.stdout + plan_result.stderr
    plan = json.loads((out_dir / "补丁计划.json").read_text(encoding="utf-8"))
    approval_path = _write_json(root_case / "approval.json", _approval(plan))

    result = _run_patch(l2_report, out_dir / "执行", test_io_env, approval=approval_path)

    assert result.returncode == int(ExitCode.OK), result.stdout + result.stderr
    audit = json.loads((out_dir / "执行" / "补丁审计.json").read_text(encoding="utf-8"))
    candidate = Path(audit["候选正文"])
    diff_path = Path(audit["unified_diff"])
    revalidation = audit["复验结果"]
    assert audit["status"] == "READY_FOR_ACCEPTANCE"
    assert audit["approval"]["source_sha256"] == formal_before
    assert audit["approval"]["patch_sha256"] == plan["patch_sha256"]
    assert candidate.exists()
    assert diff_path.exists()
    assert "在这里写第一章正文。" not in candidate.read_text(encoding="utf-8")
    assert diff_path.read_text(encoding="utf-8").startswith("--- ")
    assert revalidation["exit_code"] in {int(ExitCode.OK), int(ExitCode.REVIEW_REQUIRED), int(ExitCode.GATE_REJECTED)}
    assert revalidation["gate_results"]["L1-01"] == "STRUCTURE_SIGNAL_PRESENT"
    assert revalidation["failure_packet"]
    assert audit["正式正文保持不变"] is True
    assert _sha256(chapter) == formal_before


def test_b2_real_tp001_revalidation_uses_pipeline_input_snapshot_without_test_io():
    run_id = "pytest-B2-real-" + uuid.uuid4().hex[:8]
    run_root = ROOT / "运行记录" / run_id
    packet = run_root / "第一层" / "失败包.json"
    l2_dir = run_root / "第二层"
    l3_dir = run_root / "第三层"
    env = dict(os.environ)
    env.pop("XCUE_TEST_ALLOW_EXTERNAL_IO", None)
    env.pop("XCUE_TEST_IO_TOKEN_FILE", None)
    formal_before = _sha256(TP001正文)
    _write_failure_packet(packet, TP001正文)

    l2_report = _run_l2(packet, l2_dir, env)
    plan_result = _run_patch(l2_report, l3_dir, env, plan_only=True, run_id=run_id + "-PLAN")
    assert plan_result.returncode == int(ExitCode.OK), plan_result.stdout + plan_result.stderr
    plan = json.loads((l3_dir / "补丁计划.json").read_text(encoding="utf-8"))
    approval_path = _write_json(run_root / "approval.json", _approval(plan))

    result = _run_patch(l2_report, l3_dir / "执行", env, approval=approval_path, run_id=run_id)

    assert result.returncode == int(ExitCode.OK), result.stdout + result.stderr
    audit = json.loads((l3_dir / "执行" / "补丁审计.json").read_text(encoding="utf-8"))
    revalidation = audit["复验结果"]
    snapshot = Path(revalidation["revalidation_snapshot"])
    assert audit["status"] == "READY_FOR_ACCEPTANCE"
    assert snapshot.exists()
    assert snapshot.is_relative_to((ROOT / "运行记录" / f"{run_id}-REVAL" / "输入快照").resolve())
    assert revalidation["gate_results"]["L1-01"] == "STRUCTURE_SIGNAL_PRESENT"
    assert _sha256(TP001正文) == formal_before


@pytest.mark.parametrize(
    "case_name, mutate, expected_status",
    [
        ("rejected", lambda ctx: _write_json(ctx["approval"], _approval(ctx["plan"], status="REJECTED")), "APPROVAL_REJECTED"),
        ("source_hash_changed", lambda ctx: (ctx["chapter"].write_text(ctx["chapter"].read_text(encoding="utf-8") + "\n变更\n", encoding="utf-8"), _write_json(ctx["approval"], _approval(ctx["plan"])))[1], "STALE_APPROVAL"),
        ("patch_hash_changed", lambda ctx: _write_json(ctx["approval"], _approval(ctx["plan"], patch_sha256="0" * 64)), "PATCH_PRECONDITION_FAILED"),
        ("missing_anchor", lambda ctx: (ctx["chapter"].write_text("锚点已经不在这里\n", encoding="utf-8"), _write_json(ctx["approval"], _approval(ctx["plan"])))[1], "PATCH_PRECONDITION_FAILED"),
        ("ambiguous_anchor", lambda ctx: (ctx["chapter"].write_text(ctx["chapter"].read_text(encoding="utf-8") + "\n在这里写第一章正文。\n", encoding="utf-8"), _write_json(ctx["approval"], _approval(ctx["plan"])))[1], "PATCH_AMBIGUOUS_ANCHOR"),
    ],
)
def test_b2_approval_and_precondition_failures_do_not_write_candidate(root_case, test_io_env, case_name, mutate, expected_status):
    chapter = root_case / f"{case_name}.md"
    chapter.write_text(TP001正文.read_text(encoding="utf-8"), encoding="utf-8")
    before = _sha256(chapter)
    _chapter, l2_report = _prepare_l2_with_strategy(root_case / case_name, test_io_env, _patch_strategy(chapter))
    out_dir = root_case / case_name / "第三层"
    plan_result = _run_patch(l2_report, out_dir, test_io_env, plan_only=True)
    assert plan_result.returncode == int(ExitCode.OK), plan_result.stdout + plan_result.stderr
    plan = json.loads((out_dir / "补丁计划.json").read_text(encoding="utf-8"))
    approval_path = root_case / case_name / "approval.json"
    ctx = {"chapter": chapter, "plan": plan, "approval": approval_path}
    mutate(ctx)

    result = _run_patch(l2_report, out_dir / "执行", test_io_env, approval=approval_path)

    assert result.returncode == int(ExitCode.BLOCKED)
    payload = json.loads(result.stderr)
    assert payload["error_code"] == expected_status
    assert not (out_dir / "执行" / "候选正文.md").exists()
    if expected_status != "STALE_APPROVAL":
        assert _sha256(chapter) == before or expected_status in {"PATCH_PRECONDITION_FAILED", "PATCH_AMBIGUOUS_ANCHOR"}


def test_b2_append_is_idempotent(root_case, test_io_env):
    chapter = root_case / "append.md"
    chapter.write_text(TP001正文.read_text(encoding="utf-8"), encoding="utf-8")
    strategy = _patch_strategy(chapter, operation="APPEND", insertion="\n" + _valid_chapter())
    _chapter, l2_report = _prepare_l2_with_strategy(root_case, test_io_env, strategy)
    out_dir = root_case / "第三层"
    plan_result = _run_patch(l2_report, out_dir, test_io_env, plan_only=True)
    assert plan_result.returncode == int(ExitCode.OK), plan_result.stdout + plan_result.stderr
    plan = json.loads((out_dir / "补丁计划.json").read_text(encoding="utf-8"))
    approval = _write_json(root_case / "approval.json", _approval(plan))
    first = _run_patch(l2_report, out_dir / "执行1", test_io_env, approval=approval)
    assert first.returncode == int(ExitCode.OK), first.stdout + first.stderr

    second = _run_patch(l2_report, out_dir / "执行2", test_io_env, approval=approval)

    assert second.returncode == int(ExitCode.BLOCKED)
    assert json.loads(second.stderr)["error_code"] == "PATCH_ALREADY_APPLIED"


@pytest.mark.parametrize(
    "strategy_patch, expected_status",
    [
        ({"project_id": "OTHER"}, "PROJECT_NOT_ALLOWED"),
        ({"target_file": "../outside.md"}, "PROJECT_NOT_ALLOWED"),
        ({"source_module": "L2-02"}, "PATCH_STRATEGY_NOT_L201"),
        ({"automatic_execution_eligible": False}, "PATCH_NOT_ELIGIBLE"),
        ({"requires_generative_completion": True}, "GENERATIVE_PATCH_FORBIDDEN"),
    ],
)
def test_b2_rejects_out_of_scope_or_generative_strategy(root_case, test_io_env, strategy_patch, expected_status):
    chapter = root_case / "ch01.md"
    chapter.write_text(TP001正文.read_text(encoding="utf-8"), encoding="utf-8")
    strategy = _patch_strategy(chapter)
    strategy.update(strategy_patch)
    packet = root_case / "第一层" / "失败包.json"
    _write_failure_packet(packet, chapter)
    l2_report = _run_l2(packet, root_case / "第二层", test_io_env)
    _inject_strategies(l2_report, [strategy])

    result = _run_patch(l2_report, root_case / "第三层", test_io_env, plan_only=True)

    assert result.returncode == int(ExitCode.BLOCKED)
    payload = json.loads(result.stderr)
    assert payload["error_code"] == expected_status


def test_b2_revalidation_failure_is_terminal_and_keeps_formal_text(root_case, test_io_env):
    chapter = root_case / "bad_candidate.md"
    chapter.write_text(TP001正文.read_text(encoding="utf-8"), encoding="utf-8")
    bad_text = "# ch01\n\n仍然太短。\n"
    strategy = _patch_strategy(chapter, replacement=bad_text)
    before = _sha256(chapter)
    _chapter, l2_report = _prepare_l2_with_strategy(root_case, test_io_env, strategy)
    out_dir = root_case / "第三层"
    plan_result = _run_patch(l2_report, out_dir, test_io_env, plan_only=True)
    assert plan_result.returncode == int(ExitCode.OK), plan_result.stdout + plan_result.stderr
    plan = json.loads((out_dir / "补丁计划.json").read_text(encoding="utf-8"))
    approval = _write_json(root_case / "approval.json", _approval(plan))

    result = _run_patch(l2_report, out_dir / "执行", test_io_env, approval=approval)

    assert result.returncode == int(ExitCode.BLOCKED)
    payload = json.loads(result.stderr)
    assert payload["error_code"] == "PATCH_VALIDATION_FAILED"
    audit = json.loads((out_dir / "执行" / "补丁审计.json").read_text(encoding="utf-8"))
    assert audit["status"] == "PATCH_VALIDATION_FAILED"
    assert audit["复验结果"]["exit_code"] == int(ExitCode.GATE_REJECTED)
    assert _sha256(chapter) == before


def test_b2_atomic_write_failure_leaves_no_partial_candidate(root_case, test_io_env):
    chapter = root_case / "atomic.md"
    chapter.write_text(TP001正文.read_text(encoding="utf-8"), encoding="utf-8")
    _chapter, l2_report = _prepare_l2_with_strategy(root_case, test_io_env, _patch_strategy(chapter))
    out_dir = root_case / "第三层"
    plan_result = _run_patch(l2_report, out_dir, test_io_env, plan_only=True)
    assert plan_result.returncode == int(ExitCode.OK), plan_result.stdout + plan_result.stderr
    plan = json.loads((out_dir / "补丁计划.json").read_text(encoding="utf-8"))
    approval = _write_json(root_case / "approval.json", _approval(plan))
    env = {**test_io_env, "XCUE_B2_FAIL_BEFORE_REPLACE": "1"}

    result = _run_patch(l2_report, out_dir / "执行", env, approval=approval)

    assert result.returncode == int(ExitCode.INTERNAL_ERROR)
    payload = json.loads(result.stderr)
    assert payload["error_code"] == "PATCH_WRITE_FAILED"
    assert not (out_dir / "执行" / "候选正文.md").exists()
    assert not any((out_dir / "执行").glob(".候选正文.md.*.tmp")) if (out_dir / "执行").exists() else True
