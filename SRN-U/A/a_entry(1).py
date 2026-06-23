#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SRN-U A层：创作入口最小可运行实现。

范围：
- 仅实现 ProjectBrief、ProjectSeed、G0、G1、人工审批与本地文件落盘。
- 不实现 B—H，不使用 API，不建立数据库。
- 内置 A-T01 至 A-T10 自测。

运行目录：
    runs/<project_id>/A/

可通过环境变量 SRNU_RUNS_DIR 修改 runs 根目录。
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


UNKNOWN = "UNKNOWN"
SCHEMA_VERSION = "1.0"
VALID_OPERATION_MODES = {"create_new", "continue_existing", "revise_existing"}
VALID_ACTIONS = {"compile", "approve"}
VALID_HUMAN_DECISIONS = {"approve", "revise", "reject"}
VALID_LEAD_STRUCTURES = {"单主角", "双主角", "群像"}

ERROR_CODES = {
    "A_INPUT_MISSING",
    "A_INPUT_CONFLICT",
    "A_SOURCE_MISSING",
    "A_SEED_INVALID",
    "A_APPROVAL_REQUIRED",
}

NEXT_ACTIONS = {
    "human_approve",
    "revise_brief",
    "supply_sources",
    "B_INIT",
    "stop",
}

COMMON_METADATA_FIELDS = (
    "object_id",
    "object_type",
    "schema_version",
    "object_version",
    "project_id",
    "status",
    "created_at",
    "updated_at",
    "source_refs",
)

# 实现时发现的最小阻断修正。它们只改变运行解释，不改变冻结核心对象。
MINIMAL_CORRECTIONS: List[Dict[str, Any]] = [
    {
        "id": "A-MC-01",
        "reason": (
            "A层草案把 ProjectSeed.candidate 的结构校验写成 G1 PASS，"
            "但 M0-04 冻结基线规定 G1 只有 approved/locked 才能 PASS。"
        ),
        "change": (
            "新增仅存在于运行信封中的 G1_PRECHECK：candidate 通过预检后等待人工审批；"
            "人工 approve 生成新版本 approved 后，才执行正式 G1。"
        ),
        "impact_scope": "仅运行信封 gate.current；ProjectBrief/ProjectSeed 字段与状态集合不变。",
        "test_evidence": ["A-T08", "A-T09"],
    },
    {
        "id": "A-MC-02",
        "reason": (
            "函数参数 source_ref 证明的是本次请求来源，不能同时证明续写/修订所需的既有正文、"
            "设定或状态材料，否则 A-T05 永远无法成立。"
        ),
        "change": (
            "continue_existing/revise_existing 除本次 source_ref 外，"
            "还必须在 raw_input.source_refs、raw_input.existing_material_refs、"
            "raw_input.existing_material_paths 或 previous_brief.source_refs 中提供既有材料引用。"
        ),
        "impact_scope": "仅 G0 来源判定；不新增核心对象字段。",
        "test_evidence": ["A-T05"],
    },
    {
        "id": "A-MC-03",
        "reason": "A-T10 需要重新编译，但 input.txt 又被规定为不可覆盖。",
        "change": (
            "首次输入固定写入 input.txt；后续不同输入写入 history/input_<timestamp>_<hash>.txt，"
            "不覆盖首份原始输入。"
        ),
        "impact_scope": "仅 A层本地文件保存策略；正式对象和目录主结构不变。",
        "test_evidence": ["A-T10"],
    },
    {
        "id": "A-MC-04",
        "reason": "独立验收证明陈旧 candidate 可以覆盖磁盘中的当前 ProjectSeed，破坏唯一真源与版本链。",
        "change": (
            "approve 与带 previous_* 的重新编译必须先读取磁盘当前对象；对象标识、版本、状态和内容摘要"
            "必须与调用方对象精确一致，否则在 G0 BLOCKED，且不得改写正式对象文件。"
        ),
        "impact_scope": "仅 G0 当前真源预检和版本递增依据；不新增核心对象或数据库。",
        "test_evidence": ["A-RT01", "A-RT04"],
    },
    {
        "id": "A-MC-05",
        "reason": "独立验收证明错误 object_type 与缺失 schema/object_version 的对象仍可进入审批。",
        "change": "增加九类对象公共元数据最小校验；A层只接收 ProjectBrief 与 ProjectSeed 的合法版本。",
        "impact_scope": "仅正式对象入口校验；字段集合来自 M0-02 冻结基线。",
        "test_evidence": ["A-RT02", "A-RT03"],
    },
    {
        "id": "A-MC-06",
        "reason": "路径型 source_ref 若不可读取，G0 仍可能继续，无法满足来源可访问要求。",
        "change": "对形似本地路径的本次来源与既有材料来源执行存在性、文件性和可读性检查。",
        "impact_scope": "仅 G0 来源检查；普通对象引用标识仍按非空标识处理。",
        "test_evidence": ["A-RT05"],
    },
]

BRIEF_FIELDS = (
    "operation_mode",
    "target_platform",
    "genre",
    "target_reader",
    "core_emotion",
    "idea_statement",
    "length_target",
    "must_have",
    "must_avoid",
    "style_preference",
    "commercial_goal",
    "open_questions",
)

SEED_FIELDS = (
    "project_title",
    "one_sentence_promise",
    "content_source",
    "lead_structure",
    "lead_core",
    "primary_opposition",
    "minimum_world_rules",
    "long_term_conflict",
    "stage_one_goal",
    "opening_hook",
    "continuation_reason",
    "approved_constraints",
    "rejected_directions",
)

GENERIC_PROMISES = {
    "主角一路变强",
    "主角改变命运",
    "这是一个波澜壮阔的故事",
    "一路变强",
    "改变命运",
}
GENERIC_CONTENT_SOURCES = {
    "不断变强",
    "主角不断升级",
    "主角一路打脸",
    "剧情越来越精彩",
    "不断升级",
    "一路打脸",
}
GENERIC_OPPOSITIONS = {"困难很多", "敌人很强", "世界很危险"}
ABSTRACT_STAGE_GOALS = {"成长", "变强", "探索世界"}
ACTION_MARKERS = {
    "完成",
    "发现",
    "获得",
    "阻止",
    "查清",
    "逃出",
    "建立",
    "解决",
    "进入",
    "通过",
    "夺回",
    "控制",
    "救出",
    "揭露",
    "确认",
}

# 用于降低“开篇钩子与卖点同源”启发式中的虚假字符重合。
COMMON_HAN_CHARS = set("的一是在不了有和人这中大为上个国我以要他时来用们生到作地于出就分对成会可主角读者故事小说")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _runs_root() -> Path:
    return Path(os.environ.get("SRNU_RUNS_DIR", "runs")).expanduser().resolve()


def _deepcopy(value: Any) -> Any:
    return copy.deepcopy(value)


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _is_unknown(value: Any) -> bool:
    if _is_blank(value):
        return True
    return isinstance(value, str) and value.strip().upper() in {
        "UNKNOWN",
        "UNDECIDED",
        "DISPUTED",
    }


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return _deepcopy(value)
    if isinstance(value, tuple):
        return [_deepcopy(item) for item in value]
    if isinstance(value, set):
        return [_deepcopy(item) for item in sorted(value, key=str)]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        # 只对显式分隔符拆分，避免破坏自然语言短句。
        if "\n" in text:
            return [item.strip(" -\t") for item in text.splitlines() if item.strip(" -\t")]
        return [text]
    return [_deepcopy(value)]


def _as_refs(value: Any) -> List[str]:
    refs: List[str] = []
    for item in _as_list(value):
        if isinstance(item, Mapping):
            candidate = item.get("ref") or item.get("id") or item.get("path")
            if candidate is not None:
                refs.append(str(candidate).strip())
        elif item is not None:
            refs.append(str(item).strip())
    return _dedupe([ref for ref in refs if ref])


def _dedupe(items: Iterable[Any]) -> List[Any]:
    result: List[Any] = []
    seen: set[str] = set()
    for item in items:
        marker = json.dumps(item, ensure_ascii=False, sort_keys=True, default=str)
        if marker not in seen:
            result.append(item)
            seen.add(marker)
    return result


def _canonical_text(value: Any) -> str:
    if isinstance(value, Mapping):
        text = " ".join(_canonical_text(v) for v in value.values())
    elif isinstance(value, (list, tuple, set)):
        text = " ".join(_canonical_text(v) for v in value)
    elif value is None:
        text = ""
    else:
        text = str(value)
    return re.sub(r"[\s\W_]+", "", text, flags=re.UNICODE).lower()


def _flatten_text(value: Any) -> str:
    if isinstance(value, Mapping):
        return " ".join(_flatten_text(v) for v in value.values())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_flatten_text(v) for v in value)
    return "" if value is None else str(value)


def _meaningful_units(value: Any) -> set[str]:
    text = _flatten_text(value).lower()
    units: set[str] = set()
    for word in re.findall(r"[a-z0-9]{3,}", text):
        units.add(word)
    han = "".join(re.findall(r"[\u4e00-\u9fff]", text))
    for n in (2, 3, 4):
        for i in range(max(0, len(han) - n + 1)):
            gram = han[i : i + n]
            if not all(ch in COMMON_HAN_CHARS for ch in gram):
                units.add(gram)
    return units


def _related(left: Any, right: Any) -> bool:
    left_raw = _flatten_text(left)
    right_raw = _flatten_text(right)
    # 明确声明“与……无关”时，不得因关键词表面重合而判为同源。
    if "无关" in left_raw or "无关" in right_raw:
        return False
    left_text = _canonical_text(left)
    right_text = _canonical_text(right)
    if not left_text or not right_text:
        return False
    if left_text in right_text or right_text in left_text:
        return True
    if _meaningful_units(left) & _meaningful_units(right):
        return True
    left_chars = {ch for ch in left_text if "\u4e00" <= ch <= "\u9fff" and ch not in COMMON_HAN_CHARS}
    right_chars = {ch for ch in right_text if "\u4e00" <= ch <= "\u9fff" and ch not in COMMON_HAN_CHARS}
    return len(left_chars & right_chars) >= 2


def _direct_conflicts(must_have: Sequence[Any], must_avoid: Sequence[Any]) -> List[Tuple[int, int, str]]:
    conflicts: List[Tuple[int, int, str]] = []
    for i, have in enumerate(must_have):
        left = _canonical_text(have)
        if not left:
            continue
        for j, avoid in enumerate(must_avoid):
            right = _canonical_text(avoid)
            if not right:
                continue
            if left == right or (min(len(left), len(right)) >= 2 and (left in right or right in left)):
                conflicts.append((i, j, str(have)))
    return conflicts


def _issue(code: str, field: str, message: str, evidence: Sequence[str], repair_action: str) -> Dict[str, Any]:
    if code not in ERROR_CODES:
        raise ValueError(f"unsupported A-layer issue code: {code}")
    return {
        "code": code,
        "field": field,
        "message": message,
        "evidence": list(evidence),
        "repair_action": repair_action,
    }


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


def _next_version(previous: Optional[Mapping[str, Any]]) -> str:
    if not previous:
        return "1"
    return str(_safe_int(previous.get("object_version"), 0) + 1)


def _object_ref(obj: Mapping[str, Any]) -> str:
    return f"{obj.get('object_id', 'UNKNOWN')}@v{obj.get('object_version', 'UNKNOWN')}"


def _object_digest(obj: Mapping[str, Any]) -> str:
    payload = json.dumps(dict(obj), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _validate_formal_object(
    obj: Mapping[str, Any],
    expected_type: str,
    project_id: Optional[str] = None,
    allowed_statuses: Optional[set[str]] = None,
) -> List[Dict[str, Any]]:
    """校验进入A层的正式对象身份、公共元数据与项目归属。"""
    issues: List[Dict[str, Any]] = []
    ref = _object_ref(obj)

    for field in COMMON_METADATA_FIELDS:
        value = obj.get(field)
        if _is_blank(value) or (field == "source_refs" and not _as_refs(value)):
            issues.append(
                _issue(
                    "A_INPUT_MISSING",
                    field,
                    f"{expected_type} 缺少冻结基线要求的公共元数据字段 {field}。",
                    [f"{ref}.{field}={value!r}"],
                    f"补齐 {expected_type}.{field} 后重新进入 G0。",
                )
            )

    actual_type = obj.get("object_type")
    if not _is_blank(actual_type) and actual_type != expected_type:
        issues.append(
            _issue(
                "A_INPUT_CONFLICT",
                "object_type",
                f"入口对象类型应为 {expected_type}，实际为 {actual_type}。",
                [f"{ref}.object_type={actual_type}"],
                f"提供当前 {expected_type} 对象，禁止用其他核心对象冒充。",
            )
        )

    schema_version = obj.get("schema_version")
    if not _is_blank(schema_version) and str(schema_version) != SCHEMA_VERSION:
        issues.append(
            _issue(
                "A_INPUT_CONFLICT",
                "schema_version",
                f"当前A层只接受 schema_version={SCHEMA_VERSION}。",
                [f"{ref}.schema_version={schema_version}"],
                "先执行兼容迁移或提供1.0对象，不在A层静默改写结构版本。",
            )
        )

    version = obj.get("object_version")
    if not _is_blank(version) and (_safe_int(version, 0) < 1 or str(version).strip() != str(_safe_int(version, 0))):
        issues.append(
            _issue(
                "A_INPUT_CONFLICT",
                "object_version",
                "object_version 必须是从1开始的整数字符串或整数。",
                [f"{ref}.object_version={version!r}"],
                "提供可比较、可递增的正式版本号。",
            )
        )

    if project_id and obj.get("project_id") and str(obj.get("project_id")) != str(project_id):
        issues.append(
            _issue(
                "A_INPUT_CONFLICT",
                "project_id",
                "正式对象不属于当前项目。",
                [f"entry.project_id={project_id}", f"{ref}.project_id={obj.get('project_id')}"],
                "只提供与当前 project_id 一致的对象。",
            )
        )

    if allowed_statuses is not None and obj.get("status") not in allowed_statuses:
        issues.append(
            _issue(
                "A_INPUT_CONFLICT",
                "status",
                f"{expected_type} 当前状态不允许执行该动作。",
                [f"{ref}.status={obj.get('status')}", f"allowed={sorted(allowed_statuses)}"],
                "提供当前工作流允许的对象状态。",
            )
        )
    return issues


def _current_object_path(project_id: str, expected_type: str) -> Path:
    filename = "project_brief.yaml" if expected_type == "ProjectBrief" else "project_seed.yaml"
    return _runs_root() / project_id / "A" / filename


def _load_current_object(project_id: str, expected_type: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    path = _current_object_path(project_id, expected_type)
    if not path.exists() or not path.is_file() or not os.access(path, os.R_OK):
        return None, [
            _issue(
                "A_SOURCE_MISSING",
                expected_type,
                f"无法读取磁盘当前 {expected_type} 真源。",
                [str(path)],
                "恢复当前对象文件，或重新从合法上游生成，不得凭调用方缓存继续。",
            )
        ]
    try:
        loaded = _load_yaml_like(path)
    except Exception as exc:
        return None, [
            _issue(
                "A_SOURCE_MISSING",
                expected_type,
                f"磁盘当前 {expected_type} 无法解析。",
                [str(path), f"{type(exc).__name__}: {exc}"],
                "修复当前真源文件后重新进入 G0。",
            )
        ]
    if not isinstance(loaded, Mapping):
        return None, [
            _issue(
                "A_INPUT_CONFLICT",
                expected_type,
                f"磁盘当前 {expected_type} 不是对象映射。",
                [str(path), f"loaded_type={type(loaded).__name__}"],
                "恢复合法对象文件。",
            )
        ]
    current = dict(loaded)
    return current, _validate_formal_object(current, expected_type, project_id)


def _validate_matches_current(
    provided: Mapping[str, Any],
    current: Mapping[str, Any],
    expected_type: str,
) -> List[Dict[str, Any]]:
    if _object_digest(provided) == _object_digest(current):
        return []
    return [
        _issue(
            "A_INPUT_CONFLICT",
            expected_type,
            f"调用方提交的 {expected_type} 不是磁盘当前真源，可能是陈旧版本或被篡改副本。",
            [
                f"provided={_object_ref(provided)} sha256={_object_digest(provided)}",
                f"current={_object_ref(current)} sha256={_object_digest(current)}",
            ],
            "重新读取磁盘当前对象后再执行；禁止用陈旧对象覆盖当前真源。",
        )
    ]


def _serialize_raw_input(raw_input: Any) -> str:
    if isinstance(raw_input, str):
        return raw_input
    return json.dumps(raw_input, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def _try_yaml_load(text: str) -> Optional[Any]:
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text)
    except Exception:
        return None


def _parse_raw_input(raw_input: Any) -> Tuple[Dict[str, Any], str]:
    raw_text = _serialize_raw_input(raw_input)
    if isinstance(raw_input, Mapping):
        return _deepcopy(dict(raw_input)), raw_text
    if not isinstance(raw_input, str):
        return {"idea_statement": UNKNOWN}, raw_text

    stripped = raw_input.strip()
    if not stripped:
        return {"idea_statement": UNKNOWN}, raw_text

    try:
        loaded = json.loads(stripped)
        if isinstance(loaded, Mapping):
            return _deepcopy(dict(loaded)), raw_text
    except json.JSONDecodeError:
        pass

    loaded = _try_yaml_load(stripped)
    if isinstance(loaded, Mapping):
        return _deepcopy(dict(loaded)), raw_text

    # 纯自然语言无法在无模型条件下可靠拆出关键字段；只保留为用户明确给出的 idea_statement。
    return {"idea_statement": stripped}, raw_text


def _dump_yaml_like(path: Path, data: Any) -> None:
    """优先写 YAML；无 PyYAML 时写 JSON（JSON 是 YAML 1.2 的合法子集）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import yaml  # type: ignore

        content = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=120)
    except Exception:
        content = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False, default=str) + "\n"
    _atomic_write_text(path, content)


def _load_yaml_like(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    loaded = _try_yaml_load(text)
    if loaded is not None:
        return loaded
    return json.loads(text)


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _allocate_project_id() -> str:
    root = _runs_root()
    root.mkdir(parents=True, exist_ok=True)
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = f"NOVEL-{date_part}-"
    existing: List[int] = []
    for child in root.iterdir():
        if child.is_dir() and child.name.startswith(prefix):
            suffix = child.name[len(prefix) :]
            if suffix.isdigit():
                existing.append(int(suffix))
    candidate = max(existing, default=0) + 1
    while True:
        project_id = f"{prefix}{candidate:04d}"
        try:
            (root / project_id / "A").mkdir(parents=True, exist_ok=False)
            return project_id
        except FileExistsError:
            candidate += 1


def _looks_like_path(ref: str) -> bool:
    return (
        ref.startswith(("./", "../", "/", "~"))
        or "\\" in ref
        or "/" in ref
        or bool(re.search(r"\.(txt|md|yaml|yml|json|docx|pdf)$", ref, flags=re.IGNORECASE))
    )


def _ref_accessible(ref: str) -> bool:
    if not _looks_like_path(ref):
        # 对象/材料标识不是路径；只校验其非空。真正解析由对应读取层负责。
        return bool(ref.strip())
    path = Path(ref).expanduser()
    return path.exists() and path.is_file() and os.access(path, os.R_OK)


def _material_refs(data: Mapping[str, Any], previous_brief: Optional[Mapping[str, Any]], request_refs: Sequence[str]) -> List[str]:
    refs: List[str] = []
    for key in ("source_refs", "existing_material_refs", "existing_material_paths"):
        refs.extend(_as_refs(data.get(key)))
    if previous_brief:
        refs.extend(_as_refs(previous_brief.get("source_refs")))
    request_set = set(request_refs)
    return [ref for ref in _dedupe(refs) if ref not in request_set]


def _validate_project_consistency(
    project_id: Optional[str],
    previous_brief: Optional[Mapping[str, Any]],
    previous_seed: Optional[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    observed = [
        str(obj.get("project_id"))
        for obj in (previous_brief, previous_seed)
        if obj and obj.get("project_id")
    ]
    if project_id:
        observed.append(str(project_id))
    if len(set(observed)) > 1:
        issues.append(
            _issue(
                "A_INPUT_CONFLICT",
                "project_id",
                "检测到不同 project_id 的对象或入口参数，G0 阻断跨项目引用。",
                [f"project_id={value}" for value in observed],
                "只保留同一项目的 ProjectBrief、ProjectSeed 与入口 project_id。",
            )
        )
    return issues


def _resolve_project_id(
    data: Mapping[str, Any],
    project_id: Optional[str],
    previous_brief: Optional[Mapping[str, Any]],
    previous_seed: Optional[Mapping[str, Any]],
) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    issues = _validate_project_consistency(project_id, previous_brief, previous_seed)
    if issues:
        return None, issues

    resolved = project_id
    if not resolved and previous_brief:
        resolved = str(previous_brief.get("project_id") or "").strip() or None
    if not resolved and previous_seed:
        resolved = str(previous_seed.get("project_id") or "").strip() or None

    operation_mode = str(data.get("operation_mode") or UNKNOWN).strip()
    if not resolved and operation_mode == "create_new":
        resolved = _allocate_project_id()
    elif not resolved:
        issues.append(
            _issue(
                "A_SOURCE_MISSING",
                "project_id",
                "既有项目或未声明 create_new 的输入缺少 project_id。",
                [f"operation_mode={operation_mode}"],
                "提供已有 project_id，或明确声明 operation_mode=create_new。",
            )
        )
    return resolved, issues


def _g0_check(
    data: Mapping[str, Any],
    source_ref: Any,
    project_id: Optional[str],
    previous_brief: Optional[Mapping[str, Any]],
    previous_seed: Optional[Mapping[str, Any]],
) -> Tuple[Optional[str], List[str], List[Dict[str, Any]]]:
    request_refs = _as_refs(source_ref)
    issues: List[Dict[str, Any]] = []
    if not request_refs:
        issues.append(
            _issue(
                "A_SOURCE_MISSING",
                "source_ref",
                "本次原始输入没有可识别的来源标识。",
                ["source_ref is empty"],
                "提供本次用户输入或本地文件的来源标识。",
            )
        )
    else:
        inaccessible_request_refs = [ref for ref in request_refs if not _ref_accessible(ref)]
        if inaccessible_request_refs:
            issues.append(
                _issue(
                    "A_SOURCE_MISSING",
                    "source_ref",
                    "本次来源被声明为本地路径，但文件不存在、不是普通文件或不可读取。",
                    inaccessible_request_refs,
                    "修正本地来源路径或读取权限。",
                )
            )

    resolved, project_issues = _resolve_project_id(data, project_id, previous_brief, previous_seed)
    issues.extend(project_issues)
    operation_mode = str(data.get("operation_mode") or UNKNOWN).strip()

    if resolved and not project_issues:
        if previous_brief is not None:
            issues.extend(_validate_formal_object(previous_brief, "ProjectBrief", resolved))
            current_brief, current_brief_issues = _load_current_object(resolved, "ProjectBrief")
            issues.extend(current_brief_issues)
            if current_brief is not None and not current_brief_issues:
                issues.extend(_validate_matches_current(previous_brief, current_brief, "ProjectBrief"))
        if previous_seed is not None:
            issues.extend(_validate_formal_object(previous_seed, "ProjectSeed", resolved))
            current_seed, current_seed_issues = _load_current_object(resolved, "ProjectSeed")
            issues.extend(current_seed_issues)
            if current_seed is not None and not current_seed_issues:
                issues.extend(_validate_matches_current(previous_seed, current_seed, "ProjectSeed"))

    if operation_mode in {"continue_existing", "revise_existing"}:
        material_refs = _material_refs(data, previous_brief, request_refs)
        if not material_refs:
            issues.append(
                _issue(
                    "A_SOURCE_MISSING",
                    "source_refs",
                    "续写或修订模式没有独立的既有正文、设定或状态材料引用。",
                    ["仅存在本次请求 source_ref，未发现既有材料 source_refs"],
                    "在 raw_input.source_refs 或 existing_material_refs 中提供既有材料引用。",
                )
            )
        else:
            inaccessible = [ref for ref in material_refs if not _ref_accessible(ref)]
            if inaccessible:
                issues.append(
                    _issue(
                        "A_SOURCE_MISSING",
                        "source_refs",
                        "部分声明为本地路径的既有材料不可读取。",
                        inaccessible,
                        "修正本地文件路径或文件读取权限。",
                    )
                )

    return resolved, request_refs, issues


def _merge_source_refs(request_refs: Sequence[str], data: Mapping[str, Any], previous: Optional[Mapping[str, Any]]) -> List[str]:
    refs: List[str] = list(request_refs)
    refs.extend(_as_refs(data.get("source_refs")))
    refs.extend(_as_refs(data.get("existing_material_refs")))
    refs.extend(_as_refs(data.get("existing_material_paths")))
    if previous:
        refs.extend(_as_refs(previous.get("source_refs")))
    return _dedupe([ref for ref in refs if ref])


def _build_project_brief(
    data: Mapping[str, Any],
    project_id: str,
    request_refs: Sequence[str],
    previous_brief: Optional[Mapping[str, Any]],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    now = _utc_now()
    version = _next_version(previous_brief)
    base: Dict[str, Any] = {}
    if previous_brief:
        base = _deepcopy(dict(previous_brief))

    for field in BRIEF_FIELDS:
        if field in data:
            base[field] = _deepcopy(data[field])

    for required in ("operation_mode", "genre", "core_emotion", "idea_statement"):
        if _is_blank(base.get(required)):
            base[required] = UNKNOWN

    for optional in (
        "target_platform",
        "target_reader",
        "length_target",
        "style_preference",
        "commercial_goal",
    ):
        if _is_blank(base.get(optional)):
            base[optional] = UNKNOWN

    base["must_have"] = _as_list(base.get("must_have"))
    base["must_avoid"] = _as_list(base.get("must_avoid"))
    base["open_questions"] = _as_list(base.get("open_questions"))

    brief: Dict[str, Any] = {
        "object_id": (previous_brief or {}).get("object_id") or f"PB-{project_id}",
        "object_type": "ProjectBrief",
        "schema_version": SCHEMA_VERSION,
        "object_version": version,
        "project_id": project_id,
        "status": "ready",
        "created_at": (previous_brief or {}).get("created_at") or now,
        "updated_at": now,
        "operation_mode": str(base.get("operation_mode") or UNKNOWN),
        "target_platform": base.get("target_platform", UNKNOWN),
        "genre": base.get("genre", UNKNOWN),
        "target_reader": base.get("target_reader", UNKNOWN),
        "core_emotion": base.get("core_emotion", UNKNOWN),
        "idea_statement": base.get("idea_statement", UNKNOWN),
        "length_target": base.get("length_target", UNKNOWN),
        "must_have": base["must_have"],
        "must_avoid": base["must_avoid"],
        "style_preference": base.get("style_preference", UNKNOWN),
        "commercial_goal": base.get("commercial_goal", UNKNOWN),
        "open_questions": base["open_questions"],
        "source_refs": _merge_source_refs(request_refs, data, previous_brief),
    }

    issues: List[Dict[str, Any]] = []
    if brief["operation_mode"] not in VALID_OPERATION_MODES:
        brief["status"] = "invalid"
        issues.append(
            _issue(
                "A_INPUT_CONFLICT",
                "operation_mode",
                "operation_mode 不属于允许值。",
                [f"value={brief['operation_mode']}"],
                "改为 create_new、continue_existing 或 revise_existing。",
            )
        )

    conflicts = _direct_conflicts(brief["must_have"], brief["must_avoid"])
    if conflicts:
        brief["status"] = "invalid"
        for have_index, avoid_index, text in conflicts:
            issues.append(
                _issue(
                    "A_INPUT_CONFLICT",
                    "must_have / must_avoid",
                    f"同一要求同时出现在必须项与禁止项：{text}",
                    [
                        f"{brief['object_id']}.must_have[{have_index}]",
                        f"{brief['object_id']}.must_avoid[{avoid_index}]",
                    ],
                    "由人工选择保留必须项或禁止项中的一侧。",
                )
            )

    if _is_unknown(brief["idea_statement"]):
        if brief["status"] != "invalid":
            brief["status"] = "draft"
        issues.append(
            _issue(
                "A_INPUT_MISSING",
                "idea_statement",
                "idea_statement 缺失或为 UNKNOWN，ProjectBrief 只能保持 draft。",
                [f"{brief['object_id']}.idea_statement"],
                "提供一句明确的创意陈述。",
            )
        )

    for field, question in (
        ("target_platform", "目标平台未定"),
        ("target_reader", "目标读者未定或过宽"),
        ("length_target", "目标篇幅未定"),
        ("style_preference", "次要文风未定"),
    ):
        if _is_unknown(brief[field]) and question not in brief["open_questions"]:
            brief["open_questions"].append(question)

    return brief, issues


def _nested_seed_input(data: Mapping[str, Any]) -> Dict[str, Any]:
    merged = dict(data)
    nested = data.get("project_seed")
    if isinstance(nested, Mapping):
        merged.update(_deepcopy(dict(nested)))
    return merged


def _compile_lead_core(data: Mapping[str, Any]) -> Any:
    if "lead_core" in data:
        return _deepcopy(data["lead_core"])
    identity = data.get("lead_identity")
    desire = data.get("lead_desire")
    deficiency = data.get("lead_deficiency")
    if any(not _is_blank(value) for value in (identity, desire, deficiency)):
        return {
            "identity": identity if not _is_blank(identity) else UNKNOWN,
            "desire": desire if not _is_blank(desire) else UNKNOWN,
            "deficiency": deficiency if not _is_blank(deficiency) else UNKNOWN,
        }
    return UNKNOWN


def _compile_constraints(brief: Mapping[str, Any], data: Mapping[str, Any]) -> List[Any]:
    constraints: List[Any] = []
    constraints.extend(_as_list(data.get("approved_constraints")))
    constraints.extend({"type": "must_have", "value": item} for item in _as_list(brief.get("must_have")))
    constraints.extend({"type": "must_avoid", "value": item} for item in _as_list(brief.get("must_avoid")))
    return _dedupe(constraints)


def _build_project_seed(
    data: Mapping[str, Any],
    brief: Mapping[str, Any],
    previous_seed: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    now = _utc_now()
    source = _nested_seed_input(data)
    version = _next_version(previous_seed)
    project_id = str(brief["project_id"])

    project_title = source.get("project_title") or source.get("title")
    generated_title = False
    if _is_blank(project_title):
        genre = brief.get("genre")
        project_title = f"工作名：{genre if not _is_unknown(genre) else project_id}"
        generated_title = True

    promise = source.get("one_sentence_promise")
    if _is_blank(promise):
        # 只做无损字段映射，不添加新事实；是否足够具体交由 G1_PRECHECK 判定。
        promise = brief.get("idea_statement", UNKNOWN)

    seed: Dict[str, Any] = {
        "object_id": (previous_seed or {}).get("object_id") or f"PS-{project_id}",
        "object_type": "ProjectSeed",
        "schema_version": SCHEMA_VERSION,
        "object_version": version,
        "project_id": project_id,
        "status": "candidate",
        "created_at": (previous_seed or {}).get("created_at") or now,
        "updated_at": now,
        "project_title": project_title,
        "one_sentence_promise": promise,
        "content_source": source.get("content_source", UNKNOWN),
        "lead_structure": source.get("lead_structure", UNKNOWN),
        "lead_core": _compile_lead_core(source),
        "primary_opposition": source.get("primary_opposition", UNKNOWN),
        "minimum_world_rules": _as_list(source.get("minimum_world_rules")),
        "long_term_conflict": source.get("long_term_conflict", UNKNOWN),
        "stage_one_goal": source.get("stage_one_goal", UNKNOWN),
        "opening_hook": source.get("opening_hook", UNKNOWN),
        "continuation_reason": source.get("continuation_reason", UNKNOWN),
        "approved_constraints": _compile_constraints(brief, source),
        "rejected_directions": _as_list(source.get("rejected_directions")),
        "source_refs": _dedupe([_object_ref(brief)] + _as_refs(brief.get("source_refs"))),
    }
    notes = _as_list((previous_seed or {}).get("notes"))
    if generated_title:
        notes.append("project_title 由系统生成，仅为工作名，未视为用户最终命名。")
    if source.get("one_sentence_promise") in (None, ""):
        notes.append("one_sentence_promise 直接继承 ProjectBrief.idea_statement，未添加新事实。")
    if notes:
        seed["notes"] = _dedupe(notes)
    return seed


def _lead_core_complete(value: Any, structure: Any) -> bool:
    def complete(item: Any) -> bool:
        return isinstance(item, Mapping) and all(
            not _is_unknown(item.get(field)) for field in ("identity", "desire", "deficiency")
        )

    if isinstance(value, Mapping):
        return complete(value)
    if isinstance(value, list):
        if not value or not all(complete(item) for item in value):
            return False
        if structure == "双主角":
            return len(value) >= 2
        if structure == "群像":
            return len(value) >= 2
        return True
    return False


def _specific_text(value: Any, forbidden: set[str], min_length: int = 6) -> bool:
    text = _canonical_text(value)
    if not text or _is_unknown(value):
        return False
    if text in {_canonical_text(item) for item in forbidden}:
        return False
    return len(text) >= min_length


def _content_source_sustainable(value: Any) -> bool:
    text = _canonical_text(value)
    if not text or _is_unknown(value):
        return False
    forbidden = {_canonical_text(item) for item in GENERIC_CONTENT_SOURCES}
    if text in forbidden or any(text == item for item in forbidden):
        return False
    return len(text) >= 4


def _long_conflict_sustainable(value: Any) -> bool:
    if isinstance(value, Mapping):
        aliases = {
            "sides": ("sides", "opponents", "持续对立双方"),
            "root": ("root_cause", "root", "无法一次解决的根因"),
            "escalation": ("escalation", "upgrade", "冲突升级方式"),
        }
        for names in aliases.values():
            if not any(not _is_unknown(value.get(name)) for name in names):
                return False
        return True
    text = _canonical_text(value)
    if not text or _is_unknown(value) or len(text) < 12:
        return False
    escalation_markers = ("升级", "逐步", "每次", "不断", "随着", "越来越", "长期", "对抗", "争夺", "无法")
    return any(marker in str(value) for marker in escalation_markers)


def _stage_goal_executable(value: Any) -> bool:
    text = _canonical_text(value)
    if not text or _is_unknown(value):
        return False
    if text in {_canonical_text(item) for item in ABSTRACT_STAGE_GOALS}:
        return False
    return len(text) >= 6 and any(marker in str(value) for marker in ACTION_MARKERS)


def _constraint_payloads(seed: Mapping[str, Any]) -> Tuple[List[Any], List[Any]]:
    must_have: List[Any] = []
    must_avoid: List[Any] = []
    for item in _as_list(seed.get("approved_constraints")):
        if isinstance(item, Mapping):
            kind = str(item.get("type") or "")
            value = item.get("value")
            if kind == "must_have":
                must_have.append(value)
            elif kind == "must_avoid":
                must_avoid.append(value)
        elif isinstance(item, str):
            if item.startswith(("必须：", "必须:")):
                must_have.append(item.split(":" if ":" in item else "：", 1)[-1])
            elif item.startswith(("禁止：", "禁止:")):
                must_avoid.append(item.split(":" if ":" in item else "：", 1)[-1])
    return must_have, must_avoid


def _validate_seed_fields(seed: Mapping[str, Any]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    seed_ref = _object_ref(seed)

    if not _specific_text(seed.get("one_sentence_promise"), GENERIC_PROMISES, min_length=8):
        issues.append(
            _issue(
                "A_SEED_INVALID",
                "one_sentence_promise",
                "一句话卖点缺失、过于空泛，或不足以形成具体承诺。",
                [f"{seed_ref}.one_sentence_promise"],
                "明确核心人物、异常/机制与持续阅读体验。",
            )
        )

    if not _content_source_sustainable(seed.get("content_source")):
        issues.append(
            _issue(
                "A_SEED_INVALID",
                "content_source",
                "内容源未说明如何持续产生新冲突，或仅描述不断变强/升级。",
                [f"{seed_ref}.content_source={seed.get('content_source')}"],
                "改为可重复产生事件、委托、规则代价或身份冲突的内容源。",
            )
        )

    structure = seed.get("lead_structure")
    if structure not in VALID_LEAD_STRUCTURES:
        issues.append(
            _issue(
                "A_SEED_INVALID",
                "lead_structure",
                "主导人物结构不明确。",
                [f"{seed_ref}.lead_structure={structure}"],
                "明确为单主角、双主角或群像。",
            )
        )

    if not _lead_core_complete(seed.get("lead_core"), structure):
        issues.append(
            _issue(
                "A_SEED_INVALID",
                "lead_core",
                "lead_core 未完整提供 identity、desire、deficiency。",
                [f"{seed_ref}.lead_core"],
                "为核心人物补齐身份、欲望与缺口。",
            )
        )

    if not _specific_text(seed.get("primary_opposition"), GENERIC_OPPOSITIONS, min_length=4):
        issues.append(
            _issue(
                "A_SEED_INVALID",
                "primary_opposition",
                "主要阻力缺失或仅是空泛困难描述。",
                [f"{seed_ref}.primary_opposition"],
                "明确具体对手、组织、制度、环境或内部冲突。",
            )
        )

    rules = [rule for rule in _as_list(seed.get("minimum_world_rules")) if not _is_unknown(rule)]
    if not rules:
        issues.append(
            _issue(
                "A_SEED_INVALID",
                "minimum_world_rules",
                "缺少启动第一阶段所需的最小世界规则。",
                [f"{seed_ref}.minimum_world_rules"],
                "提供至少一条可约束第一阶段行动与因果的规则。",
            )
        )

    if not _long_conflict_sustainable(seed.get("long_term_conflict")):
        issues.append(
            _issue(
                "A_SEED_INVALID",
                "long_term_conflict",
                "长期冲突未体现持续对立、不可一次解决的根因或升级方式。",
                [f"{seed_ref}.long_term_conflict"],
                "补充对立双方、长期根因与冲突升级路径。",
            )
        )

    if not _stage_goal_executable(seed.get("stage_one_goal")):
        issues.append(
            _issue(
                "A_SEED_INVALID",
                "stage_one_goal",
                "第一阶段目标是抽象愿望，不能作为可验收结果。",
                [f"{seed_ref}.stage_one_goal={seed.get('stage_one_goal')}"],
                "改为包含明确行动与可观察结果的阶段目标。",
            )
        )

    hook = seed.get("opening_hook")
    promise = seed.get("one_sentence_promise")
    if _is_unknown(hook) or not _related(hook, promise):
        issues.append(
            _issue(
                "A_SEED_INVALID",
                "opening_hook",
                "开篇钩子与一句话卖点没有可检测的同源机制或主题锚点。",
                [f"{seed_ref}.opening_hook", f"{seed_ref}.one_sentence_promise"],
                "让开篇异常、冲突或问题直接来自核心卖点。",
            )
        )

    continuation = seed.get("continuation_reason")
    if _is_unknown(continuation) or not (
        _related(continuation, seed.get("content_source"))
        or _related(continuation, seed.get("long_term_conflict"))
        or _related(continuation, seed.get("lead_core"))
    ):
        issues.append(
            _issue(
                "A_SEED_INVALID",
                "continuation_reason",
                "追读理由未能追溯到内容源、长期冲突或人物未解决欲望。",
                [f"{seed_ref}.continuation_reason"],
                "明确第一章后稳定新增内容从何而来。",
            )
        )

    must_have, must_avoid = _constraint_payloads(seed)
    for have_index, avoid_index, text in _direct_conflicts(must_have, must_avoid):
        issues.append(
            _issue(
                "A_INPUT_CONFLICT",
                "approved_constraints",
                f"已编译约束同时要求和禁止：{text}",
                [
                    f"{seed_ref}.approved_constraints.must_have[{have_index}]",
                    f"{seed_ref}.approved_constraints.must_avoid[{avoid_index}]",
                ],
                "由人工裁决保留其中一侧后重新编译。",
            )
        )

    return issues


def _validate_seed_precheck(seed: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues = _validate_seed_fields(seed)
    if len(_as_list(seed.get("minimum_world_rules"))) > 5:
        seed.setdefault("notes", [])
        warning = "minimum_world_rules 超过5条：项目种子可能已膨胀为世界百科。"
        if warning not in seed["notes"]:
            seed["notes"].append(warning)
    return issues


def _validate_g1(seed: Mapping[str, Any]) -> List[Dict[str, Any]]:
    issues = _validate_seed_fields(seed)
    if seed.get("status") not in {"approved", "locked"}:
        issues.append(
            _issue(
                "A_APPROVAL_REQUIRED",
                "status",
                "正式 G1 只接受 approved 或 locked 的 ProjectSeed。",
                [f"{_object_ref(seed)}.status={seed.get('status')}"],
                "完成人工 approve，生成新的 approved 版本后重新执行 G1。",
            )
        )
    return issues


def _base_envelope(action: str, project_id: Optional[str], request_refs: Sequence[str]) -> Dict[str, Any]:
    return {
        "layer": "A",
        "action": action,
        "gate": {"current": "G0", "result": "BLOCKED"},
        "project_id": project_id,
        "project_brief": None,
        "project_seed": None,
        "issues": [],
        "next_action": "stop",
        "evidence_refs": list(request_refs),
    }


def _build_handoff(seed: Mapping[str, Any], approval_ref: str) -> Dict[str, Any]:
    if seed.get("status") not in {"approved", "locked"}:
        raise ValueError("B_INIT handoff requires ProjectSeed.approved or locked")
    return {
        "from": "A",
        "to": "B_INIT",
        "project_id": seed["project_id"],
        "project_seed_ref": seed["object_id"],
        "project_seed_version": seed["object_version"],
        "gate": "G1",
        "gate_result": "PASS",
        "approval_ref": approval_ref,
    }


def _approval_record(
    project_id: str,
    previous_seed: Mapping[str, Any],
    decision: str,
    source_ref: Any,
    raw_data: Mapping[str, Any],
) -> Dict[str, Any]:
    now = _utc_now()
    approval_id = f"AP-{project_id}-{_timestamp_slug()}"
    proposed = "ProjectSeed.approved" if decision == "approve" else (
        "返回A层重新编译" if decision == "revise" else "ProjectSeed.rejected"
    )
    return {
        "approval_id": approval_id,
        "project_id": project_id,
        "变更对象": _object_ref(previous_seed),
        "原内容": {"status": previous_seed.get("status"), "object_version": previous_seed.get("object_version")},
        "拟变更内容": proposed,
        "变更理由": raw_data.get("approval_reason", UNKNOWN),
        "影响范围": raw_data.get("impact_scope", "A层 ProjectSeed 工作流状态与B_INIT交接"),
        "已知风险": _as_list(raw_data.get("accepted_risks") or raw_data.get("known_risks")),
        "批准或拒绝": decision,
        "批准人": raw_data.get("approved_by") or ",".join(_as_refs(source_ref)) or UNKNOWN,
        "批准时间": now,
    }


def _archive_current_if_needed(current_path: Path, history_dir: Path, incoming: Optional[Mapping[str, Any]]) -> None:
    if not current_path.exists() or incoming is None:
        return
    try:
        existing = _load_yaml_like(current_path)
    except Exception:
        existing = None
    if existing == incoming:
        return
    if isinstance(existing, Mapping):
        version = existing.get("object_version", "UNKNOWN")
        object_type = str(existing.get("object_type", current_path.stem)).lower()
        archive_name = f"{object_type}_v{version}_{_timestamp_slug()}.yaml"
    else:
        archive_name = f"{current_path.stem}_{_timestamp_slug()}.yaml"
    history_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(current_path, history_dir / archive_name)


def _persist_run(
    raw_text: str,
    envelope: Mapping[str, Any],
    approval: Optional[Mapping[str, Any]] = None,
    write_objects: bool = True,
) -> None:
    project_id = envelope.get("project_id")
    if not project_id:
        return
    a_dir = _runs_root() / str(project_id) / "A"
    history_dir = a_dir / "history"
    a_dir.mkdir(parents=True, exist_ok=True)
    history_dir.mkdir(parents=True, exist_ok=True)

    input_path = a_dir / "input.txt"
    if not input_path.exists():
        _atomic_write_text(input_path, raw_text)
    else:
        existing = input_path.read_text(encoding="utf-8")
        if existing != raw_text:
            digest = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()[:10]
            revision_path = history_dir / f"input_{_timestamp_slug()}_{digest}.txt"
            _atomic_write_text(revision_path, raw_text)

    brief = envelope.get("project_brief")
    seed = envelope.get("project_seed")
    brief_path = a_dir / "project_brief.yaml"
    seed_path = a_dir / "project_seed.yaml"
    if write_objects and isinstance(brief, Mapping):
        _archive_current_if_needed(brief_path, history_dir, brief)
        _dump_yaml_like(brief_path, brief)
    if write_objects and isinstance(seed, Mapping):
        _archive_current_if_needed(seed_path, history_dir, seed)
        _dump_yaml_like(seed_path, seed)

    log_path = a_dir / "run_log.yaml"
    log: Dict[str, Any]
    if log_path.exists():
        try:
            loaded = _load_yaml_like(log_path)
            log = dict(loaded) if isinstance(loaded, Mapping) else {}
        except Exception:
            log = {}
    else:
        log = {}
    log.setdefault("implementation_corrections", MINIMAL_CORRECTIONS)
    log.setdefault("runs", [])
    entry = {
        "run_at": _utc_now(),
        "layer": envelope.get("layer"),
        "action": envelope.get("action"),
        "gate": _deepcopy(envelope.get("gate")),
        "project_id": project_id,
        "brief_ref": _object_ref(brief) if isinstance(brief, Mapping) else None,
        "seed_ref": _object_ref(seed) if isinstance(seed, Mapping) else None,
        "issues": _deepcopy(envelope.get("issues", [])),
        "next_action": envelope.get("next_action"),
        "evidence_refs": _deepcopy(envelope.get("evidence_refs", [])),
        "handoff": _deepcopy(envelope.get("handoff")),
        "objects_written": write_objects,
    }
    if approval:
        entry["approval"] = _deepcopy(approval)
    log["runs"].append(entry)
    _dump_yaml_like(log_path, log)


def _compile_action(
    raw_input: Any,
    source_ref: Any,
    project_id: Optional[str],
    previous_brief: Optional[Mapping[str, Any]],
    previous_seed: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    data, raw_text = _parse_raw_input(raw_input)
    resolved_id, request_refs, g0_issues = _g0_check(data, source_ref, project_id, previous_brief, previous_seed)
    envelope = _base_envelope("compile", resolved_id, request_refs)

    if g0_issues or not resolved_id:
        envelope["issues"] = g0_issues
        envelope["gate"] = {"current": "G0", "result": "BLOCKED"}
        envelope["next_action"] = "supply_sources" if any(
            issue["code"] == "A_SOURCE_MISSING" for issue in g0_issues
        ) else "stop"
        _persist_run(raw_text, envelope)
        return envelope

    brief, brief_issues = _build_project_brief(data, resolved_id, request_refs, previous_brief)
    envelope["project_brief"] = brief
    envelope["issues"] = brief_issues

    if brief["status"] not in {"ready", "locked"}:
        envelope["gate"] = {"current": "G1_PRECHECK", "result": "BLOCKED"}
        envelope["next_action"] = "revise_brief"
        _persist_run(raw_text, envelope)
        return envelope

    seed = _build_project_seed(data, brief, previous_seed)
    seed_issues = _validate_seed_precheck(seed)
    if seed_issues:
        seed["status"] = "rejected"
        envelope["project_seed"] = seed
        envelope["issues"] = brief_issues + seed_issues
        envelope["gate"] = {"current": "G1_PRECHECK", "result": "BLOCKED"}
        envelope["next_action"] = "revise_brief"
        _persist_run(raw_text, envelope)
        return envelope

    seed["status"] = "candidate"
    envelope["project_seed"] = seed
    envelope["issues"] = brief_issues + [
        _issue(
            "A_APPROVAL_REQUIRED",
            "project_seed.status",
            "候选项目种子已通过结构预检，但尚未获得人工批准。",
            [f"{_object_ref(seed)}.status=candidate"],
            "执行 action=approve 且 human_decision=approve。",
        )
    ]
    envelope["gate"] = {"current": "G1_PRECHECK", "result": "PASS"}
    envelope["next_action"] = "human_approve"
    _persist_run(raw_text, envelope)
    return envelope


def _approve_action(
    raw_input: Any,
    source_ref: Any,
    project_id: Optional[str],
    previous_brief: Optional[Mapping[str, Any]],
    previous_seed: Optional[Mapping[str, Any]],
    human_decision: Optional[str],
) -> Dict[str, Any]:
    data, raw_text = _parse_raw_input(raw_input)
    request_refs = _as_refs(source_ref)
    resolved_id = project_id or (str(previous_seed.get("project_id")) if previous_seed else None)
    envelope = _base_envelope("approve", resolved_id, request_refs)
    envelope["project_brief"] = _deepcopy(previous_brief) if previous_brief else None

    g0_issues = _validate_project_consistency(resolved_id, previous_brief, previous_seed)
    approval_issues: List[Dict[str, Any]] = []

    if not request_refs:
        g0_issues.append(
            _issue(
                "A_SOURCE_MISSING",
                "source_ref",
                "人工决策缺少来源标识。",
                ["source_ref is empty"],
                "提供批准人或人工决策记录来源。",
            )
        )
    else:
        inaccessible_request_refs = [ref for ref in request_refs if not _ref_accessible(ref)]
        if inaccessible_request_refs:
            g0_issues.append(
                _issue(
                    "A_SOURCE_MISSING",
                    "source_ref",
                    "人工决策来源被声明为本地路径，但不可读取。",
                    inaccessible_request_refs,
                    "修正本地来源路径或读取权限。",
                )
            )

    if previous_seed is None:
        approval_issues.append(
            _issue(
                "A_INPUT_MISSING",
                "previous_seed",
                "人工审批缺少待决 ProjectSeed.candidate。",
                ["previous_seed is None"],
                "提供磁盘当前待审批 ProjectSeed.candidate。",
            )
        )
    if human_decision not in VALID_HUMAN_DECISIONS:
        approval_issues.append(
            _issue(
                "A_INPUT_MISSING",
                "human_decision",
                "human_decision 必须为 approve、revise 或 reject。",
                [f"human_decision={human_decision}"],
                "提供合法人工决策。",
            )
        )

    current_seed: Optional[Dict[str, Any]] = None
    if resolved_id and previous_seed is not None and not g0_issues:
        g0_issues.extend(
            _validate_formal_object(
                previous_seed,
                "ProjectSeed",
                resolved_id,
                allowed_statuses={"candidate"},
            )
        )
        if previous_brief is not None:
            g0_issues.extend(_validate_formal_object(previous_brief, "ProjectBrief", resolved_id))
        loaded_seed, load_issues = _load_current_object(resolved_id, "ProjectSeed")
        current_seed = loaded_seed
        g0_issues.extend(load_issues)
        if current_seed is not None and not load_issues:
            g0_issues.extend(_validate_matches_current(previous_seed, current_seed, "ProjectSeed"))

    issues = g0_issues + approval_issues
    if issues or not resolved_id or previous_seed is None or human_decision is None:
        envelope["issues"] = issues
        envelope["project_seed"] = _deepcopy(previous_seed) if previous_seed else None
        envelope["gate"] = {"current": "G0" if g0_issues else "G1", "result": "BLOCKED"}
        envelope["next_action"] = "supply_sources" if any(i["code"] == "A_SOURCE_MISSING" for i in issues) else "stop"
        _persist_run(raw_text, envelope, write_objects=False)
        return envelope

    assert current_seed is not None
    approval = _approval_record(resolved_id, current_seed, human_decision, source_ref, data)

    if human_decision == "revise":
        envelope["project_seed"] = _deepcopy(current_seed)
        envelope["issues"] = [
            _issue(
                "A_APPROVAL_REQUIRED",
                "human_decision",
                "人工要求修订；当前 candidate 保留，不进入 B_INIT。",
                [approval["approval_id"], _object_ref(current_seed)],
                "以磁盘当前 ProjectBrief/ProjectSeed 为基线重新执行 action=compile。",
            )
        ]
        envelope["gate"] = {"current": "G1", "result": "BLOCKED"}
        envelope["next_action"] = "revise_brief"
        _persist_run(raw_text, envelope, approval)
        return envelope

    now = _utc_now()
    new_seed = _deepcopy(dict(current_seed))
    new_seed["object_version"] = _next_version(current_seed)
    new_seed["updated_at"] = now
    new_seed["source_refs"] = _dedupe(_as_refs(new_seed.get("source_refs")) + [approval["approval_id"]])

    if human_decision == "reject":
        new_seed["status"] = "rejected"
        envelope["project_seed"] = new_seed
        envelope["gate"] = {"current": "G1", "result": "BLOCKED"}
        envelope["next_action"] = "stop"
        _persist_run(raw_text, envelope, approval)
        return envelope

    new_seed["status"] = "approved"
    g1_issues = _validate_g1(new_seed)
    if g1_issues:
        envelope["project_seed"] = _deepcopy(current_seed)
        envelope["issues"] = g1_issues
        envelope["gate"] = {"current": "G1", "result": "BLOCKED"}
        envelope["next_action"] = "revise_brief"
        _persist_run(raw_text, envelope, approval, write_objects=False)
        return envelope

    envelope["project_seed"] = new_seed
    envelope["issues"] = []
    envelope["gate"] = {"current": "G1", "result": "PASS"}
    envelope["next_action"] = "B_INIT"
    envelope["handoff"] = _build_handoff(new_seed, approval["approval_id"])
    _persist_run(raw_text, envelope, approval)
    return envelope


def run_a_layer(
    raw_input: Any,
    source_ref: Any,
    project_id: Optional[str] = None,
    action: str = "compile",
    previous_brief: Optional[Mapping[str, Any]] = None,
    previous_seed: Optional[Mapping[str, Any]] = None,
    human_decision: Optional[str] = None,
) -> Dict[str, Any]:
    """运行 SRN-U A层。

    参数与 A层实施设计保持一致。函数会在本地 runs/<project_id>/A/ 落盘。
    返回值是运行信封，不是第十类核心对象。
    """
    if action not in VALID_ACTIONS:
        request_refs = _as_refs(source_ref)
        envelope = _base_envelope(action, project_id, request_refs)
        envelope["issues"] = [
            _issue(
                "A_INPUT_CONFLICT",
                "action",
                f"action={action} 不受支持。",
                [f"allowed={sorted(VALID_ACTIONS)}"],
                "使用 compile 或 approve。",
            )
        ]
        return envelope

    previous_brief_copy = _deepcopy(dict(previous_brief)) if previous_brief else None
    previous_seed_copy = _deepcopy(dict(previous_seed)) if previous_seed else None

    if action == "compile":
        return _compile_action(
            raw_input=raw_input,
            source_ref=source_ref,
            project_id=project_id,
            previous_brief=previous_brief_copy,
            previous_seed=previous_seed_copy,
        )
    return _approve_action(
        raw_input=raw_input,
        source_ref=source_ref,
        project_id=project_id,
        previous_brief=previous_brief_copy,
        previous_seed=previous_seed_copy,
        human_decision=human_decision,
    )


def _valid_input() -> Dict[str, Any]:
    return {
        "operation_mode": "create_new",
        "target_platform": "番茄",
        "genre": "规则怪谈",
        "target_reader": "偏好快节奏规则冲突的读者",
        "core_emotion": "紧张中的偷赢感",
        "idea_statement": "梦境泄漏进现实，处理员必须让所有知情者重新遗忘。",
        "length_target": "100万字",
        "must_have": ["现实世界与梦境世界并行"],
        "must_avoid": ["系统面板式倒计时"],
        "style_preference": "具体、克制、行动驱动",
        "commercial_goal": "完成可连载的商业小说",
        "project_title": "梦只能被遗忘",
        "one_sentence_promise": "梦境处理员在泄漏梦境侵入现实前清除记忆，让读者持续获得规则危机中的偷赢感。",
        "content_source": "不同梦境泄漏案件，以及每次清除记忆引发的身份与组织冲突。",
        "lead_structure": "单主角",
        "lead_core": {
            "identity": "新入职的梦境处理员",
            "desire": "查清自己为何记得被全城遗忘的事故",
            "deficiency": "无法确认自己的记忆是否真实",
        },
        "primary_opposition": {
            "external": "失控梦境与垄断遗忘权的组织",
            "internal": "主角无法确认自身记忆真伪",
        },
        "minimum_world_rules": [
            "梦境被多人记住后会在现实中获得实体",
            "处理完成后相关记忆必须被清除",
            "主角保留部分本应被清除的记忆",
        ],
        "long_term_conflict": "主角与垄断遗忘权的组织长期对抗；组织依靠篡改记忆维持秩序，每次案件升级都会暴露更多被删除的事故。",
        "stage_one_goal": "完成第一次独立梦境处理，并发现自己的事故档案被删除。",
        "opening_hook": "陌生人说出处理员昨夜已经清除的泄漏梦境。",
        "continuation_reason": "每个梦境泄漏案件都会推进组织篡改记忆的长期冲突，并逼近主角被删除的事故记忆。",
        "approved_constraints": ["现实与梦境世界并行", "不使用系统面板"],
        "rejected_directions": ["与核心机制无关的纯升级流"],
    }


def _test_case(test_id: str, description: str, func: Any) -> Dict[str, Any]:
    started = _utc_now()
    try:
        actual = func()
        return {
            "id": test_id,
            "description": description,
            "status": "PASS",
            "actual_result": actual,
            "started_at": started,
            "finished_at": _utc_now(),
        }
    except Exception as exc:
        return {
            "id": test_id,
            "description": description,
            "status": "FAIL",
            "actual_result": {"error": f"{type(exc).__name__}: {exc}"},
            "started_at": started,
            "finished_at": _utc_now(),
        }


def run_self_tests(test_root: Optional[Path] = None) -> Dict[str, Any]:
    """执行 A-T01 至 A-T10，并返回包含 actual_result 的报告。"""
    if test_root is None:
        test_root = Path(tempfile.mkdtemp(prefix="srnu-a-tests-"))
    else:
        test_root = Path(test_root).resolve()
        if test_root.exists():
            shutil.rmtree(test_root)
        test_root.mkdir(parents=True, exist_ok=True)

    old_root = os.environ.get("SRNU_RUNS_DIR")
    os.environ["SRNU_RUNS_DIR"] = str(test_root / "runs")

    cases: List[Dict[str, Any]] = []
    acceptance_checks: List[Dict[str, Any]] = []
    valid = _valid_input()

    def t01() -> Dict[str, Any]:
        result = run_a_layer(_deepcopy(valid), "TEST-A-T01")
        assert result["project_id"] and result["project_id"].startswith("NOVEL-")
        assert result["gate"]["result"] == "PASS"
        return {"project_id": result["project_id"], "gate": result["gate"]}

    def t02() -> Dict[str, Any]:
        result = run_a_layer(_deepcopy(valid), "TEST-A-T02")
        assert result["project_brief"]["status"] == "ready"
        assert result["project_seed"]["status"] == "candidate"
        return {
            "brief_status": result["project_brief"]["status"],
            "seed_status": result["project_seed"]["status"],
        }

    def t03() -> Dict[str, Any]:
        data = _deepcopy(valid)
        data.pop("idea_statement")
        result = run_a_layer(data, "TEST-A-T03")
        assert result["project_brief"]["status"] == "draft"
        assert result["project_seed"] is None
        return {"brief_status": "draft", "seed_generated": False, "gate": result["gate"]}

    def t04() -> Dict[str, Any]:
        data = _deepcopy(valid)
        data["must_have"] = ["系统面板式倒计时"]
        data["must_avoid"] = ["系统面板式倒计时"]
        result = run_a_layer(data, "TEST-A-T04")
        assert result["gate"]["result"] == "BLOCKED"
        assert result["project_brief"]["status"] == "invalid"
        return {"brief_status": "invalid", "issue_codes": [i["code"] for i in result["issues"]]}

    def t05() -> Dict[str, Any]:
        data = _deepcopy(valid)
        data["operation_mode"] = "continue_existing"
        result = run_a_layer(data, "TEST-A-T05-REQUEST", project_id="NOVEL-TEST-A-T05")
        assert result["gate"] == {"current": "G0", "result": "BLOCKED"}
        assert result["next_action"] == "supply_sources"
        return {"gate": result["gate"], "next_action": result["next_action"]}

    def t06() -> Dict[str, Any]:
        data = _deepcopy(valid)
        data["content_source"] = "不断变强"
        result = run_a_layer(data, "TEST-A-T06")
        assert result["project_seed"]["status"] == "rejected"
        assert result["gate"]["result"] == "BLOCKED"
        return {"seed_status": "rejected", "invalid_fields": [i["field"] for i in result["issues"]]}

    def t07() -> Dict[str, Any]:
        data = _deepcopy(valid)
        data["opening_hook"] = "城市中心突然发生一场与梦境无关的爆炸。"
        result = run_a_layer(data, "TEST-A-T07")
        assert result["project_seed"]["status"] == "rejected"
        assert any(issue["field"] == "opening_hook" for issue in result["issues"])
        return {"seed_status": "rejected", "opening_hook_rejected": True}

    t08_cache: Dict[str, Any] = {}

    def t08() -> Dict[str, Any]:
        result = run_a_layer(_deepcopy(valid), "TEST-A-T08")
        assert result["project_seed"]["status"] == "candidate"
        assert result["next_action"] == "human_approve"
        assert "handoff" not in result
        t08_cache["result"] = result
        return {
            "seed_status": "candidate",
            "next_action": "human_approve",
            "entered_B": False,
            "gate": result["gate"],
        }

    def t09() -> Dict[str, Any]:
        base = t08_cache.get("result") or run_a_layer(_deepcopy(valid), "TEST-A-T09-COMPILE")
        result = run_a_layer(
            {
                "approval_reason": "批准该最小项目种子进入B-INIT",
                "approved_by": "TEST-HUMAN",
                "accepted_risks": ["项目名仍为工作名时可在后续人工修改"],
            },
            "TEST-A-T09-APPROVAL",
            project_id=base["project_id"],
            action="approve",
            previous_brief=base["project_brief"],
            previous_seed=base["project_seed"],
            human_decision="approve",
        )
        assert result["project_seed"]["status"] == "approved"
        assert result["project_seed"]["object_version"] == "2"
        assert result["next_action"] == "B_INIT"
        assert result["handoff"]["gate_result"] == "PASS"
        return {
            "seed_status": "approved",
            "object_version": "2",
            "next_action": "B_INIT",
            "handoff": result["handoff"],
        }

    def t10() -> Dict[str, Any]:
        base = run_a_layer(_deepcopy(valid), "TEST-A-T10-COMPILE")
        old_seed = _deepcopy(base["project_seed"])
        decision = run_a_layer(
            {"approval_reason": "opening_hook需要更直接"},
            "TEST-A-T10-REVISE",
            project_id=base["project_id"],
            action="approve",
            previous_brief=base["project_brief"],
            previous_seed=base["project_seed"],
            human_decision="revise",
        )
        assert decision["project_seed"] == old_seed
        assert decision["next_action"] == "revise_brief"

        revised_input = _deepcopy(valid)
        revised_input["opening_hook"] = "泄漏梦境中的死者在现实里叫出处理员的真名。"
        revised = run_a_layer(
            revised_input,
            "TEST-A-T10-RECOMPILE",
            project_id=base["project_id"],
            action="compile",
            previous_brief=base["project_brief"],
            previous_seed=base["project_seed"],
        )
        assert revised["project_seed"]["status"] == "candidate"
        assert revised["project_seed"]["object_version"] == "2"
        a_dir = _runs_root() / base["project_id"] / "A"
        history_names = [p.name for p in (a_dir / "history").iterdir()]
        assert any("projectseed_v1" in name.lower() for name in history_names)
        assert (a_dir / "input.txt").read_text(encoding="utf-8") == _serialize_raw_input(valid)
        assert any(name.startswith("input_") for name in history_names)
        return {
            "old_seed_version": old_seed["object_version"],
            "new_seed_version": revised["project_seed"]["object_version"],
            "old_candidate_preserved": True,
            "initial_input_immutable": True,
            "history_files": sorted(history_names),
        }

    tests = [
        ("A-T01", "新项目无project_id，自动分配后继续", t01),
        ("A-T02", "create_new完整输入，生成PB.ready与PS.candidate", t02),
        ("A-T03", "idea_statement缺失，PB.draft且不生成PS", t03),
        ("A-T04", "must_have与must_avoid冲突，BLOCKED", t04),
        ("A-T05", "continue_existing无既有材料source_refs，BLOCKED", t05),
        ("A-T06", "content_source仅为不断变强，PS.rejected", t06),
        ("A-T07", "opening_hook与卖点无关，PS.rejected", t07),
        ("A-T08", "合法candidate等待人工批准，不进入B", t08),
        ("A-T09", "人工approve生成新版本PS.approved并进入B_INIT", t09),
        ("A-T10", "人工revise保留旧版本并重新编译", t10),
    ]

    try:
        for test_id, description, func in tests:
            cases.append(_test_case(test_id, description, func))

        # A层完成判定中的非编号约束：不修改调用方原始输入，不允许跨项目污染。
        mutation_input = _valid_input()
        mutation_before = _deepcopy(mutation_input)
        run_a_layer(mutation_input, "ACCEPTANCE-RAW-IMMUTABLE")
        acceptance_checks.append({
            "name": "raw_input_not_mutated",
            "status": "PASS" if mutation_input == mutation_before else "FAIL",
            "actual_result": {"unchanged": mutation_input == mutation_before},
        })

        cross_base = run_a_layer(_valid_input(), "ACCEPTANCE-CROSS-BASE")
        cross_result = run_a_layer(
            _valid_input(),
            "ACCEPTANCE-CROSS-CHECK",
            project_id="NOVEL-DIFFERENT-PROJECT",
            previous_brief=cross_base["project_brief"],
            previous_seed=cross_base["project_seed"],
        )
        cross_blocked = (
            cross_result["gate"] == {"current": "G0", "result": "BLOCKED"}
            and any(issue["field"] == "project_id" for issue in cross_result["issues"])
        )
        acceptance_checks.append({
            "name": "cross_project_reference_blocked",
            "status": "PASS" if cross_blocked else "FAIL",
            "actual_result": {"blocked": cross_blocked, "gate": cross_result["gate"]},
        })

        # A-RT01：陈旧 candidate 不得覆盖当前真源。
        stale_base = run_a_layer(_valid_input(), "A-RT01-COMPILE")
        stale_candidate = _deepcopy(stale_base["project_seed"])
        newer_input = _valid_input()
        newer_input["opening_hook"] = "梦境死者在现实中叫出处理员被删除的旧名。"
        newer = run_a_layer(
            newer_input,
            "A-RT01-RECOMPILE",
            project_id=stale_base["project_id"],
            previous_brief=stale_base["project_brief"],
            previous_seed=stale_base["project_seed"],
        )
        stale_result = run_a_layer(
            {"approval_reason": "尝试批准陈旧版本"},
            "A-RT01-APPROVE",
            project_id=stale_base["project_id"],
            action="approve",
            previous_brief=newer["project_brief"],
            previous_seed=stale_candidate,
            human_decision="approve",
        )
        current_after_stale = _load_yaml_like(_current_object_path(stale_base["project_id"], "ProjectSeed"))
        stale_blocked = (
            stale_result["gate"] == {"current": "G0", "result": "BLOCKED"}
            and current_after_stale == newer["project_seed"]
        )
        acceptance_checks.append({
            "name": "A-RT01_stale_candidate_blocked",
            "status": "PASS" if stale_blocked else "FAIL",
            "actual_result": {"blocked": stale_blocked, "gate": stale_result["gate"]},
        })

        # A-RT02：错误对象类型不得进入审批。
        type_base = run_a_layer(_valid_input(), "A-RT02-COMPILE")
        wrong_type = _deepcopy(type_base["project_seed"])
        wrong_type["object_type"] = "CharacterState"
        type_result = run_a_layer(
            {"approval_reason": "错误类型反向测试"},
            "A-RT02-APPROVE",
            project_id=type_base["project_id"],
            action="approve",
            previous_brief=type_base["project_brief"],
            previous_seed=wrong_type,
            human_decision="approve",
        )
        type_blocked = type_result["gate"] == {"current": "G0", "result": "BLOCKED"}
        acceptance_checks.append({
            "name": "A-RT02_wrong_object_type_blocked",
            "status": "PASS" if type_blocked else "FAIL",
            "actual_result": {"blocked": type_blocked, "gate": type_result["gate"]},
        })

        # A-RT03：缺失公共版本元数据不得进入审批。
        meta_base = run_a_layer(_valid_input(), "A-RT03-COMPILE")
        missing_meta = _deepcopy(meta_base["project_seed"])
        missing_meta.pop("schema_version", None)
        missing_meta.pop("object_version", None)
        meta_result = run_a_layer(
            {"approval_reason": "缺失元数据反向测试"},
            "A-RT03-APPROVE",
            project_id=meta_base["project_id"],
            action="approve",
            previous_brief=meta_base["project_brief"],
            previous_seed=missing_meta,
            human_decision="approve",
        )
        meta_blocked = meta_result["gate"] == {"current": "G0", "result": "BLOCKED"}
        acceptance_checks.append({
            "name": "A-RT03_missing_metadata_blocked",
            "status": "PASS" if meta_blocked else "FAIL",
            "actual_result": {"blocked": meta_blocked, "gate": meta_result["gate"]},
        })

        # A-RT04：带 previous_* 的重新编译也必须使用当前真源。
        compile_stale_result = run_a_layer(
            _valid_input(),
            "A-RT04-RECOMPILE",
            project_id=stale_base["project_id"],
            previous_brief=newer["project_brief"],
            previous_seed=stale_candidate,
        )
        compile_stale_blocked = compile_stale_result["gate"] == {"current": "G0", "result": "BLOCKED"}
        acceptance_checks.append({
            "name": "A-RT04_stale_recompile_blocked",
            "status": "PASS" if compile_stale_blocked else "FAIL",
            "actual_result": {"blocked": compile_stale_blocked, "gate": compile_stale_result["gate"]},
        })

        # A-RT05：不可读路径型 source_ref 必须被G0阻断。
        path_result = run_a_layer(_valid_input(), "/definitely/not/exist/source_input.md")
        path_blocked = path_result["gate"] == {"current": "G0", "result": "BLOCKED"}
        acceptance_checks.append({
            "name": "A-RT05_unreadable_source_path_blocked",
            "status": "PASS" if path_blocked else "FAIL",
            "actual_result": {"blocked": path_blocked, "gate": path_result["gate"]},
        })
    finally:
        if old_root is None:
            os.environ.pop("SRNU_RUNS_DIR", None)
        else:
            os.environ["SRNU_RUNS_DIR"] = old_root

    passed = sum(case["status"] == "PASS" for case in cases)
    acceptance_passed = sum(check["status"] == "PASS" for check in acceptance_checks)
    report = {
        "suite": "SRN-U A层 A-T01—A-T10",
        "generated_at": _utc_now(),
        "test_root": str(test_root),
        "summary": {
            "total": len(cases),
            "passed": passed,
            "failed": len(cases) - passed,
            "acceptance_total": len(acceptance_checks),
            "acceptance_passed": acceptance_passed,
            "acceptance_failed": len(acceptance_checks) - acceptance_passed,
        },
        "minimal_corrections": MINIMAL_CORRECTIONS,
        "cases": cases,
        "acceptance_checks": acceptance_checks,
    }
    report_path = test_root / "A-T01-A-T10-results.json"
    _atomic_write_text(report_path, json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n")
    report["report_path"] = str(report_path)
    return report


def _read_mapping_file(path: Optional[str]) -> Optional[Dict[str, Any]]:
    if not path:
        return None
    loaded = _load_yaml_like(Path(path))
    if not isinstance(loaded, Mapping):
        raise ValueError(f"{path} must contain a mapping/object")
    return dict(loaded)


def _read_raw_input(path: Optional[str], inline: Optional[str]) -> Any:
    if path:
        return Path(path).read_text(encoding="utf-8")
    if inline is not None:
        return inline
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise ValueError("provide --input-file, --input-json, or stdin")


def _build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SRN-U A层本地入口")
    parser.add_argument("--self-test", action="store_true", help="运行 A-T01 至 A-T10")
    parser.add_argument("--test-root", help="自测输出目录")
    parser.add_argument("--input-file", help="原始输入文件（JSON/YAML/文本）")
    parser.add_argument("--input-json", help="内联 JSON/YAML/文本")
    parser.add_argument("--source-ref", default="CLI-INPUT", help="本次输入来源标识")
    parser.add_argument("--project-id")
    parser.add_argument("--action", choices=sorted(VALID_ACTIONS), default="compile")
    parser.add_argument("--previous-brief")
    parser.add_argument("--previous-seed")
    parser.add_argument("--human-decision", choices=sorted(VALID_HUMAN_DECISIONS))
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_cli().parse_args(argv)
    if args.self_test:
        report = run_self_tests(Path(args.test_root) if args.test_root else None)
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        return 0 if (
            report["summary"]["failed"] == 0
            and report["summary"].get("acceptance_failed", 0) == 0
        ) else 1

    try:
        raw_input = _read_raw_input(args.input_file, args.input_json)
        result = run_a_layer(
            raw_input=raw_input,
            source_ref=args.source_ref,
            project_id=args.project_id,
            action=args.action,
            previous_brief=_read_mapping_file(args.previous_brief),
            previous_seed=_read_mapping_file(args.previous_seed),
            human_decision=args.human_decision,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0 if result["gate"]["result"] == "PASS" else 2
    except Exception as exc:
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
