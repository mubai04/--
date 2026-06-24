from __future__ import annotations

import difflib
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

公共组件 = Path(__file__).resolve().parents[1] / "公共组件"
if str(公共组件) not in sys.path:
    sys.path.insert(0, str(公共组件))

from 原子写入 import 原子写文本
from 文件哈希 import 计算文件哈希
from 工程异常 import 工程错误, 输入错误
from 退出码 import ExitCode
from 安全路径 import resolve_inside_root, safe_id
from 结构校验 import 按结构文件校验


ROOT = Path(__file__).resolve().parents[3]
SCHEMA_DIR = ROOT / "00_工程总控" / "工程执行层" / "公共组件" / "结构定义"
TP001_ROOT = ROOT / "70_测试项目" / "TP-001_CleanHarness_IR_Runtime"
TP001_CONTENT = TP001_ROOT / "chapters"
测试IO令牌内容 = "XCUE_TEST_EXTERNAL_IO_TOKEN_V1"


class 补丁错误(工程错误):
    def __init__(self, reason: str, message: str, exit_code: ExitCode = ExitCode.BLOCKED, **details: object) -> None:
        super().__init__(message, exit_code)
        self.details = {"reason": reason, **details}


@dataclass(frozen=True)
class 补丁计划:
    task_id: str
    project_id: str
    chapter_source: str
    source_sha256: str
    patch_sha256: str
    operation: str
    anchor: str
    expected_text: str
    replacement_text: str
    append_text: str
    position: str
    reason: str
    acceptance_conditions: list[str]
    risks: list[str]


def _允许测试外部IO() -> bool:
    if os.environ.get("XCUE_TEST_ALLOW_EXTERNAL_IO") != "1":
        return False
    token_path = os.environ.get("XCUE_TEST_IO_TOKEN_FILE", "")
    if not token_path:
        return False
    resolved = Path(token_path).resolve()
    try:
        resolved.relative_to(Path(tempfile.gettempdir()).resolve())
    except ValueError:
        return False
    try:
        return resolved.read_text(encoding="utf-8") == 测试IO令牌内容
    except OSError:
        return False


def _resolve_io_path(value: str | Path) -> Path:
    try:
        if _允许测试外部IO():
            resolved = Path(value).resolve()
            try:
                resolved.relative_to(Path(tempfile.gettempdir()).resolve())
                return resolved
            except ValueError:
                pass
        return resolve_inside_root(ROOT, value)
    except 输入错误 as exc:
        raise 补丁错误("PROJECT_NOT_ALLOWED", str(exc)) from exc


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise 输入错误(f"{label} 读取失败：{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise 输入错误(f"{label} 顶层必须是对象")
    return data


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_patch(strategy: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": strategy.get("task_id", ""),
        "project_id": strategy.get("project_id", ""),
        "source_module": strategy.get("source_module", ""),
        "target_file": strategy.get("target_file", ""),
        "operation": strategy.get("operation", ""),
        "anchor": strategy.get("anchor", ""),
        "expected_text": strategy.get("expected_text", ""),
        "replacement_text": strategy.get("replacement_text", ""),
        "append_text": strategy.get("append_text", ""),
        "position": strategy.get("position", ""),
        "reason": strategy.get("reason", ""),
        "acceptance_conditions": strategy.get("acceptance_conditions", []),
        "risks": strategy.get("risks", []),
    }


def _patch_hash(strategy: dict[str, Any]) -> str:
    text = json.dumps(_canonical_patch(strategy), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _text_hash(text)


def _strategy_text(strategy: dict[str, Any], key: str) -> str:
    value = strategy.get(key)
    if not isinstance(value, str) or not value:
        raise 补丁错误("PATCH_PRECONDITION_FAILED", f"补丁策略缺少字段：{key}")
    return value


def _strategy_list(strategy: dict[str, Any], key: str) -> list[str]:
    value = strategy.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise 补丁错误("PATCH_PRECONDITION_FAILED", f"补丁策略字段必须是字符串数组：{key}")
    return value


def _load_strategy(l2_report: Path) -> dict[str, Any]:
    data = _read_json(l2_report, "L2 报告")
    diagnostics = data.get("extensions", {}).get("L2-01真实诊断", [])
    if not isinstance(diagnostics, list):
        raise 补丁错误("PATCH_PRECONDITION_FAILED", "L2-01 真实诊断结构无效")
    strategies: list[dict[str, Any]] = []
    for diagnosis in diagnostics:
        if not isinstance(diagnosis, dict):
            continue
        raw_items = diagnosis.get("确定性候选策略", [])
        if not isinstance(raw_items, list):
            raise 补丁错误("PATCH_PRECONDITION_FAILED", "确定性候选策略必须是数组")
        strategies.extend(item for item in raw_items if isinstance(item, dict))
    if len(strategies) != 1:
        raise 补丁错误("PATCH_PRECONDITION_FAILED", "B2 首轮必须且只能消费一个 L2-01 确定性候选策略")
    return strategies[0]


def _target_path(strategy: dict[str, Any]) -> Path:
    raw = _strategy_text(strategy, "target_file")
    target = _resolve_io_path(raw)
    if strategy.get("project_id") != "TP-001":
        raise 补丁错误("PROJECT_NOT_ALLOWED", "B2 首轮只允许 TP-001")
    if target.is_absolute():
        if _允许测试外部IO():
            try:
                target.relative_to(Path(tempfile.gettempdir()).resolve())
                return target
            except ValueError:
                pass
        try:
            target.relative_to(TP001_CONTENT.resolve())
        except ValueError as exc:
            raise 补丁错误("PROJECT_NOT_ALLOWED", "目标文件不属于 TP-001 正文目录", path=str(target)) from exc
        return target
    return target


def _validate_strategy(strategy: dict[str, Any]) -> Path:
    if strategy.get("source_module") != "L2-01":
        raise 补丁错误("PATCH_STRATEGY_NOT_L201", "B2 首轮只消费 L2-01 候选策略")
    if strategy.get("automatic_execution_eligible") is not True:
        raise 补丁错误("PATCH_NOT_ELIGIBLE", "候选策略未取得自动执行资格")
    if strategy.get("requires_generative_completion") is True:
        raise 补丁错误("GENERATIVE_PATCH_FORBIDDEN", "B2 禁止生成式补全文本")
    if strategy.get("operation") not in {"REPLACE", "APPEND"}:
        raise 补丁错误("PATCH_PRECONDITION_FAILED", "B2 首轮只允许 REPLACE 或 APPEND")
    for key in ["task_id", "project_id", "target_file", "anchor", "expected_text", "reason", "position"]:
        _strategy_text(strategy, key)
    _strategy_list(strategy, "acceptance_conditions")
    _strategy_list(strategy, "risks")
    if strategy["operation"] == "REPLACE":
        _strategy_text(strategy, "replacement_text")
    if strategy["operation"] == "APPEND":
        _strategy_text(strategy, "append_text")
    return _target_path(strategy)


def _make_plan(strategy: dict[str, Any], target: Path) -> 补丁计划:
    if not target.exists() or not target.is_file():
        raise 补丁错误("PATCH_PRECONDITION_FAILED", f"目标文件不存在：{target}")
    return 补丁计划(
        task_id=_strategy_text(strategy, "task_id"),
        project_id=_strategy_text(strategy, "project_id"),
        chapter_source=str(target),
        source_sha256=计算文件哈希(target),
        patch_sha256=_patch_hash(strategy),
        operation=_strategy_text(strategy, "operation"),
        anchor=_strategy_text(strategy, "anchor"),
        expected_text=_strategy_text(strategy, "expected_text"),
        replacement_text=str(strategy.get("replacement_text", "")),
        append_text=str(strategy.get("append_text", "")),
        position=_strategy_text(strategy, "position"),
        reason=_strategy_text(strategy, "reason"),
        acceptance_conditions=_strategy_list(strategy, "acceptance_conditions"),
        risks=_strategy_list(strategy, "risks"),
    )


def _plan_dict(plan: 补丁计划, run_id: str, status: str = "PENDING_APPROVAL", out_dir: Path | None = None) -> dict[str, Any]:
    return {
        "schema_version": "xcue.l3-patch-audit/1.0",
        "execution_mode": "PATCH_EXECUTION",
        "status": status,
        "run_id": run_id,
        "task_id": plan.task_id,
        "project_id": plan.project_id,
        "chapter_source": plan.chapter_source,
        "source_sha256": plan.source_sha256,
        "patch_sha256": plan.patch_sha256,
        "operation": plan.operation,
        "anchor": plan.anchor,
        "expected_text": plan.expected_text,
        "replacement_text": plan.replacement_text,
        "append_text": plan.append_text,
        "position": plan.position,
        "reason": plan.reason,
        "acceptance_conditions": plan.acceptance_conditions,
        "risks": plan.risks,
        "候选正文": str(out_dir / "候选正文.md") if out_dir else "",
        "unified_diff": str(out_dir / "补丁.diff") if out_dir else "",
        "正式正文保持不变": True,
    }


def _write_audit(out_dir: Path, payload: dict[str, Any]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    按结构文件校验(payload, SCHEMA_DIR / "第三层补丁审计结构.json", "L3 补丁审计")
    path = out_dir / "补丁审计.json"
    原子写文本(path, json.dumps(payload, ensure_ascii=False, indent=2))
    return path


def _write_plan(out_dir: Path, plan: 补丁计划, run_id: str) -> dict[str, Any]:
    payload = _plan_dict(plan, run_id, out_dir=out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    原子写文本(out_dir / "补丁计划.json", json.dumps(payload, ensure_ascii=False, indent=2))
    _write_audit(out_dir, payload)
    return payload


def _load_approval(path: Path | None) -> dict[str, Any]:
    if path is None:
        raise 补丁错误("APPROVAL_REQUIRED", "缺少审批记录")
    data = _read_json(path, "审批记录")
    required = [
        "task_id",
        "project_id",
        "chapter_source",
        "source_sha256",
        "patch_sha256",
        "approver",
        "approval_status",
        "approval_time",
    ]
    for key in required:
        if not isinstance(data.get(key), str) or not data[key]:
            raise 补丁错误("PATCH_PRECONDITION_FAILED", f"审批记录缺少字段：{key}")
    return data


def _check_approval(plan: 补丁计划, approval: dict[str, Any]) -> None:
    if approval["approval_status"] != "APPROVED":
        raise 补丁错误("APPROVAL_REJECTED", "审批记录不是 APPROVED")
    expected = {
        "task_id": plan.task_id,
        "project_id": plan.project_id,
        "chapter_source": plan.chapter_source,
        "source_sha256": plan.source_sha256,
        "patch_sha256": plan.patch_sha256,
    }
    for key, value in expected.items():
        if key == "source_sha256":
            continue
        if approval[key] != value:
            raise 补丁错误("PATCH_PRECONDITION_FAILED", f"审批记录字段不匹配：{key}")
    if approval["source_sha256"] != plan.source_sha256:
        raise 补丁错误("STALE_APPROVAL", "审批绑定的正文哈希已过期")


def _apply_patch(plan: 补丁计划, source_text: str) -> str:
    if plan.expected_text != plan.anchor:
        raise 补丁错误("PATCH_PRECONDITION_FAILED", "expected_text 必须与 anchor 一致")
    count = source_text.count(plan.anchor)
    if count == 0:
        raise 补丁错误("PATCH_PRECONDITION_FAILED", "原文锚点不存在")
    if count > 1:
        raise 补丁错误("PATCH_AMBIGUOUS_ANCHOR", "原文锚点不唯一")
    if plan.operation == "REPLACE":
        return source_text.replace(plan.anchor, plan.replacement_text, 1)
    if plan.append_text in source_text:
        raise 补丁错误("PATCH_ALREADY_APPLIED", "APPEND 补丁内容已存在，拒绝重复执行")
    if plan.position == "BEFORE":
        return source_text.replace(plan.anchor, plan.append_text + plan.anchor, 1)
    if plan.position == "AFTER":
        return source_text.replace(plan.anchor, plan.anchor + plan.append_text, 1)
    raise 补丁错误("PATCH_PRECONDITION_FAILED", "APPEND 作用位置必须为 BEFORE 或 AFTER")


def _diff(before: str, after: str, source: str, candidate: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=source,
            tofile=candidate,
        )
    )


def _marker_path(plan: 补丁计划) -> Path:
    marker_id = _text_hash(f"{plan.task_id}:{plan.source_sha256}:{plan.patch_sha256}")
    return ROOT / "运行记录" / "B2_PATCH_MARKERS" / f"{marker_id}.json"


def _check_marker(plan: 补丁计划) -> None:
    if plan.operation != "APPEND":
        return
    marker = _marker_path(plan)
    if marker.exists():
        raise 补丁错误("PATCH_ALREADY_APPLIED", "同一补丁已生成过成功候选，拒绝重复执行")


def _write_marker(plan: 补丁计划, audit: dict[str, Any]) -> None:
    if plan.operation != "APPEND":
        return
    marker = _marker_path(plan)
    payload = {
        "schema_version": "xcue.l3-patch-marker/1.0",
        "task_id": plan.task_id,
        "source_sha256": plan.source_sha256,
        "patch_sha256": plan.patch_sha256,
        "candidate_sha256": audit.get("candidate_sha256", ""),
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "audit_json": str(Path(audit.get("候选正文", "")).parent / "补丁审计.json"),
    }
    原子写文本(marker, json.dumps(payload, ensure_ascii=False, indent=2))


def _run_l1(candidate: Path, out_dir: Path, run_id: str) -> dict[str, Any]:
    snapshot = ROOT / "运行记录" / run_id / "输入快照" / "候选正文.md"
    原子写文本(snapshot, candidate.read_text(encoding="utf-8"))
    cmd = [
        sys.executable,
        str(ROOT / "00_工程总控" / "工程执行层" / "L1工程" / "L1运行入口.py"),
        "--chapter",
        str(snapshot),
        "--project",
        "TP-001",
        "--run-id",
        run_id,
        "--out-dir",
        str(out_dir),
        "--pipeline-run-id",
        run_id,
        "--stage-run-id",
        f"{run_id}-L1",
        "--standard-mode",
        "CANDIDATE_TEST",
    ]
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    if _允许测试外部IO():
        env["XCUE_TEST_ALLOW_EXTERNAL_IO"] = "1"
        env["XCUE_TEST_IO_TOKEN_FILE"] = os.environ.get("XCUE_TEST_IO_TOKEN_FILE", "")
    result = subprocess.run(cmd, cwd=str(ROOT), text=True, encoding="utf-8", errors="replace", capture_output=True, env=env, timeout=90)
    payload = {
        "exit_code": int(result.returncode),
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "report_json": str(out_dir / "检测报告.json"),
        "failure_packet": str(out_dir / "失败包.json"),
        "revalidation_snapshot": str(snapshot),
    }
    try:
        stdout_data = json.loads(result.stdout)
        if isinstance(stdout_data, dict):
            payload["report_json"] = stdout_data.get("report_json", payload["report_json"])
            payload["failure_packet"] = stdout_data.get("failure_packet", payload["failure_packet"])
            payload["gate_results"] = stdout_data.get("gate_results", {})
    except json.JSONDecodeError:
        pass
    return payload


def _复验通过(revalidation: dict[str, Any]) -> bool:
    if revalidation["exit_code"] in {int(ExitCode.OK), int(ExitCode.REVIEW_REQUIRED)}:
        return True
    gate_results = revalidation.get("gate_results", {})
    if isinstance(gate_results, dict) and gate_results.get("L1-01") == "STRUCTURE_SIGNAL_PRESENT":
        failure_packet = Path(str(revalidation.get("failure_packet", "")))
        if failure_packet.exists():
            try:
                data = json.loads(failure_packet.read_text(encoding="utf-8-sig"))
                items = data.get("items", [])
                if isinstance(items, list):
                    return not any(isinstance(item, dict) and item.get("候选模块") == "L2-01" for item in items)
            except (OSError, json.JSONDecodeError):
                return False
    return False


def 执行补丁(
    *,
    l2_report: Path,
    out_dir: Path,
    run_id: str,
    approval_path: Path | None = None,
    plan_only: bool = False,
) -> dict[str, Any]:
    strategy = _load_strategy(l2_report)
    target = _validate_strategy(strategy)
    plan = _make_plan(strategy, target)
    if plan_only:
        return _write_plan(out_dir, plan, run_id)

    approval = _load_approval(approval_path)
    before = target.read_text(encoding="utf-8")
    before_hash = 计算文件哈希(target)
    if approval["approval_status"] != "APPROVED":
        raise 补丁错误("APPROVAL_REJECTED", "审批记录不是 APPROVED")
    if approval["patch_sha256"] != plan.patch_sha256:
        raise 补丁错误("PATCH_PRECONDITION_FAILED", "审批绑定的补丁哈希不一致")
    if approval["task_id"] != plan.task_id or approval["project_id"] != plan.project_id or approval["chapter_source"] != plan.chapter_source:
        raise 补丁错误("PATCH_PRECONDITION_FAILED", "审批记录与补丁计划不匹配")
    _check_marker(plan)
    # 锚点前置条件先于 source hash 终止，便于区分内容漂移中的定位失败。
    before.count(plan.anchor)
    after = _apply_patch(plan, before)
    if before_hash != plan.source_sha256 or approval["source_sha256"] != plan.source_sha256:
        raise 补丁错误("STALE_APPROVAL", "执行前正文哈希与计划哈希不一致")

    candidate = out_dir / "候选正文.md"
    diff_path = out_dir / "补丁.diff"
    audit = _plan_dict(plan, run_id, "PRECONDITION_CHECKED", out_dir=out_dir)
    audit["approval"] = approval
    try:
        if os.environ.get("XCUE_B2_FAIL_BEFORE_REPLACE") == "1":
            raise OSError("pytest injected write failure")
        原子写文本(candidate, after)
        原子写文本(diff_path, _diff(before, after, str(target), str(candidate)))
    except OSError as exc:
        audit["status"] = "PATCH_WRITE_FAILED"
        audit["候选正文"] = str(candidate)
        audit["unified_diff"] = str(diff_path)
        _write_audit(out_dir, audit)
        raise 补丁错误("PATCH_WRITE_FAILED", f"候选正文写入失败：{exc}", ExitCode.INTERNAL_ERROR) from exc

    audit["status"] = "PATCH_EXECUTED"
    audit["候选正文"] = str(candidate)
    audit["candidate_sha256"] = 计算文件哈希(candidate)
    audit["unified_diff"] = str(diff_path)
    audit["diff_sha256"] = 计算文件哈希(diff_path)
    audit["正式正文保持不变"] = 计算文件哈希(target) == before_hash
    revalidation = _run_l1(candidate, out_dir / "复验", f"{run_id}-REVAL")
    audit["复验结果"] = revalidation
    if not _复验通过(revalidation):
        audit["status"] = "PATCH_VALIDATION_FAILED"
        _write_audit(out_dir, audit)
        raise 补丁错误("PATCH_VALIDATION_FAILED", "候选正文 L1 复验失败")
    audit["status"] = "READY_FOR_ACCEPTANCE"
    _write_audit(out_dir, audit)
    _write_marker(plan, audit)
    return audit
