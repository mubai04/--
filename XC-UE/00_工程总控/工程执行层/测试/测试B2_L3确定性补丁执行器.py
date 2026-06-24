from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
import uuid
from pathlib import Path

import pytest

from conftest import ROOT
from 退出码 import ExitCode
from L3补丁执行器 import 执行补丁, 补丁错误


pytestmark = pytest.mark.integration

# 本文件中的“正式应用”仅验证 B2 运行时对隔离副本正文执行批准后的确定性补丁，
# 不代表 Codex 在开发过程中手工改写小说正文。

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
        "candidate_sha256": plan.get("candidate_sha256", ""),
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
    protocol_rules: Path | None = None,
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
    if protocol_rules:
        cmd.extend(["--protocol-rules", str(protocol_rules)])
    return _run(cmd, env, timeout=90)


def _run_finalize(
    audit_json: Path,
    out_dir: Path,
    env: dict[str, str],
    *,
    approval: Path,
    decision: str,
    reason: str = "",
    run_id: str | None = None,
    protocol_rules: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(统一入口),
        "--target",
        "L3_PATCH",
        "--run-id",
        run_id or "pytest-B2-L3F-" + uuid.uuid4().hex[:8],
        "--standard-mode",
        "CANDIDATE_TEST",
        "--audit-json",
        str(audit_json),
        "--approval",
        str(approval),
        "--final-decision",
        decision,
        "--out-dir",
        str(out_dir),
    ]
    if reason:
        cmd.extend(["--decision-reason", reason])
    if protocol_rules:
        cmd.extend(["--protocol-rules", str(protocol_rules)])
    return _run(cmd, env, timeout=90)


def _ready_for_finalize(root_case: Path, test_io_env: dict[str, str], name: str = "case") -> tuple[Path, Path, Path, dict[str, object], Path]:
    chapter = root_case / f"{name}.md"
    chapter.write_text(TP001正文.read_text(encoding="utf-8"), encoding="utf-8")
    _chapter, l2_report = _prepare_l2_with_strategy(root_case / name, test_io_env, _patch_strategy(chapter))
    out_dir = root_case / name / "第三层"
    plan_result = _run_patch(l2_report, out_dir, test_io_env, plan_only=True)
    assert plan_result.returncode == int(ExitCode.OK), plan_result.stdout + plan_result.stderr
    plan = json.loads((out_dir / "补丁计划.json").read_text(encoding="utf-8"))
    execute_approval = _write_json(root_case / name / "approval-execute.json", _approval(plan))
    execute_result = _run_patch(l2_report, out_dir / "执行", test_io_env, approval=execute_approval)
    assert execute_result.returncode == int(ExitCode.OK), execute_result.stdout + execute_result.stderr
    ready_audit = json.loads((out_dir / "执行" / "补丁审计.json").read_text(encoding="utf-8"))
    final_approval = _write_json(root_case / name / "approval-final.json", _approval(ready_audit))
    return chapter, out_dir, out_dir / "执行" / "补丁审计.json", ready_audit, final_approval


def _final_markers_for(audit: dict[str, object]) -> list[Path]:
    marker_root = ROOT / "运行记录" / "B2_FINAL_MARKERS"
    if not marker_root.exists():
        return []
    result: list[Path] = []
    for marker in marker_root.glob("*.json"):
        try:
            payload = json.loads(marker.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        if all(
            payload.get(key) == audit.get(key)
            for key in ["task_id", "project_id", "chapter_source", "source_sha256", "candidate_sha256", "patch_sha256"]
        ):
            result.append(marker)
    return result


def _copy_protocol_rules(root_case: Path, mutate: object | None = None) -> Path:
    source = 执行层 / "L3工程" / "protocol_rules.json"
    target = root_case / f"protocol_rules-{uuid.uuid4().hex[:8]}.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    if callable(mutate):
        mutate(data)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


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
        ("rejected", lambda ctx: _write_json(ctx["approval"], _approval(ctx["plan"], status="REJECTED")), "REJECTED"),
        ("source_hash_changed", lambda ctx: (ctx["chapter"].write_text(ctx["chapter"].read_text(encoding="utf-8") + "\n变更\n", encoding="utf-8"), _write_json(ctx["approval"], _approval(ctx["plan"])))[1], "REVALIDATION_FAILED"),
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
    if expected_status not in {"REVALIDATION_FAILED"}:
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
    assert payload["error_code"] == "REVALIDATION_FAILED"
    audit = json.loads((out_dir / "执行" / "补丁审计.json").read_text(encoding="utf-8"))
    assert audit["status"] == "REVALIDATION_FAILED"
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
    assert payload["error_code"] == "EXECUTION_FAILED"
    assert not (out_dir / "执行" / "候选正文.md").exists()
    assert not any((out_dir / "执行").glob(".候选正文.md.*.tmp")) if (out_dir / "执行").exists() else True


def test_b2_finalize_reject_marks_rejected_and_keeps_formal_text(root_case, test_io_env):
    chapter = root_case / "reject.md"
    chapter.write_text(TP001正文.read_text(encoding="utf-8"), encoding="utf-8")
    before = _sha256(chapter)
    _chapter, l2_report = _prepare_l2_with_strategy(root_case, test_io_env, _patch_strategy(chapter))
    out_dir = root_case / "第三层"
    plan_result = _run_patch(l2_report, out_dir, test_io_env, plan_only=True)
    assert plan_result.returncode == int(ExitCode.OK), plan_result.stdout + plan_result.stderr
    plan = json.loads((out_dir / "补丁计划.json").read_text(encoding="utf-8"))
    execute_approval = _write_json(root_case / "approval-execute.json", _approval(plan))
    execute_result = _run_patch(l2_report, out_dir / "执行", test_io_env, approval=execute_approval)
    assert execute_result.returncode == int(ExitCode.OK), execute_result.stdout + execute_result.stderr
    ready_audit = json.loads((out_dir / "执行" / "补丁审计.json").read_text(encoding="utf-8"))
    final_approval = _write_json(root_case / "approval-final.json", _approval(ready_audit))

    finalize = _run_finalize(
        out_dir / "执行" / "补丁审计.json",
        out_dir / "正式采纳",
        test_io_env,
        approval=final_approval,
        decision="reject",
        reason="pytest reject",
    )

    assert finalize.returncode == int(ExitCode.OK), finalize.stdout + finalize.stderr
    rejected = json.loads((out_dir / "正式采纳" / "补丁审计.json").read_text(encoding="utf-8"))
    assert rejected["final_status"] == "REJECTED"
    assert rejected["decision"] == "reject"
    assert rejected["decision_reason"] == "pytest reject"
    assert rejected["backup_sha256"] == ""
    assert _sha256(chapter) == before


def test_b2_finalize_apply_marks_applied_and_updates_formal_text(root_case, test_io_env):
    chapter = root_case / "apply.md"
    chapter.write_text(TP001正文.read_text(encoding="utf-8"), encoding="utf-8")
    _chapter, l2_report = _prepare_l2_with_strategy(root_case, test_io_env, _patch_strategy(chapter))
    out_dir = root_case / "第三层"
    plan_result = _run_patch(l2_report, out_dir, test_io_env, plan_only=True)
    assert plan_result.returncode == int(ExitCode.OK), plan_result.stdout + plan_result.stderr
    plan = json.loads((out_dir / "补丁计划.json").read_text(encoding="utf-8"))
    execute_approval = _write_json(root_case / "approval-execute.json", _approval(plan))
    execute_result = _run_patch(l2_report, out_dir / "执行", test_io_env, approval=execute_approval)
    assert execute_result.returncode == int(ExitCode.OK), execute_result.stdout + execute_result.stderr
    ready_audit = json.loads((out_dir / "执行" / "补丁审计.json").read_text(encoding="utf-8"))
    final_approval = _write_json(root_case / "approval-final.json", _approval(ready_audit))

    finalize = _run_finalize(
        out_dir / "执行" / "补丁审计.json",
        out_dir / "正式采纳",
        test_io_env,
        approval=final_approval,
        decision="apply",
    )

    assert finalize.returncode == int(ExitCode.OK), finalize.stdout + finalize.stderr
    applied = json.loads((out_dir / "正式采纳" / "补丁审计.json").read_text(encoding="utf-8"))
    assert applied["final_status"] == "APPLIED"
    assert _sha256(chapter) == applied["candidate_sha256"]


def test_b2_finalize_without_approval_aborts_without_writing_formal_text(root_case, test_io_env):
    chapter = root_case / "abort.md"
    chapter.write_text(TP001正文.read_text(encoding="utf-8"), encoding="utf-8")
    before = _sha256(chapter)
    audit_json = root_case / "第三层" / "执行" / "补丁审计.json"
    audit_json.parent.mkdir(parents=True, exist_ok=True)
    audit_json.write_text(json.dumps({"status": "READY_FOR_ACCEPTANCE"}, ensure_ascii=False), encoding="utf-8")

    finalize = _run_finalize(
        audit_json,
        root_case / "第三层" / "正式采纳",
        test_io_env,
        approval=root_case / "missing-approval.json",
        decision="apply",
    )

    assert finalize.returncode in {int(ExitCode.BLOCKED), int(ExitCode.SCHEMA_INVALID)}
    payload = json.loads(finalize.stderr)
    assert payload["error_code"] in {"APPROVAL_REQUIRED", "ABORTED", "INPUT_SCHEMA_INVALID"}
    assert _sha256(chapter) == before


def test_b2_finalize_source_hash_change_returns_revalidation_failed(root_case, test_io_env):
    chapter = root_case / "source-changed.md"
    chapter.write_text(TP001正文.read_text(encoding="utf-8"), encoding="utf-8")
    _chapter, l2_report = _prepare_l2_with_strategy(root_case, test_io_env, _patch_strategy(chapter))
    out_dir = root_case / "第三层"
    plan_result = _run_patch(l2_report, out_dir, test_io_env, plan_only=True)
    assert plan_result.returncode == int(ExitCode.OK), plan_result.stdout + plan_result.stderr
    plan = json.loads((out_dir / "补丁计划.json").read_text(encoding="utf-8"))
    execute_approval = _write_json(root_case / "approval-execute.json", _approval(plan))
    execute_result = _run_patch(l2_report, out_dir / "执行", test_io_env, approval=execute_approval)
    assert execute_result.returncode == int(ExitCode.OK), execute_result.stdout + execute_result.stderr
    ready_audit = json.loads((out_dir / "执行" / "补丁审计.json").read_text(encoding="utf-8"))
    chapter.write_text(chapter.read_text(encoding="utf-8") + "\n漂移\n", encoding="utf-8")
    final_approval = _write_json(root_case / "approval-final.json", _approval(ready_audit))

    finalize = _run_finalize(
        out_dir / "执行" / "补丁审计.json",
        out_dir / "正式采纳",
        test_io_env,
        approval=final_approval,
        decision="apply",
    )

    assert finalize.returncode == int(ExitCode.BLOCKED)
    assert json.loads(finalize.stderr)["error_code"] == "REVALIDATION_FAILED"


def test_b2_finalize_post_apply_timeout_rolls_back_and_records_terminal(root_case, test_io_env):
    chapter, out_dir, audit_json, ready_audit, final_approval = _ready_for_finalize(root_case, test_io_env, "timeout")
    original_sha = ready_audit["source_sha256"]
    env = {**test_io_env, "XCUE_B2_FAIL_APPLY_REVALIDATION_TIMEOUT": "1"}

    finalize = _run_finalize(
        audit_json,
        out_dir / "正式采纳-timeout",
        env,
        approval=final_approval,
        decision="apply",
    )

    assert finalize.returncode == int(ExitCode.OK), finalize.stdout + finalize.stderr
    audit = json.loads((out_dir / "正式采纳-timeout" / "补丁审计.json").read_text(encoding="utf-8"))
    assert audit["final_status"] == "ROLLED_BACK"
    assert audit["error_code"] == "APPLY_REVALIDATION_TIMEOUT"
    assert audit["final_source_sha256"] == original_sha
    assert _sha256(chapter) == original_sha
    assert audit["是否尝试回滚"] is True
    assert audit["回滚是否成功"] is True


def test_b2_finalize_post_apply_audit_write_failure_uses_emergency_terminal(root_case, test_io_env):
    chapter, out_dir, audit_json, ready_audit, final_approval = _ready_for_finalize(root_case, test_io_env, "audit-write-fails")
    original_sha = ready_audit["source_sha256"]
    env = {**test_io_env, "XCUE_B2_FAIL_FINAL_AUDIT_WRITE": "1"}

    finalize = _run_finalize(
        audit_json,
        out_dir / "正式采纳-audit-fails",
        env,
        approval=final_approval,
        decision="apply",
    )

    assert finalize.returncode == int(ExitCode.OK), finalize.stdout + finalize.stderr
    audit_path = out_dir / "正式采纳-audit-fails" / "补丁审计.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["final_status"] == "ROLLED_BACK"
    assert audit["error_code"] == "FINAL_AUDIT_WRITE_FAILED"
    assert audit["final_source_sha256"] == original_sha
    assert audit["emergency_audit"] is True
    assert _sha256(chapter) == original_sha


def test_b2_finalize_post_apply_plain_exception_rolls_back(root_case, test_io_env):
    chapter, out_dir, audit_json, ready_audit, final_approval = _ready_for_finalize(root_case, test_io_env, "plain-exception")
    original_sha = ready_audit["source_sha256"]
    env = {**test_io_env, "XCUE_B2_FAIL_AFTER_APPLY_PLAIN_EXCEPTION": "1"}

    finalize = _run_finalize(
        audit_json,
        out_dir / "正式采纳-plain-exception",
        env,
        approval=final_approval,
        decision="apply",
    )

    assert finalize.returncode == int(ExitCode.OK), finalize.stdout + finalize.stderr
    audit = json.loads((out_dir / "正式采纳-plain-exception" / "补丁审计.json").read_text(encoding="utf-8"))
    assert audit["final_status"] == "ROLLED_BACK"
    assert audit["error_code"] == "POST_APPLY_EXCEPTION"
    assert audit["final_source_sha256"] == original_sha
    assert _sha256(chapter) == original_sha


def test_b2_finalize_formal_replace_failure_attempts_recovery_and_records_terminal(root_case, test_io_env):
    chapter, out_dir, audit_json, ready_audit, final_approval = _ready_for_finalize(root_case, test_io_env, "formal-replace-fails")
    original_sha = ready_audit["source_sha256"]
    env = {**test_io_env, "XCUE_B2_FAIL_FORMAL_REPLACE": "1"}

    finalize = _run_finalize(
        audit_json,
        out_dir / "正式采纳-formal-replace-fails",
        env,
        approval=final_approval,
        decision="apply",
    )

    assert finalize.returncode == int(ExitCode.BLOCKED)
    assert json.loads(finalize.stderr)["error_code"] == "APPLY_FAILED"
    audit = json.loads((out_dir / "正式采纳-formal-replace-fails" / "补丁审计.json").read_text(encoding="utf-8"))
    assert audit["final_status"] in {"APPLY_FAILED", "ROLLED_BACK"}
    assert audit["final_source_sha256"] == original_sha
    assert _sha256(chapter) == original_sha
    assert audit["backup_sha256"] == original_sha
    assert not list((out_dir / "正式采纳-formal-replace-fails").glob(".*.tmp"))


def test_b2_finalize_apply_hash_mismatch_rolls_back(root_case, test_io_env):
    chapter, out_dir, audit_json, ready_audit, final_approval = _ready_for_finalize(root_case, test_io_env, "apply-hash-mismatch")
    original_sha = ready_audit["source_sha256"]
    env = {**test_io_env, "XCUE_B2_CORRUPT_AFTER_APPLY": "1"}

    finalize = _run_finalize(
        audit_json,
        out_dir / "正式采纳-hash-mismatch",
        env,
        approval=final_approval,
        decision="apply",
    )

    assert finalize.returncode == int(ExitCode.OK), finalize.stdout + finalize.stderr
    audit = json.loads((out_dir / "正式采纳-hash-mismatch" / "补丁审计.json").read_text(encoding="utf-8"))
    assert audit["final_status"] == "ROLLED_BACK"
    assert audit["error_code"] == "APPLY_FAILED"
    assert audit["final_source_sha256"] == original_sha
    assert _sha256(chapter) == original_sha


def test_b2_finalize_rollback_write_failure_records_rollback_failed(root_case, test_io_env):
    chapter, out_dir, audit_json, ready_audit, final_approval = _ready_for_finalize(root_case, test_io_env, "rollback-write-fails")
    original_sha = ready_audit["source_sha256"]
    env = {**test_io_env, "XCUE_B2_FAIL_AFTER_APPLY_PLAIN_EXCEPTION": "1", "XCUE_B2_FAIL_ROLLBACK_WRITE": "1"}

    finalize = _run_finalize(
        audit_json,
        out_dir / "正式采纳-rollback-write-fails",
        env,
        approval=final_approval,
        decision="apply",
    )

    assert finalize.returncode == int(ExitCode.BLOCKED)
    assert json.loads(finalize.stderr)["error_code"] == "ROLLBACK_FAILED"
    audit = json.loads((out_dir / "正式采纳-rollback-write-fails" / "补丁审计.json").read_text(encoding="utf-8"))
    assert audit["final_status"] == "ROLLBACK_FAILED"
    assert audit["是否尝试回滚"] is True
    assert audit["回滚是否成功"] is False
    assert audit["final_source_sha256"] != original_sha
    assert audit["final_source_sha256"] == _sha256(chapter)


def test_b2_finalize_rollback_hash_mismatch_records_rollback_failed(root_case, test_io_env):
    chapter, out_dir, audit_json, ready_audit, final_approval = _ready_for_finalize(root_case, test_io_env, "rollback-hash-mismatch")
    original_sha = ready_audit["source_sha256"]
    env = {**test_io_env, "XCUE_B2_FAIL_AFTER_APPLY_PLAIN_EXCEPTION": "1", "XCUE_B2_CORRUPT_AFTER_ROLLBACK": "1"}

    finalize = _run_finalize(
        audit_json,
        out_dir / "正式采纳-rollback-hash-mismatch",
        env,
        approval=final_approval,
        decision="apply",
    )

    assert finalize.returncode == int(ExitCode.BLOCKED)
    audit = json.loads((out_dir / "正式采纳-rollback-hash-mismatch" / "补丁审计.json").read_text(encoding="utf-8"))
    assert audit["final_status"] == "ROLLBACK_FAILED"
    assert audit["rollback_sha256"] != original_sha
    assert audit["final_source_sha256"] == _sha256(chapter)


def test_b2_finalize_rejected_then_apply_returns_existing_rejected(root_case, test_io_env):
    chapter, out_dir, audit_json, ready_audit, final_approval = _ready_for_finalize(root_case, test_io_env, "rejected-first")
    original_sha = ready_audit["source_sha256"]
    first = _run_finalize(audit_json, out_dir / "正式采纳-reject1", test_io_env, approval=final_approval, decision="reject")
    second = _run_finalize(audit_json, out_dir / "正式采纳-apply2", test_io_env, approval=final_approval, decision="apply")

    assert first.returncode == int(ExitCode.OK), first.stdout + first.stderr
    assert second.returncode == int(ExitCode.OK), second.stdout + second.stderr
    second_audit = json.loads((out_dir / "正式采纳-apply2" / "补丁审计.json").read_text(encoding="utf-8"))
    assert second_audit["final_status"] == "REJECTED"
    assert second_audit["terminal_state_conflict"] is True
    assert _sha256(chapter) == original_sha
    assert len(_final_markers_for(ready_audit)) == 1


def test_b2_finalize_repeat_reject_is_idempotent(root_case, test_io_env):
    chapter, out_dir, audit_json, ready_audit, final_approval = _ready_for_finalize(root_case, test_io_env, "repeat-reject")
    original_sha = ready_audit["source_sha256"]
    first = _run_finalize(audit_json, out_dir / "正式采纳-reject1", test_io_env, approval=final_approval, decision="reject")
    second = _run_finalize(audit_json, out_dir / "正式采纳-reject2", test_io_env, approval=final_approval, decision="reject")

    assert first.returncode == int(ExitCode.OK), first.stdout + first.stderr
    assert second.returncode == int(ExitCode.OK), second.stdout + second.stderr
    assert json.loads((out_dir / "正式采纳-reject2" / "补丁审计.json").read_text(encoding="utf-8"))["final_status"] == "REJECTED"
    assert _sha256(chapter) == original_sha
    assert len(_final_markers_for(ready_audit)) == 1


def test_b2_finalize_concurrent_conflicting_decisions_create_one_terminal(root_case, test_io_env):
    _chapter, out_dir, audit_json, ready_audit, final_approval = _ready_for_finalize(root_case, test_io_env, "concurrent")

    def run(decision: str) -> subprocess.CompletedProcess[str]:
        return _run_finalize(
            audit_json,
            out_dir / f"正式采纳-{decision}-{uuid.uuid4().hex[:6]}",
            test_io_env,
            approval=final_approval,
            decision=decision,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, ["apply", "reject"]))

    assert all(result.returncode == int(ExitCode.OK) for result in results), "\n".join(result.stdout + result.stderr for result in results)
    markers = _final_markers_for(ready_audit)
    assert len(markers) == 1
    marker_payload = json.loads(markers[0].read_text(encoding="utf-8"))
    assert marker_payload["final_status"] in {"APPLIED", "REJECTED"}


def test_b2_protocol_rules_disable_patch_execution_blocks_runtime(root_case, test_io_env):
    chapter = root_case / "rules-disabled.md"
    chapter.write_text(TP001正文.read_text(encoding="utf-8"), encoding="utf-8")
    _chapter, l2_report = _prepare_l2_with_strategy(root_case, test_io_env, _patch_strategy(chapter))
    rules = _copy_protocol_rules(root_case, lambda data: data["patch_execution"].__setitem__("enabled", False))

    result = _run_patch(l2_report, root_case / "第三层-rules-disabled", test_io_env, plan_only=True, protocol_rules=rules)

    assert result.returncode == int(ExitCode.BLOCKED)
    assert json.loads(result.stderr)["error_code"] == "PATCH_RULES_DISABLED"


@pytest.mark.parametrize(
    "case_name, mutate",
    [
        ("missing-patch-execution", lambda data: data.pop("patch_execution")),
        ("missing-requires-backup", lambda data: data["patch_execution"].pop("requires_backup")),
        ("missing-requires-atomic-write", lambda data: data["patch_execution"].pop("requires_atomic_write")),
        (
            "missing-rollback-on-post-apply-failure",
            lambda data: data["patch_execution"].pop("rollback_on_any_post_apply_failure"),
        ),
    ],
)
def test_b2_protocol_rules_missing_required_patch_execution_fields_fail_at_load(root_case, test_io_env, case_name, mutate):
    chapter = root_case / f"{case_name}.md"
    chapter.write_text(TP001正文.read_text(encoding="utf-8"), encoding="utf-8")
    before = _sha256(chapter)
    _chapter, l2_report = _prepare_l2_with_strategy(root_case, test_io_env, _patch_strategy(chapter))
    rules = _copy_protocol_rules(root_case, mutate)

    result = _run_patch(l2_report, root_case / f"第三层-{case_name}", test_io_env, plan_only=True, protocol_rules=rules)

    assert result.returncode == int(ExitCode.RULE_PARSE_FAILED)
    assert json.loads(result.stderr)["error_code"] == "RULE_PARSE_FAILED"
    assert not (root_case / f"第三层-{case_name}" / "候选正文.md").exists()
    assert _sha256(chapter) == before


def test_b2_direct_executor_requires_structured_patch_rules(root_case, test_io_env):
    chapter = root_case / "direct-no-rules.md"
    chapter.write_text(TP001正文.read_text(encoding="utf-8"), encoding="utf-8")
    before = _sha256(chapter)
    _chapter, l2_report = _prepare_l2_with_strategy(root_case, test_io_env, _patch_strategy(chapter))

    with pytest.raises(补丁错误) as exc_info:
        执行补丁(
            l2_report=l2_report,
            audit_json=None,
            out_dir=root_case / "direct-no-rules-out",
            run_id="pytest-direct-no-rules",
            plan_only=True,
            protocol_rules=None,
        )

    assert exc_info.value.details["reason"] == "PATCH_RULES_INVALID"
    assert not (root_case / "direct-no-rules-out" / "候选正文.md").exists()
    assert _sha256(chapter) == before


def test_b2_protocol_rules_allowed_projects_change_runtime_result(root_case, test_io_env):
    chapter = root_case / "rules-project.md"
    chapter.write_text(TP001正文.read_text(encoding="utf-8"), encoding="utf-8")
    before = _sha256(chapter)
    _chapter, l2_report = _prepare_l2_with_strategy(root_case, test_io_env, _patch_strategy(chapter))
    rules = _copy_protocol_rules(root_case, lambda data: data["patch_execution"].__setitem__("allowed_projects", ["OTHER"]))

    result = _run_patch(l2_report, root_case / "第三层-rules-project", test_io_env, plan_only=True, protocol_rules=rules)

    assert result.returncode == int(ExitCode.BLOCKED)
    assert json.loads(result.stderr)["error_code"] == "PROJECT_NOT_ALLOWED"
    assert not (root_case / "第三层-rules-project" / "候选正文.md").exists()
    assert _sha256(chapter) == before


def test_b2_protocol_rules_allowed_sources_change_runtime_result(root_case, test_io_env):
    chapter = root_case / "rules-source.md"
    chapter.write_text(TP001正文.read_text(encoding="utf-8"), encoding="utf-8")
    before = _sha256(chapter)
    _chapter, l2_report = _prepare_l2_with_strategy(root_case, test_io_env, _patch_strategy(chapter))
    rules = _copy_protocol_rules(root_case, lambda data: data["patch_execution"].__setitem__("allowed_sources", ["L2-02"]))

    result = _run_patch(l2_report, root_case / "第三层-rules-source", test_io_env, plan_only=True, protocol_rules=rules)

    assert result.returncode == int(ExitCode.BLOCKED)
    assert json.loads(result.stderr)["error_code"] == "PATCH_STRATEGY_NOT_L201"
    assert not (root_case / "第三层-rules-source" / "候选正文.md").exists()
    assert _sha256(chapter) == before


def test_b2_protocol_rules_allowed_operations_change_runtime_result(root_case, test_io_env):
    chapter = root_case / "rules-operation.md"
    chapter.write_text(TP001正文.read_text(encoding="utf-8"), encoding="utf-8")
    _chapter, l2_report = _prepare_l2_with_strategy(root_case, test_io_env, _patch_strategy(chapter, operation="APPEND", insertion="\n" + _valid_chapter()))
    rules = _copy_protocol_rules(root_case, lambda data: data["patch_execution"].__setitem__("allowed_operations", ["REPLACE"]))

    result = _run_patch(l2_report, root_case / "第三层-rules-operation", test_io_env, plan_only=True, protocol_rules=rules)

    assert result.returncode == int(ExitCode.BLOCKED)
    assert json.loads(result.stderr)["error_code"] == "PATCH_PRECONDITION_FAILED"


@pytest.mark.parametrize(
    "case_name, mutate, expected",
    [
        ("forged-ready-json", lambda audit: audit.update({"source_sha256": "0" * 64}), "REVALIDATION_FAILED"),
        ("candidate-replaced", lambda audit: Path(audit["候选正文"]).write_text("# tampered\n", encoding="utf-8"), "REVALIDATION_FAILED"),
        ("candidate-sha-changed", lambda audit: audit.update({"candidate_sha256": "0" * 64}), "REVALIDATION_FAILED"),
        ("diff-sha-changed", lambda audit: audit.update({"diff_sha256": "0" * 64}), "REVALIDATION_FAILED"),
        ("revalidation-snapshot-changed", lambda audit: Path(audit["复验结果"]["revalidation_snapshot"]).write_text("# tampered\n", encoding="utf-8"), "REVALIDATION_FAILED"),
    ],
)
def test_b2_ready_audit_lineage_tampering_rejected_before_formal_write(root_case, test_io_env, case_name, mutate, expected):
    chapter, out_dir, audit_json, ready_audit, final_approval = _ready_for_finalize(root_case, test_io_env, case_name)
    before = _sha256(chapter)
    tampered = json.loads(audit_json.read_text(encoding="utf-8"))
    mutate(tampered)
    tampered_path = out_dir / f"{case_name}-tampered.json"
    _write_json(tampered_path, tampered)

    finalize = _run_finalize(
        tampered_path,
        out_dir / f"正式采纳-{case_name}",
        test_io_env,
        approval=final_approval,
        decision="apply",
    )

    assert finalize.returncode == int(ExitCode.BLOCKED)
    assert json.loads(finalize.stderr)["error_code"] == expected
    assert _sha256(chapter) == before


@pytest.mark.parametrize(
    "case_name, patch",
    [
        ("decision-task-mismatch", {"task_id": "OTHER-TASK"}),
        ("decision-candidate-mismatch", {"candidate_sha256": "0" * 64}),
        ("decision-patch-mismatch", {"patch_sha256": "0" * 64}),
    ],
)
def test_b2_final_decision_must_bind_approved_object(root_case, test_io_env, case_name, patch):
    chapter, out_dir, audit_json, _ready_audit, final_approval = _ready_for_finalize(root_case, test_io_env, case_name)
    before = _sha256(chapter)
    approval = json.loads(final_approval.read_text(encoding="utf-8"))
    approval.update(patch)
    bad_approval = _write_json(out_dir / f"{case_name}-approval.json", approval)

    finalize = _run_finalize(
        audit_json,
        out_dir / f"正式采纳-{case_name}",
        test_io_env,
        approval=bad_approval,
        decision="reject",
    )

    assert finalize.returncode == int(ExitCode.BLOCKED)
    assert _sha256(chapter) == before


def test_b2_finalize_repeat_apply_is_idempotent(root_case, test_io_env):
    chapter = root_case / "idempotent.md"
    chapter.write_text(TP001正文.read_text(encoding="utf-8"), encoding="utf-8")
    _chapter, l2_report = _prepare_l2_with_strategy(root_case, test_io_env, _patch_strategy(chapter))
    out_dir = root_case / "第三层"
    plan_result = _run_patch(l2_report, out_dir, test_io_env, plan_only=True)
    assert plan_result.returncode == int(ExitCode.OK), plan_result.stdout + plan_result.stderr
    plan = json.loads((out_dir / "补丁计划.json").read_text(encoding="utf-8"))
    execute_approval = _write_json(root_case / "approval-execute.json", _approval(plan))
    execute_result = _run_patch(l2_report, out_dir / "执行", test_io_env, approval=execute_approval)
    assert execute_result.returncode == int(ExitCode.OK), execute_result.stdout + execute_result.stderr
    ready_audit = json.loads((out_dir / "执行" / "补丁审计.json").read_text(encoding="utf-8"))
    final_approval = _write_json(root_case / "approval-final.json", _approval(ready_audit))

    first = _run_finalize(
        out_dir / "执行" / "补丁审计.json",
        out_dir / "正式采纳1",
        test_io_env,
        approval=final_approval,
        decision="apply",
    )
    second = _run_finalize(
        out_dir / "执行" / "补丁审计.json",
        out_dir / "正式采纳2",
        test_io_env,
        approval=final_approval,
        decision="apply",
    )

    assert first.returncode == int(ExitCode.OK), first.stdout + first.stderr
    assert second.returncode == int(ExitCode.OK), second.stdout + second.stderr
    first_audit = json.loads((out_dir / "正式采纳1" / "补丁审计.json").read_text(encoding="utf-8"))
    second_audit = json.loads((out_dir / "正式采纳2" / "补丁审计.json").read_text(encoding="utf-8"))
    assert first_audit["final_status"] == "APPLIED"
    assert second_audit["final_status"] == "APPLIED"


def test_b2_finalize_apply_then_reject_returns_existing_applied(root_case, test_io_env):
    chapter = root_case / "applied-once.md"
    chapter.write_text(TP001正文.read_text(encoding="utf-8"), encoding="utf-8")
    _chapter, l2_report = _prepare_l2_with_strategy(root_case, test_io_env, _patch_strategy(chapter))
    out_dir = root_case / "第三层"
    plan_result = _run_patch(l2_report, out_dir, test_io_env, plan_only=True)
    assert plan_result.returncode == int(ExitCode.OK), plan_result.stdout + plan_result.stderr
    plan = json.loads((out_dir / "补丁计划.json").read_text(encoding="utf-8"))
    execute_approval = _write_json(root_case / "approval-execute.json", _approval(plan))
    execute_result = _run_patch(l2_report, out_dir / "执行", test_io_env, approval=execute_approval)
    assert execute_result.returncode == int(ExitCode.OK), execute_result.stdout + execute_result.stderr
    ready_audit = json.loads((out_dir / "执行" / "补丁审计.json").read_text(encoding="utf-8"))
    final_approval = _write_json(root_case / "approval-final.json", _approval(ready_audit))
    first = _run_finalize(
        out_dir / "执行" / "补丁审计.json",
        out_dir / "正式采纳1",
        test_io_env,
        approval=final_approval,
        decision="apply",
    )
    second = _run_finalize(
        out_dir / "执行" / "补丁审计.json",
        out_dir / "正式采纳2",
        test_io_env,
        approval=final_approval,
        decision="reject",
    )
    assert first.returncode == int(ExitCode.OK), first.stdout + first.stderr
    assert second.returncode == int(ExitCode.OK), second.stdout + second.stderr
    second_audit = json.loads((out_dir / "正式采纳2" / "补丁审计.json").read_text(encoding="utf-8"))
    assert second_audit["final_status"] == "APPLIED"
    assert second_audit["terminal_state_conflict"] is True
    assert len(_final_markers_for(ready_audit)) == 1


def test_b2_l3_task_planning_only_remains_unchanged(root_case, test_io_env):
    packet = root_case / "第一层" / "失败包.json"
    chapter = root_case / "planning-only.md"
    chapter.write_text(TP001正文.read_text(encoding="utf-8"), encoding="utf-8")
    _write_failure_packet(packet, chapter)
    l2_report = _run_l2(packet, root_case / "第二层", test_io_env)

    result = _run(
        [
            sys.executable,
            str(统一入口),
            "--target",
            "L3",
            "--run-id",
            "pytest-L3-planning-" + uuid.uuid4().hex[:8],
            "--standard-mode",
            "CANDIDATE_TEST",
            "--l2-report",
            str(l2_report),
            "--out-dir",
            str(root_case / "L3规划"),
        ],
        test_io_env,
        timeout=90,
    )

    assert result.returncode in {int(ExitCode.OK), int(ExitCode.BLOCKED)}, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    report = json.loads(Path(json.loads(payload["stdout"])["report_json"]).read_text(encoding="utf-8"))
    assert report["execution_mode"] == "TASK_PLANNING_ONLY"
