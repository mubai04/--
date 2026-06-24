from __future__ import annotations

import difflib
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import uuid
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


最终状态 = {
    "REJECTED",
    "APPLIED",
    "ROLLED_BACK",
    "EXECUTION_FAILED",
    "REVALIDATION_FAILED",
    "APPLY_FAILED",
    "ROLLBACK_FAILED",
    "ABORTED",
}


DEFAULT_PATCH_RULES = {
    "enabled": True,
    "allowed_projects": ["TP-001"],
    "allowed_sources": ["L2-01"],
    "allowed_operations": ["REPLACE", "APPEND"],
    "requires_candidate_approval": True,
    "requires_final_decision": True,
    "requires_backup": True,
    "requires_atomic_write": True,
    "requires_post_apply_revalidation": True,
    "rollback_on_any_post_apply_failure": True,
    "formal_text_write": "approved_runtime_only",
    "terminal_states": list(最终状态),
}


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


def _patch_rules(protocol_rules: Any | None) -> dict[str, Any]:
    if protocol_rules is None:
        return DEFAULT_PATCH_RULES
    rules = getattr(protocol_rules, "补丁执行规则", None)
    if not isinstance(rules, dict) or not rules:
        raise 补丁错误("PATCH_RULES_INVALID", "L3_PATCH 缺少结构化 patch_execution 规则")
    return rules


def _target_path(strategy: dict[str, Any], rules: dict[str, Any]) -> Path:
    raw = _strategy_text(strategy, "target_file")
    target = _resolve_io_path(raw)
    allowed_projects = set(rules.get("allowed_projects", []))
    if strategy.get("project_id") not in allowed_projects:
        raise 补丁错误("PROJECT_NOT_ALLOWED", f"B2 首轮只允许：{','.join(sorted(allowed_projects))}")
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


def _validate_strategy(strategy: dict[str, Any], rules: dict[str, Any]) -> Path:
    if rules.get("enabled") is not True:
        raise 补丁错误("PATCH_RULES_DISABLED", "patch_execution 未启用")
    allowed_sources = set(rules.get("allowed_sources", []))
    if strategy.get("source_module") not in allowed_sources:
        raise 补丁错误("PATCH_STRATEGY_NOT_L201", f"B2 首轮只消费：{','.join(sorted(allowed_sources))}")
    if strategy.get("automatic_execution_eligible") is not True:
        raise 补丁错误("PATCH_NOT_ELIGIBLE", "候选策略未取得自动执行资格")
    if strategy.get("requires_generative_completion") is True:
        raise 补丁错误("GENERATIVE_PATCH_FORBIDDEN", "B2 禁止生成式补全文本")
    allowed_operations = set(rules.get("allowed_operations", []))
    if strategy.get("operation") not in allowed_operations:
        raise 补丁错误("PATCH_PRECONDITION_FAILED", f"B2 首轮只允许：{','.join(sorted(allowed_operations))}")
    for key in ["task_id", "project_id", "target_file", "anchor", "expected_text", "reason", "position"]:
        _strategy_text(strategy, key)
    _strategy_list(strategy, "acceptance_conditions")
    _strategy_list(strategy, "risks")
    if strategy["operation"] == "REPLACE":
        _strategy_text(strategy, "replacement_text")
    if strategy["operation"] == "APPEND":
        _strategy_text(strategy, "append_text")
    return _target_path(strategy, rules)


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
        "schema_version": "xcue.l3-patch-audit/2.0",
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
        "started_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "finished_at": "",
        "final_status": "",
        "decision": "",
        "decision_reason": "",
        "approver": "",
        "approval_time": "",
        "approval": None,
        "final_decision": None,
        "revalidation": None,
        "lineage": {
            "task_id": plan.task_id,
            "project_id": plan.project_id,
            "chapter_source": plan.chapter_source,
            "source_sha256": plan.source_sha256,
            "patch_sha256": plan.patch_sha256,
        },
        "candidate_sha256": "",
        "diff_sha256": "",
        "backup_path": "",
        "backup_sha256": "",
        "applied_sha256": "",
        "rollback_sha256": "",
        "final_source_sha256": "",
        "last_complete_artifact_sha256": "",
        "last_successful_stage": "",
        "error_code": "",
        "error_reason": "",
        "rollback_attempted": False,
        "rollback_succeeded": False,
        "是否尝试回滚": False,
        "回滚是否成功": False,
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


def _load_approval(path: Path | None, *, require_candidate_hash: bool) -> dict[str, Any]:
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
    if require_candidate_hash:
        required.append("candidate_sha256")
    for key in required:
        if not isinstance(data.get(key), str) or not data[key]:
            raise 补丁错误("PATCH_PRECONDITION_FAILED", f"审批记录缺少字段：{key}")
    return data


def _check_approval(plan: 补丁计划, approval: dict[str, Any]) -> None:
    if approval["approval_status"] != "APPROVED":
        raise 补丁错误("REJECTED", "审批记录不是 APPROVED")
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
        raise 补丁错误("REVALIDATION_FAILED", "审批绑定的正文哈希已过期")


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


def _finalize_marker_path(task_id: str, final_status: str, chapter_source: str, patch_sha256: str, candidate_sha256: str) -> Path:
    marker_id = _text_hash(f"{task_id}:{final_status}:{chapter_source}:{patch_sha256}:{candidate_sha256}")
    return ROOT / "运行记录" / "B2_FINAL_MARKERS" / f"{marker_id}.json"


def _terminal_identity(audit: dict[str, Any]) -> str:
    return _text_hash(
        ":".join(
            str(audit.get(key, ""))
            for key in ["task_id", "project_id", "chapter_source", "source_sha256", "candidate_sha256", "patch_sha256"]
        )
    )


def _terminal_marker_path(audit: dict[str, Any]) -> Path:
    return ROOT / "运行记录" / "B2_FINAL_MARKERS" / f"{_terminal_identity(audit)}.json"


def _load_ready_audit(path: Path) -> dict[str, Any]:
    payload = _read_json(path, "补丁审计")
    按结构文件校验(payload, SCHEMA_DIR / "第三层补丁审计结构.json", "READY L3 补丁审计")
    if payload.get("status") != "READY_FOR_ACCEPTANCE":
        raise 补丁错误("ABORTED", "正式采纳只接受 READY_FOR_ACCEPTANCE 审计")
    required = ["task_id", "project_id", "chapter_source", "source_sha256", "patch_sha256", "candidate_sha256", "diff_sha256", "候选正文", "unified_diff"]
    for key in required:
        if not isinstance(payload.get(key), str) or not payload.get(key):
            raise 补丁错误("ABORTED", f"READY_FOR_ACCEPTANCE 审计缺少字段：{key}")
    candidate = Path(str(payload["候选正文"]))
    diff_path = Path(str(payload["unified_diff"]))
    if not candidate.exists() or 计算文件哈希(candidate) != payload["candidate_sha256"]:
        raise 补丁错误("REVALIDATION_FAILED", "READY 候选正文血缘不匹配")
    if not diff_path.exists() or 计算文件哈希(diff_path) != payload["diff_sha256"]:
        raise 补丁错误("REVALIDATION_FAILED", "READY 补丁 diff 血缘不匹配")
    revalidation = payload.get("复验结果")
    if not isinstance(revalidation, dict):
        raise 补丁错误("REVALIDATION_FAILED", "READY 审计缺少复验结果")
    for key in ["report_json", "failure_packet"]:
        artifact = Path(str(revalidation.get(key, "")))
        if not artifact.exists():
            raise 补丁错误("REVALIDATION_FAILED", f"READY 复验产物不存在：{key}")
    snapshot = Path(str(revalidation.get("revalidation_snapshot", "")))
    if not snapshot.exists() or 计算文件哈希(snapshot) != payload["candidate_sha256"]:
        raise 补丁错误("REVALIDATION_FAILED", "READY 复验快照未绑定 candidate_sha256")
    report_json = Path(str(revalidation["report_json"]))
    report_sha256 = 计算文件哈希(report_json)
    payload["revalidation"] = {
        "report_json": str(report_json),
        "report_sha256": report_sha256,
        "failure_packet": str(revalidation.get("failure_packet", "")),
        "candidate_sha256": payload["candidate_sha256"],
        "accepted": _复验通过(revalidation),
    }
    if not _复验通过(revalidation):
        raise 补丁错误("REVALIDATION_FAILED", "READY 复验结果不满足正式采纳条件")
    return payload


def _record_terminal(
    audit: dict[str, Any],
    *,
    final_status: str,
    last_successful_stage: str,
    last_complete_artifact_sha256: str = "",
    error_code: str = "",
    error_reason: str = "",
    rollback_attempted: bool = False,
    rollback_succeeded: bool = False,
) -> dict[str, Any]:
    audit["status"] = final_status
    audit["final_status"] = final_status
    audit["last_successful_stage"] = last_successful_stage
    audit["last_complete_artifact_sha256"] = last_complete_artifact_sha256
    audit["error_code"] = error_code
    audit["error_reason"] = error_reason
    audit["是否尝试回滚"] = rollback_attempted
    audit["回滚是否成功"] = rollback_succeeded
    audit["rollback_attempted"] = rollback_attempted
    audit["rollback_succeeded"] = rollback_succeeded
    audit["finished_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    return audit


def _audit_final_decision(audit: dict[str, Any], approval: dict[str, Any], decision: str, reason: str) -> None:
    audit["decision"] = decision
    audit["decision_reason"] = reason
    audit["approver"] = approval["approver"]
    audit["approval_time"] = approval["approval_time"]
    audit["final_decision"] = {
        "task_id": approval["task_id"],
        "project_id": approval["project_id"],
        "chapter_source": approval["chapter_source"],
        "source_sha256": approval["source_sha256"],
        "candidate_sha256": approval.get("candidate_sha256", ""),
        "patch_sha256": approval["patch_sha256"],
        "decision": decision,
        "decision_maker": approval["approver"],
        "decision_time": approval["approval_time"],
        "decision_reason": reason,
    }


def _check_final_approval(ready: dict[str, Any], approval: dict[str, Any]) -> None:
    expected = {
        "task_id": ready["task_id"],
        "project_id": ready["project_id"],
        "chapter_source": ready["chapter_source"],
        "source_sha256": ready["source_sha256"],
        "candidate_sha256": ready.get("candidate_sha256", ""),
        "patch_sha256": ready["patch_sha256"],
    }
    for key, value in expected.items():
        if approval.get(key) != value:
            raise 补丁错误("REVALIDATION_FAILED", f"最终决定绑定字段不匹配：{key}")


def _write_final_marker(audit: dict[str, Any]) -> None:
    final_status = str(audit.get("final_status", ""))
    if final_status not in {"REJECTED", "APPLIED"}:
        return
    marker = _terminal_marker_path(audit)
    marker.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(audit, ensure_ascii=False, indent=2)
    try:
        with marker.open("x", encoding="utf-8", newline="") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        return


def _try_idempotent_final(audit: dict[str, Any], decision: str, target: Path) -> dict[str, Any] | None:
    marker = _terminal_marker_path(audit)
    if not marker.exists():
        return None
    payload = _read_json(marker, "正式采纳标记")
    requested_status = "APPLIED" if decision == "apply" else "REJECTED"
    existing_status = str(payload.get("final_status", ""))
    if existing_status == "APPLIED" and target.exists() and 计算文件哈希(target) != payload.get("candidate_sha256", ""):
        return None
    if existing_status != requested_status:
        payload["terminal_state_conflict"] = True
        payload["error_code"] = "TERMINAL_STATE_CONFLICT"
        payload["error_reason"] = f"已有互斥终态 {existing_status}，拒绝创建 {requested_status}"
    return payload


def _formal_l1_passed(payload: dict[str, Any]) -> bool:
    result = payload.get("复验结果", {})
    return isinstance(result, dict) and _复验通过(result)


def _run_apply_revalidation(target: Path, out_dir: Path, run_id: str) -> dict[str, Any]:
    return _run_l1(target, out_dir, run_id)


def _atomic_replace_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _write_backup(path: Path, data: bytes) -> tuple[Path, str]:
    backup_dir = path.parent / "_b2_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    original_sha256 = hashlib.sha256(data).hexdigest()
    backup = backup_dir / f"{path.stem}.{datetime.now().strftime('%Y%m%d-%H%M%S')}.{original_sha256[:12]}.{uuid.uuid4().hex}.bak.md"
    with backup.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    return backup, 计算文件哈希(backup)


def _atomic_replace_text(path: Path, text: str) -> None:
    原子写文本(path, text)


def _rollback_formal(target: Path, original_bytes: bytes, audit: dict[str, Any]) -> tuple[bool, str]:
    try:
        if _允许测试外部IO() and os.environ.get("XCUE_B2_FAIL_ROLLBACK_WRITE") == "1":
            raise OSError("pytest injected rollback failure")
        _atomic_replace_bytes(target, original_bytes)
        rollback_sha = 计算文件哈希(target)
        if _允许测试外部IO() and os.environ.get("XCUE_B2_CORRUPT_AFTER_ROLLBACK") == "1":
            target.write_text(target.read_text(encoding="utf-8") + "\npytest rollback corruption\n", encoding="utf-8")
            rollback_sha = 计算文件哈希(target)
        return rollback_sha == audit.get("source_sha256", ""), rollback_sha
    except OSError:
        return False, ""


def _safe_write_terminal_audit(out_dir: Path, payload: dict[str, Any], *, emergency: bool = False) -> None:
    if _允许测试外部IO() and os.environ.get("XCUE_B2_FAIL_FINAL_AUDIT_WRITE") == "1" and not emergency:
        raise OSError("pytest injected final audit write failure")
    if emergency:
        payload["emergency_audit"] = True
    _write_audit(out_dir, payload)


def _normalize_error(exc: BaseException) -> tuple[str, str]:
    if isinstance(exc, 补丁错误):
        return str(exc.details.get("reason", "APPLY_FAILED")), str(exc)
    if isinstance(exc, subprocess.TimeoutExpired):
        return "APPLY_REVALIDATION_TIMEOUT", str(exc)
    if isinstance(exc, OSError):
        return "FINAL_AUDIT_WRITE_FAILED", str(exc)
    return "POST_APPLY_EXCEPTION", str(exc)


def _finalize_reject(ready: dict[str, Any], approval: dict[str, Any], out_dir: Path, reason: str) -> dict[str, Any]:
    target = Path(str(ready["chapter_source"]))
    _check_final_approval(ready, approval)
    existing = _try_idempotent_final(ready, "reject", target)
    if existing is not None:
        _write_audit(out_dir, existing)
        return existing
    _audit_final_decision(ready, approval, "reject", reason)
    ready["candidate_sha256"] = approval.get("candidate_sha256", ready.get("candidate_sha256", ""))
    ready["final_source_sha256"] = 计算文件哈希(target)
    ready["正式正文保持不变"] = ready["final_source_sha256"] == ready["source_sha256"]
    payload = _record_terminal(
        ready,
        final_status="REJECTED",
        last_successful_stage="READY_FOR_ACCEPTANCE",
        last_complete_artifact_sha256=str(ready.get("candidate_sha256", "")),
    )
    _write_audit(out_dir, payload)
    _write_final_marker(payload)
    return payload


def _finalize_apply(ready: dict[str, Any], approval: dict[str, Any], out_dir: Path, reason: str, run_id: str) -> dict[str, Any]:
    target = Path(str(ready["chapter_source"]))
    candidate = Path(str(ready["候选正文"]))
    existing = _try_idempotent_final(ready, "apply", target)
    if existing is not None:
        _write_audit(out_dir, existing)
        return existing
    if not candidate.exists():
        raise 补丁错误("ABORTED", "候选正文不存在")
    if not _formal_l1_passed(ready):
        raise 补丁错误("REVALIDATION_FAILED", "候选正文未通过 L1 复验")
    current_source = 计算文件哈希(target)
    current_candidate = 计算文件哈希(candidate)
    if current_source != ready["source_sha256"] or approval["source_sha256"] != ready["source_sha256"]:
        raise 补丁错误("REVALIDATION_FAILED", "正式正文 source_sha256 已变化")
    if current_candidate != ready.get("candidate_sha256", "") or approval["candidate_sha256"] != ready.get("candidate_sha256", ""):
        raise 补丁错误("REVALIDATION_FAILED", "candidate_sha256 不匹配")
    if approval["patch_sha256"] != ready["patch_sha256"]:
        raise 补丁错误("REVALIDATION_FAILED", "patch_sha256 不匹配")
    if approval["project_id"] != ready["project_id"] or approval["chapter_source"] != ready["chapter_source"]:
        raise 补丁错误("REVALIDATION_FAILED", "审批绑定对象不匹配")
    _check_final_approval(ready, approval)

    original_bytes = target.read_bytes()
    approved_bytes = candidate.read_bytes()
    _audit_final_decision(ready, approval, "apply", reason)
    ready["candidate_sha256"] = current_candidate
    backup_path, backup_sha = _write_backup(target, original_bytes)
    ready["backup_path"] = str(backup_path)
    ready["backup_sha256"] = backup_sha
    try:
        if _允许测试外部IO() and os.environ.get("XCUE_B2_FAIL_FORMAL_REPLACE") == "1":
            raise OSError("pytest injected formal replace failure")
        _atomic_replace_bytes(target, approved_bytes)
    except OSError as exc:
        ready["final_source_sha256"] = 计算文件哈希(target)
        rolled_back, rollback_sha = _rollback_formal(target, original_bytes, ready)
        ready["rollback_sha256"] = rollback_sha
        ready["final_source_sha256"] = 计算文件哈希(target) if target.exists() else ready["final_source_sha256"]
        final_status = "ROLLED_BACK" if rolled_back else "APPLY_FAILED"
        payload = _record_terminal(
            ready,
            final_status=final_status,
            last_successful_stage="BACKUP_WRITTEN" if not rolled_back else "ROLLBACK_VERIFIED",
            last_complete_artifact_sha256=rollback_sha if rolled_back else backup_sha,
            error_code="APPLY_FAILED",
            error_reason=str(exc),
            rollback_attempted=True,
            rollback_succeeded=rolled_back,
        )
        _write_audit(out_dir, payload)
        raise 补丁错误("APPLY_FAILED", f"正式正文原子替换失败：{exc}", ExitCode.BLOCKED)

    try:
        ready["applied_sha256"] = 计算文件哈希(target)
        ready["final_source_sha256"] = ready["applied_sha256"]
        if _允许测试外部IO() and os.environ.get("XCUE_B2_CORRUPT_AFTER_APPLY") == "1":
            target.write_text(target.read_text(encoding="utf-8") + "\npytest apply corruption\n", encoding="utf-8")
            ready["applied_sha256"] = 计算文件哈希(target)
            ready["final_source_sha256"] = ready["applied_sha256"]
        if ready["applied_sha256"] != current_candidate:
            raise 补丁错误("APPLY_FAILED", "正式正文哈希不等于 candidate_sha256")
        if _允许测试外部IO() and os.environ.get("XCUE_B2_FAIL_APPLY_REVALIDATION_TIMEOUT") == "1":
            raise subprocess.TimeoutExpired(cmd="pytest injected formal L1", timeout=1)
        if _允许测试外部IO() and os.environ.get("XCUE_B2_FAIL_AFTER_APPLY_PLAIN_EXCEPTION") == "1":
            raise RuntimeError("pytest injected post apply exception")
        formal_revalidation = _run_apply_revalidation(target, out_dir / "正式复验", f"{run_id}-APPLY")
        ready["正式复验结果"] = formal_revalidation
        if not _复验通过(formal_revalidation):
            raise 补丁错误("APPLY_FAILED", "应用后正式正文 L1 复验失败")
        payload = _record_terminal(
            ready,
            final_status="APPLIED",
            last_successful_stage="FORMAL_REVALIDATED",
            last_complete_artifact_sha256=ready["applied_sha256"],
        )
        _safe_write_terminal_audit(out_dir, payload)
        _write_final_marker(payload)
        return payload
    except Exception as exc:
        error_code, error_reason = _normalize_error(exc)
        rolled_back, rollback_sha = _rollback_formal(target, original_bytes, ready)
        ready["rollback_sha256"] = rollback_sha
        ready["final_source_sha256"] = 计算文件哈希(target) if target.exists() else ""
        if rolled_back:
            payload = _record_terminal(
                ready,
                final_status="ROLLED_BACK",
                last_successful_stage="ROLLBACK_VERIFIED",
                last_complete_artifact_sha256=rollback_sha,
                error_code=error_code,
                error_reason=error_reason,
                rollback_attempted=True,
                rollback_succeeded=True,
            )
            _safe_write_terminal_audit(out_dir, payload, emergency=error_code == "FINAL_AUDIT_WRITE_FAILED")
            return payload
        payload = _record_terminal(
            ready,
            final_status="ROLLBACK_FAILED",
            last_successful_stage="APPLY_ATTEMPTED",
            last_complete_artifact_sha256=ready.get("applied_sha256", backup_sha),
            error_code=error_code,
            error_reason=error_reason,
            rollback_attempted=True,
            rollback_succeeded=False,
        )
        _write_audit(out_dir, payload)
        raise 补丁错误("ROLLBACK_FAILED", str(exc), ExitCode.BLOCKED)


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
    l2_report: Path | None,
    audit_json: Path | None,
    out_dir: Path,
    run_id: str,
    approval_path: Path | None = None,
    plan_only: bool = False,
    final_decision: str | None = None,
    decision_reason: str = "",
    protocol_rules: Any | None = None,
) -> dict[str, Any]:
    rules = _patch_rules(protocol_rules)
    if final_decision:
        if audit_json is None:
            raise 补丁错误("ABORTED", "正式采纳缺少审计文件")
        if rules.get("requires_final_decision") is not True:
            raise 补丁错误("PATCH_RULES_INVALID", "patch_execution 必须要求最终决定")
        ready = _load_ready_audit(audit_json)
        target = _resolve_io_path(str(ready["chapter_source"]))
        if str(ready.get("project_id", "")) not in set(rules.get("allowed_projects", [])):
            raise 补丁错误("PROJECT_NOT_ALLOWED", "B2 首轮项目不在 patch_execution.allowed_projects")
        if str(ready.get("operation", "")) not in set(rules.get("allowed_operations", [])):
            raise 补丁错误("PATCH_PRECONDITION_FAILED", "READY 审计操作不在 patch_execution.allowed_operations")
        approval = _load_approval(approval_path, require_candidate_hash=True)
        if approval.get("approval_status") != "APPROVED":
            raise 补丁错误("ABORTED", "缺少最终批准记录")
        if final_decision == "reject":
            return _finalize_reject(ready, approval, out_dir, decision_reason)
        if final_decision == "apply":
            return _finalize_apply(ready, approval, out_dir, decision_reason, run_id)
        raise 补丁错误("ABORTED", "不支持的最终决定")

    if l2_report is None:
        raise 补丁错误("ABORTED", "缺少 L2 报告")
    strategy = _load_strategy(l2_report)
    target = _validate_strategy(strategy, rules)
    plan = _make_plan(strategy, target)
    if plan_only:
        payload = _write_plan(out_dir, plan, run_id)
        payload["finished_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        _write_audit(out_dir, payload)
        return payload

    if rules.get("requires_candidate_approval") is not True:
        raise 补丁错误("PATCH_RULES_INVALID", "patch_execution 必须要求候选审批")
    approval = _load_approval(approval_path, require_candidate_hash=False)
    before = target.read_text(encoding="utf-8")
    before_hash = 计算文件哈希(target)
    if approval["approval_status"] != "APPROVED":
        raise 补丁错误("REJECTED", "审批记录不是 APPROVED")
    if approval["patch_sha256"] != plan.patch_sha256:
        raise 补丁错误("PATCH_PRECONDITION_FAILED", "审批绑定的补丁哈希不一致")
    if approval["task_id"] != plan.task_id or approval["project_id"] != plan.project_id or approval["chapter_source"] != plan.chapter_source:
        raise 补丁错误("PATCH_PRECONDITION_FAILED", "审批记录与补丁计划不匹配")
    _check_marker(plan)
    # 锚点前置条件先于 source hash 终止，便于区分内容漂移中的定位失败。
    before.count(plan.anchor)
    after = _apply_patch(plan, before)
    if before_hash != plan.source_sha256 or approval["source_sha256"] != plan.source_sha256:
        raise 补丁错误("REVALIDATION_FAILED", "执行前正文哈希与计划哈希不一致")

    candidate = out_dir / "候选正文.md"
    diff_path = out_dir / "补丁.diff"
    audit = _plan_dict(plan, run_id, "PRECONDITION_CHECKED", out_dir=out_dir)
    audit["approval"] = approval
    audit["approver"] = approval["approver"]
    audit["approval_time"] = approval["approval_time"]
    try:
        if os.environ.get("XCUE_B2_FAIL_BEFORE_REPLACE") == "1":
            raise OSError("pytest injected write failure")
        原子写文本(candidate, after)
        原子写文本(diff_path, _diff(before, after, str(target), str(candidate)))
    except OSError as exc:
        audit["candidate_sha256"] = ""
        audit["候选正文"] = str(candidate)
        audit["unified_diff"] = str(diff_path)
        payload = _record_terminal(
            audit,
            final_status="EXECUTION_FAILED",
            last_successful_stage="PRECONDITION_CHECKED",
            error_code="EXECUTION_FAILED",
            error_reason=str(exc),
        )
        _write_audit(out_dir, payload)
        raise 补丁错误("EXECUTION_FAILED", f"候选正文写入失败：{exc}", ExitCode.INTERNAL_ERROR) from exc

    audit["status"] = "EXECUTED_IN_SANDBOX"
    audit["候选正文"] = str(candidate)
    audit["candidate_sha256"] = 计算文件哈希(candidate)
    audit["unified_diff"] = str(diff_path)
    audit["diff_sha256"] = 计算文件哈希(diff_path)
    audit["last_successful_stage"] = "EXECUTED_IN_SANDBOX"
    audit["正式正文保持不变"] = 计算文件哈希(target) == before_hash
    revalidation = _run_l1(candidate, out_dir / "复验", f"{run_id}-REVAL")
    audit["复验结果"] = revalidation
    report_path = Path(str(revalidation.get("report_json", "")))
    audit["revalidation"] = {
        "report_json": str(report_path),
        "report_sha256": 计算文件哈希(report_path) if report_path.exists() else "",
        "failure_packet": str(revalidation.get("failure_packet", "")),
        "candidate_sha256": audit["candidate_sha256"],
        "accepted": _复验通过(revalidation),
    }
    if not _复验通过(revalidation):
        payload = _record_terminal(
            audit,
            final_status="REVALIDATION_FAILED",
            last_successful_stage="EXECUTED_IN_SANDBOX",
            last_complete_artifact_sha256=audit["candidate_sha256"],
            error_code="REVALIDATION_FAILED",
            error_reason="候选正文 L1 复验失败",
        )
        _write_audit(out_dir, payload)
        raise 补丁错误("REVALIDATION_FAILED", "候选正文 L1 复验失败")
    audit["status"] = "READY_FOR_ACCEPTANCE"
    audit["last_successful_stage"] = "READY_FOR_ACCEPTANCE"
    audit["last_complete_artifact_sha256"] = audit["candidate_sha256"]
    audit["finished_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    _write_audit(out_dir, audit)
    _write_marker(plan, audit)
    return audit
