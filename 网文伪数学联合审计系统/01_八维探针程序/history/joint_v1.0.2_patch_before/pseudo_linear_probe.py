#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八维伪线性探针 v3.2.1

正确运行边界：
- Codex 负责阅读小说文本，并按固定结构生成 extraction.json；
- 本脚本不调用任何模型 API，不读取 Codex 会话，不需要 API Key；
- 本脚本只负责：任务封装、结构校验、向量化、线性计算、门控、报告、对比、权重拟合；
- 不读取模型隐藏层，不是真实线性探针；
- activation 不是爆款概率、签约率、留存率或收入预测。

Python 3.11+
第三方依赖：无（仅使用 Python 标准库）
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

VERSION = "3.2.1"
SCHEMA_VERSION = "3.2.1"
RUBRIC_VERSION = "八维伪线性探针-v3.2.1"
DEFAULT_MAX_CHARS = 50_000

InputType = Literal[
    "online_full",
    "unpublished_full",
    "first_three",
    "single_chapter",
    "fragment",
]

INPUT_TYPES: dict[str, str] = {
    "online_full": "已上线整书",
    "unpublished_full": "未上线整书",
    "first_three": "前三章",
    "single_chapter": "单章",
    "fragment": "小说片段",
}

AXIS_NAMES = [
    "因果代价轴",
    "期待违背轴",
    "极速流转轴",
    "章尾钩子轴",
    "活人冲突轴",
    "侧面烘托轴",
    "反差造梗轴",
    "设定动作化轴",
]

GATE_NAMES = [
    "卖点识别门",
    "情绪承诺门",
    "开篇入口门",
    "主角发动机门",
    "最小兑现门",
    "连载扩展门",
]

# 这些轴决定章节是否形成可持续的因果推进与追读承诺。
# 缺失时不能仅依靠其他低权重轴输出中高等级。
DEFAULT_CRITICAL_AXES = [
    "因果代价轴",
    "极速流转轴",
    "章尾钩子轴",
    "活人冲突轴",
]

RISK_LEVELS = {"低", "中", "高"}
READABILITY_LEVELS = {"低", "中", "高", "证据不足"}

# 工程初始值：不是平台事实，不是训练结论。
DEFAULT_WEIGHTS = {
    "因果代价轴": 0.45,
    "期待违背轴": 0.55,
    "极速流转轴": 0.65,
    "章尾钩子轴": 0.75,
    "活人冲突轴": 0.75,
    "侧面烘托轴": 0.35,
    "反差造梗轴": 0.25,
    "设定动作化轴": 0.60,
}
DEFAULT_BIAS = 0.0
DEFAULT_THRESHOLDS = {
    "high": 0.68,
    "medium": 0.50,
    "low": 0.35,
    "minimum_coverage": 0.625,
    "minimum_weighted_coverage": 0.70,
}

CODEX_INSTRUCTION = r"""
# Codex 执行任务：生成八维特征提取文件

你已经是本任务的模型执行端。不要让 Python 脚本再次调用任何 API。

## 输入

读取同目录下：

- `task.json`
- `extraction.template.json`
- `extraction.schema.json`

## 输出

在同目录生成：

```text
extraction.json
```

硬要求：

1. 严格保留 `schema_version`、`rubric_version`、`task_id`、`source_sha256`、`input_type`。
2. 八维必须且只能各出现一次；六个商业门必须且只能各出现一次。
3. `evidence_sufficient=true` 时：
   - `score` 必须为 0—4；
   - `evidence` 至少一条；
   - 每条 evidence 必须逐字来自 `task.json.text`，禁止概括、改写和编造；
   - `judgment` 不得为空；
   - `evidence_gap` 必须为空。
4. `evidence_sufficient=false` 时：
   - `score=null`；
   - `evidence=[]`；
   - `evidence_gap` 必须明确写出缺什么证据。
5. 分数含义：0=缺失或反向伤害；1=有痕迹但不起作用；2=合格；3=明显增强；4=主要驱动力且可能过载。
6. Codex 不得输出综合总分；综合计算由本地 Python 完成。
7. 不得输出或改写“允许判断/禁止外推”边界；边界由 Python 根据 `input_type` 固定生成。
8. 同一病灶只能登记一个主轴，其他维度放入 `related_axes`。
9. `top_issues` 最多三项，其中 `evidence` 也必须逐字来自正文。
10. 主线字段全空时，不得把 `readability_risk` 写成“低”或“中”；必须列出 `missing_items`。
11. 同一句原文可以辅助多个维度，但不得作为三个及以上高分维度的唯一正向证据；每个高分维度至少提供一条维度专属证据。
12. 片段、单章不得外推整书市场结论，不得编造平台数据、读者数据、留存率、签约率、收入或爆款概率。
13. 完成 `extraction.json` 后，执行本文件末尾“当前任务本地计算命令”。

## 八维定义

- 因果代价轴：收益是否同步形成真实债务、污染、责任、反噬或后续成本。
- 期待违背轴：结果是否改变读者预测及人物处境，而非只换台词或随机惊吓。
- 极速流转轴：文字是否持续改变目标、权力、信息、收益损失、阻力或不可撤销决定。
- 章尾钩子轴：结尾是否启动不能无成本搁置、且下一章可兑现的阅读承诺。
- 活人冲突轴：角色是否围绕利益、责任、资源、解释权和条件主动改变局势。
- 侧面烘托轴：配角、旁观者、组织或制度是否因主角异常付出成本并调整行为。
- 反差造梗轴：反差是否来自稳定行为逻辑，并改变资源、风险、身份或关系。
- 设定动作化轴：新设定是否通过动作、后果和选择出现，而非停下来讲解。

## 六个商业门

- 卖点识别门：能否一句话说清不可替代的设定、职业、能力或矛盾。
- 情绪承诺门：读者主要获得的爽、怕、笑、赢、窥秘、报复、升级等是否清晰。
- 开篇入口门：是否快速出现具体麻烦、欲望、异常或收益。
- 主角发动机门：主角是否有稳定欲望、资源缺口、风险偏好和行动方式。
- 最小兑现门：是否存在可重复生产的爽点、破局、反转、收益或揭密单位。
- 连载扩展门：机制是否能升级对象、代价、对手、地图、制度和关系。
""".strip()


@dataclass(frozen=True)
class WeightSet:
    weights: dict[str, float]
    bias: float
    thresholds: dict[str, float]
    critical_axes: tuple[str, ...]
    source: str
    status: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def sigmoid(value: float) -> float:
    if value >= 0:
        e = math.exp(-value)
        return 1.0 / (1.0 + e)
    e = math.exp(value)
    return e / (1.0 + e)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_text_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"文件不存在：{path}")
    if not path.is_file():
        raise ValueError(f"路径不是文件：{path}")
    raw = path.read_bytes()
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", raw, 0, 1, "无法识别文本编码，请转为 UTF-8")


def read_json_file(path: Path) -> Any:
    try:
        return json.loads(read_text_file(path))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 解析失败：{path}：{exc}") from exc


def load_json_object(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    data = read_json_file(path)
    if not isinstance(data, dict):
        raise ValueError(f"JSON 顶层必须是对象：{path}")
    return data


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_text_length(text: str, max_chars: int, allow_truncate: bool) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    if not allow_truncate:
        raise ValueError(
            f"输入共 {len(text)} 字符，超过 --max-chars={max_chars}。"
            "默认拒绝静默截断；请拆分输入，或显式使用 --allow-truncate。"
        )
    return text[:max_chars], True


def expect_dict(value: Any, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{location} 必须是对象")
    return value


def expect_list(value: Any, location: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{location} 必须是数组")
    return value


def expect_str(value: Any, location: str, *, allow_empty: bool = True) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{location} 必须是字符串")
    if not allow_empty and not value.strip():
        raise ValueError(f"{location} 不得为空")
    return value


def expect_bool(value: Any, location: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{location} 必须是布尔值")
    return value


def expect_int_range(value: Any, location: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(f"{location} 必须是 {low}—{high} 的整数")
    return value


def expect_str_list(value: Any, location: str) -> list[str]:
    items = expect_list(value, location)
    result: list[str] = []
    for index, item in enumerate(items):
        result.append(expect_str(item, f"{location}[{index}]"))
    return result


def exact_keys(obj: dict[str, Any], required: set[str], location: str) -> None:
    missing = sorted(required - set(obj))
    extra = sorted(set(obj) - required)
    if missing or extra:
        raise ValueError(f"{location} 字段不匹配。缺失={missing}，额外={extra}")



def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def quote_exists_in_text(quote: str, source_text: str) -> bool:
    quote = quote.strip()
    if not quote:
        return False
    if quote in source_text:
        return True
    return normalize_whitespace(quote) in normalize_whitespace(source_text)


def validate_source_quote(quote: Any, source_text: str, location: str) -> str:
    value = expect_str(quote, location, allow_empty=False).strip()
    if len(normalize_whitespace(value)) < 2:
        raise ValueError(f"{location} 过短，不能作为可审计原文证据")
    if not quote_exists_in_text(value, source_text):
        raise ValueError(f"{location} 无法在 task.text 中定位，禁止使用概括、改写或虚构证据：{value!r}")
    return value


def validate_evidence_state(
    *, sufficient: bool, score: Any, confidence: Any, evidence: Any,
    judgment: Any, evidence_gap: Any, source_text: str, location: str,
) -> tuple[int | None, list[str]]:
    checked_confidence = expect_int_range(confidence, f"{location}.confidence", 0, 100)
    evidence_items = expect_list(evidence, f"{location}.evidence")
    checked_judgment = expect_str(judgment, f"{location}.judgment")
    checked_gap = expect_str(evidence_gap, f"{location}.evidence_gap")
    if sufficient:
        checked_score = expect_int_range(score, f"{location}.score", 0, 4)
        if checked_confidence <= 0:
            raise ValueError(f"{location} 有充分证据时 confidence 必须大于 0")
        if not evidence_items:
            raise ValueError(f"{location} evidence_sufficient=true 时 evidence 至少一条")
        checked_evidence = [
            validate_source_quote(item, source_text, f"{location}.evidence[{index}]")
            for index, item in enumerate(evidence_items)
        ]
        if not checked_judgment.strip():
            raise ValueError(f"{location} evidence_sufficient=true 时 judgment 不得为空")
        if checked_gap.strip():
            raise ValueError(f"{location} evidence_sufficient=true 时 evidence_gap 必须为空")
        return checked_score, checked_evidence
    if score is not None:
        raise ValueError(f"{location} 证据不足时 score 必须为 null")
    if evidence_items:
        raise ValueError(f"{location} 证据不足时 evidence 必须为空数组")
    if not checked_gap.strip():
        raise ValueError(f"{location} 证据不足时 evidence_gap 不得为空")
    return None, []


def fixed_judgment_boundary(input_type: str) -> dict[str, str]:
    return {
        "allowed_judgment": default_allowed_judgment(input_type),
        "forbidden_extrapolation": default_forbidden_extrapolation(input_type),
    }

def default_allowed_judgment(input_type: str) -> str:
    return {
        "online_full": "市场事实与文本商业执行分离判断",
        "unpublished_full": "整书文本商业执行潜力与连载结构风险",
        "first_three": "开篇文本执行潜力与首轮兑现能力",
        "single_chapter": "本章追读执行强度",
        "fragment": "局部爆款机制承载度",
    }[input_type]


def default_forbidden_extrapolation(input_type: str) -> str:
    if input_type in {"fragment", "single_chapter"}:
        return "不得外推整书爆款、真实留存、签约率、收入或连载稳定性"
    return "不得虚构真实市场数据、具体爆款概率、签约率、留存率或收入"


def extraction_template(task: dict[str, Any]) -> dict[str, Any]:
    def axis_item(name: str) -> dict[str, Any]:
        return {
            "axis": name,
            "evidence_sufficient": False,
            "score": None,
            "confidence": 0,
            "overload_risk": "低",
            "evidence": [],
            "judgment": "",
            "root_issue": "",
            "related_axes": [],
            "evidence_gap": "待提取",
        }

    def gate_item(name: str) -> dict[str, Any]:
        return {
            "gate": name,
            "evidence_sufficient": False,
            "score": None,
            "confidence": 0,
            "evidence": [],
            "judgment": "",
            "evidence_gap": "待提取",
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "rubric_version": RUBRIC_VERSION,
        "task_id": task["task_id"],
        "source_sha256": task["source"]["sha256"],
        "input_type": task["input_type"],
        "extractor": {"name": "Codex", "run_note": ""},
        "mainline": {
            "core_viewpoint": "",
            "current_goal": "",
            "current_obstacle": "",
            "gained_or_lost": "",
            "situation_change": "",
            "next_commitment": "",
            "one_sentence_mainline": "",
            "readability_risk": "证据不足",
            "missing_items": ["待提取"],
        },
        "axes": [axis_item(name) for name in AXIS_NAMES],
        "gates": [gate_item(name) for name in GATE_NAMES],
        "top_issues": [],
        "evidence_gaps": [],
        "extraction_confidence": 0,
    }

def extraction_schema() -> dict[str, Any]:
    axis_enum = AXIS_NAMES
    gate_enum = GATE_NAMES
    evidence_conditional = {
        "if": {"properties": {"evidence_sufficient": {"const": True}}, "required": ["evidence_sufficient"]},
        "then": {
            "properties": {
                "score": {"type": "integer", "minimum": 0, "maximum": 4},
                "confidence": {"type": "integer", "minimum": 1, "maximum": 100},
                "evidence": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 2}},
                "judgment": {"type": "string", "minLength": 1},
                "evidence_gap": {"const": ""},
            }
        },
        "else": {
            "properties": {
                "score": {"type": "null"},
                "evidence": {"type": "array", "maxItems": 0},
                "evidence_gap": {"type": "string", "minLength": 1},
            }
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://local.invalid/eight-dimension-pseudo-linear-probe-v3.2.1.schema.json",
        "title": "八维伪线性探针 v3.2.1 特征提取",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema_version", "rubric_version", "task_id", "source_sha256", "input_type",
            "extractor", "mainline", "axes", "gates", "top_issues", "evidence_gaps",
            "extraction_confidence",
        ],
        "properties": {
            "schema_version": {"const": SCHEMA_VERSION},
            "rubric_version": {"const": RUBRIC_VERSION},
            "task_id": {"type": "string", "minLength": 1},
            "source_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "input_type": {"enum": list(INPUT_TYPES)},
            "extractor": {
                "type": "object", "additionalProperties": False,
                "required": ["name", "run_note"],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "run_note": {"type": "string"},
                },
            },
            "mainline": {
                "type": "object", "additionalProperties": False,
                "required": [
                    "core_viewpoint", "current_goal", "current_obstacle", "gained_or_lost",
                    "situation_change", "next_commitment", "one_sentence_mainline",
                    "readability_risk", "missing_items",
                ],
                "properties": {
                    "core_viewpoint": {"type": "string"}, "current_goal": {"type": "string"},
                    "current_obstacle": {"type": "string"}, "gained_or_lost": {"type": "string"},
                    "situation_change": {"type": "string"}, "next_commitment": {"type": "string"},
                    "one_sentence_mainline": {"type": "string"},
                    "readability_risk": {"enum": sorted(READABILITY_LEVELS)},
                    "missing_items": {"type": "array", "items": {"type": "string", "minLength": 1}},
                },
            },
            "axes": {
                "type": "array", "minItems": 8, "maxItems": 8,
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": [
                        "axis", "evidence_sufficient", "score", "confidence", "overload_risk",
                        "evidence", "judgment", "root_issue", "related_axes", "evidence_gap",
                    ],
                    "properties": {
                        "axis": {"enum": axis_enum}, "evidence_sufficient": {"type": "boolean"},
                        "score": {"type": ["integer", "null"], "minimum": 0, "maximum": 4},
                        "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
                        "overload_risk": {"enum": sorted(RISK_LEVELS)},
                        "evidence": {"type": "array", "items": {"type": "string"}},
                        "judgment": {"type": "string"}, "root_issue": {"type": "string"},
                        "related_axes": {"type": "array", "uniqueItems": True, "items": {"enum": axis_enum}},
                        "evidence_gap": {"type": "string"},
                    },
                    "allOf": [evidence_conditional],
                },
            },
            "gates": {
                "type": "array", "minItems": 6, "maxItems": 6,
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": [
                        "gate", "evidence_sufficient", "score", "confidence",
                        "evidence", "judgment", "evidence_gap",
                    ],
                    "properties": {
                        "gate": {"enum": gate_enum}, "evidence_sufficient": {"type": "boolean"},
                        "score": {"type": ["integer", "null"], "minimum": 0, "maximum": 4},
                        "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
                        "evidence": {"type": "array", "items": {"type": "string"}},
                        "judgment": {"type": "string"}, "evidence_gap": {"type": "string"},
                    },
                    "allOf": [evidence_conditional],
                },
            },
            "top_issues": {
                "type": "array", "maxItems": 3,
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": [
                        "issue_id", "primary_axis", "related_axes", "location", "evidence",
                        "root_cause", "commercial_damage", "minimum_change",
                    ],
                    "properties": {
                        "issue_id": {"type": "string", "minLength": 1},
                        "primary_axis": {"enum": axis_enum},
                        "related_axes": {"type": "array", "uniqueItems": True, "items": {"enum": axis_enum}},
                        "location": {"type": "string", "minLength": 1},
                        "evidence": {"type": "string", "minLength": 2},
                        "root_cause": {"type": "string", "minLength": 1},
                        "commercial_damage": {"type": "string", "minLength": 1},
                        "minimum_change": {"type": "string", "minLength": 1},
                    },
                },
            },
            "evidence_gaps": {"type": "array", "items": {"type": "string", "minLength": 1}},
            "extraction_confidence": {"type": "integer", "minimum": 0, "maximum": 100},
        },
    }

def validate_task(task: dict[str, Any]) -> dict[str, Any]:
    exact_keys(
        task,
        {"schema_version", "rubric_version", "task_id", "created_at", "input_type", "source", "metadata", "text", "truncated"},
        "task",
    )
    if task["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"task.schema_version 必须为 {SCHEMA_VERSION}")
    if task["rubric_version"] != RUBRIC_VERSION:
        raise ValueError(f"task.rubric_version 必须为 {RUBRIC_VERSION}")
    expect_str(task["task_id"], "task.task_id", allow_empty=False)
    expect_str(task["created_at"], "task.created_at", allow_empty=False)
    input_type = expect_str(task["input_type"], "task.input_type")
    if input_type not in INPUT_TYPES:
        raise ValueError(f"task.input_type 非法：{input_type}")
    source = expect_dict(task["source"], "task.source")
    exact_keys(source, {"name", "path", "sha256", "character_count"}, "task.source")
    expect_str(source["name"], "task.source.name", allow_empty=False)
    expect_str(source["path"], "task.source.path", allow_empty=False)
    expected_hash = expect_str(source["sha256"], "task.source.sha256", allow_empty=False)
    if len(expected_hash) != 64 or any(ch not in "0123456789abcdef" for ch in expected_hash):
        raise ValueError("task.source.sha256 必须是 64 位小写十六进制")
    if isinstance(source["character_count"], bool) or not isinstance(source["character_count"], int) or source["character_count"] < 0:
        raise ValueError("task.source.character_count 必须是非负整数")
    expect_dict(task["metadata"], "task.metadata")
    text = expect_str(task["text"], "task.text")
    expect_bool(task["truncated"], "task.truncated")
    if sha256_text(text) != expected_hash:
        raise ValueError("task.text 与 task.source.sha256 不一致")
    if len(text) != source["character_count"]:
        raise ValueError("task.text 长度与 task.source.character_count 不一致")
    return task


def validate_extraction(extraction: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    exact_keys(
        extraction,
        {
            "schema_version", "rubric_version", "task_id", "source_sha256", "input_type",
            "extractor", "mainline", "axes", "gates", "top_issues", "evidence_gaps",
            "extraction_confidence",
        },
        "extraction",
    )
    if extraction["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"extraction.schema_version 必须为 {SCHEMA_VERSION}")
    if extraction["rubric_version"] != RUBRIC_VERSION:
        raise ValueError(f"extraction.rubric_version 必须为 {RUBRIC_VERSION}")
    if extraction["task_id"] != task["task_id"]:
        raise ValueError("extraction.task_id 与 task.json 不一致")
    if extraction["source_sha256"] != task["source"]["sha256"]:
        raise ValueError("extraction.source_sha256 与 task.json 不一致")
    if extraction["input_type"] != task["input_type"]:
        raise ValueError("extraction.input_type 与 task.json 不一致")
    source_text = task["text"]

    extractor = expect_dict(extraction["extractor"], "extraction.extractor")
    exact_keys(extractor, {"name", "run_note"}, "extraction.extractor")
    expect_str(extractor["name"], "extraction.extractor.name", allow_empty=False)
    expect_str(extractor["run_note"], "extraction.extractor.run_note")

    mainline = expect_dict(extraction["mainline"], "extraction.mainline")
    exact_keys(
        mainline,
        {
            "core_viewpoint", "current_goal", "current_obstacle", "gained_or_lost",
            "situation_change", "next_commitment", "one_sentence_mainline",
            "readability_risk", "missing_items",
        },
        "extraction.mainline",
    )
    mainline_keys = (
        "core_viewpoint", "current_goal", "current_obstacle", "gained_or_lost",
        "situation_change", "next_commitment", "one_sentence_mainline",
    )
    for key in mainline_keys:
        expect_str(mainline[key], f"extraction.mainline.{key}")
    risk = expect_str(mainline["readability_risk"], "extraction.mainline.readability_risk")
    if risk not in READABILITY_LEVELS:
        raise ValueError(f"readability_risk 非法：{risk}")
    missing_items = expect_str_list(mainline["missing_items"], "extraction.mainline.missing_items")
    nonempty_count = sum(bool(mainline[key].strip()) for key in mainline_keys)
    if risk == "低":
        if nonempty_count < 5 or not mainline["one_sentence_mainline"].strip():
            raise ValueError("readability_risk=低 时主线字段至少五项非空，且一句话主线不得为空")
        if missing_items:
            raise ValueError("readability_risk=低 时 missing_items 必须为空")
    elif risk in {"中", "高", "证据不足"} and nonempty_count < 5 and not missing_items:
        raise ValueError(f"readability_risk={risk} 且主线信息不完整时必须列出 missing_items")

    axis_items = expect_list(extraction["axes"], "extraction.axes")
    axis_map: dict[str, dict[str, Any]] = {}
    axis_keys = {
        "axis", "evidence_sufficient", "score", "confidence", "overload_risk",
        "evidence", "judgment", "root_issue", "related_axes", "evidence_gap",
    }
    for index, raw in enumerate(axis_items):
        item = expect_dict(raw, f"extraction.axes[{index}]")
        exact_keys(item, axis_keys, f"extraction.axes[{index}]")
        name = expect_str(item["axis"], f"extraction.axes[{index}].axis")
        if name not in AXIS_NAMES:
            raise ValueError(f"未知维度：{name}")
        if name in axis_map:
            raise ValueError(f"重复维度：{name}")
        sufficient = expect_bool(item["evidence_sufficient"], f"{name}.evidence_sufficient")
        checked_score, checked_evidence = validate_evidence_state(
            sufficient=sufficient, score=item["score"], confidence=item["confidence"],
            evidence=item["evidence"], judgment=item["judgment"], evidence_gap=item["evidence_gap"],
            source_text=source_text, location=name,
        )
        item["score"] = checked_score
        item["evidence"] = checked_evidence
        overload = expect_str(item["overload_risk"], f"{name}.overload_risk")
        if overload not in RISK_LEVELS:
            raise ValueError(f"{name}.overload_risk 非法：{overload}")
        expect_str(item["root_issue"], f"{name}.root_issue")
        related = expect_str_list(item["related_axes"], f"{name}.related_axes")
        if name in related:
            raise ValueError(f"{name}.related_axes 不得包含自身")
        invalid_related = [value for value in related if value not in AXIS_NAMES]
        if invalid_related:
            raise ValueError(f"{name}.related_axes 含非法维度：{invalid_related}")
        if len(set(related)) != len(related):
            raise ValueError(f"{name}.related_axes 存在重复值")
        axis_map[name] = item
    missing_axes = [name for name in AXIS_NAMES if name not in axis_map]
    if missing_axes or len(axis_map) != len(AXIS_NAMES):
        raise ValueError(f"八维不完整。缺失={missing_axes}")
    extraction["axes"] = [axis_map[name] for name in AXIS_NAMES]

    # 防止同一原句在多个高分轴上重复计权。允许共享上下文，
    # 但三个及以上高分轴不能只依赖同一句证据。
    quote_axes: dict[str, set[str]] = {}
    for axis in extraction["axes"]:
        if axis["evidence_sufficient"] and axis["score"] is not None and axis["score"] >= 3:
            for quote in axis["evidence"]:
                quote_axes.setdefault(quote, set()).add(axis["axis"])
    overused = {quote: sorted(names) for quote, names in quote_axes.items() if len(names) >= 3}
    if overused:
        details = "；".join(f"{quote!r}→{'、'.join(names)}" for quote, names in overused.items())
        raise ValueError("同一原句不得作为三个及以上高分维度的重复正向证据：" + details)

    gate_items = expect_list(extraction["gates"], "extraction.gates")
    gate_map: dict[str, dict[str, Any]] = {}
    gate_keys = {"gate", "evidence_sufficient", "score", "confidence", "evidence", "judgment", "evidence_gap"}
    for index, raw in enumerate(gate_items):
        item = expect_dict(raw, f"extraction.gates[{index}]")
        exact_keys(item, gate_keys, f"extraction.gates[{index}]")
        name = expect_str(item["gate"], f"extraction.gates[{index}].gate")
        if name not in GATE_NAMES:
            raise ValueError(f"未知商业门：{name}")
        if name in gate_map:
            raise ValueError(f"重复商业门：{name}")
        sufficient = expect_bool(item["evidence_sufficient"], f"{name}.evidence_sufficient")
        checked_score, checked_evidence = validate_evidence_state(
            sufficient=sufficient, score=item["score"], confidence=item["confidence"],
            evidence=item["evidence"], judgment=item["judgment"], evidence_gap=item["evidence_gap"],
            source_text=source_text, location=name,
        )
        item["score"] = checked_score
        item["evidence"] = checked_evidence
        gate_map[name] = item
    missing_gates = [name for name in GATE_NAMES if name not in gate_map]
    if missing_gates or len(gate_map) != len(GATE_NAMES):
        raise ValueError(f"六门不完整。缺失={missing_gates}")
    extraction["gates"] = [gate_map[name] for name in GATE_NAMES]

    issues = expect_list(extraction["top_issues"], "extraction.top_issues")
    if len(issues) > 3:
        raise ValueError("top_issues 最多三项")
    issue_ids: set[str] = set()
    issue_keys = {
        "issue_id", "primary_axis", "related_axes", "location", "evidence",
        "root_cause", "commercial_damage", "minimum_change",
    }
    for index, raw in enumerate(issues):
        issue = expect_dict(raw, f"extraction.top_issues[{index}]")
        exact_keys(issue, issue_keys, f"extraction.top_issues[{index}]")
        issue_id = expect_str(issue["issue_id"], f"issue[{index}].issue_id", allow_empty=False)
        if issue_id in issue_ids:
            raise ValueError(f"重复 issue_id：{issue_id}")
        issue_ids.add(issue_id)
        primary = expect_str(issue["primary_axis"], f"{issue_id}.primary_axis")
        if primary not in AXIS_NAMES:
            raise ValueError(f"{issue_id}.primary_axis 非法：{primary}")
        related = expect_str_list(issue["related_axes"], f"{issue_id}.related_axes")
        if primary in related:
            raise ValueError(f"{issue_id}.related_axes 不得包含主轴")
        if any(value not in AXIS_NAMES for value in related):
            raise ValueError(f"{issue_id}.related_axes 含非法维度")
        if len(set(related)) != len(related):
            raise ValueError(f"{issue_id}.related_axes 存在重复值")
        for key in ("location", "root_cause", "commercial_damage", "minimum_change"):
            expect_str(issue[key], f"{issue_id}.{key}", allow_empty=False)
        issue["evidence"] = validate_source_quote(issue["evidence"], source_text, f"{issue_id}.evidence")

    expect_str_list(extraction["evidence_gaps"], "extraction.evidence_gaps")
    expect_int_range(extraction["extraction_confidence"], "extraction.extraction_confidence", 0, 100)
    return extraction

def load_weights(path: Path | None) -> WeightSet:
    if path is None:
        return WeightSet(
            weights=DEFAULT_WEIGHTS.copy(),
            bias=DEFAULT_BIAS,
            thresholds=DEFAULT_THRESHOLDS.copy(),
            critical_axes=tuple(DEFAULT_CRITICAL_AXES),
            source="内置工程初始权重",
            status="uncalibrated",
        )
    data = load_json_object(path)
    weights = expect_dict(data.get("weights"), "weights")
    checked: dict[str, float] = {}
    for axis in AXIS_NAMES:
        if axis not in weights:
            raise ValueError(f"权重文件缺少维度：{axis}")
        value = weights[axis]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ValueError(f"权重 {axis} 必须是有限数字")
        checked[axis] = float(value)
    extra = sorted(set(weights) - set(AXIS_NAMES))
    if extra:
        raise ValueError(f"权重文件含额外维度：{extra}")
    if sum(abs(value) for value in checked.values()) <= 0:
        raise ValueError("权重绝对值总和必须大于 0")

    bias_value = data.get("bias", 0.0)
    if isinstance(bias_value, bool) or not isinstance(bias_value, (int, float)) or not math.isfinite(float(bias_value)):
        raise ValueError("bias 必须是有限数字")

    thresholds_raw = data.get("thresholds", DEFAULT_THRESHOLDS)
    thresholds = expect_dict(thresholds_raw, "thresholds")
    checked_thresholds: dict[str, float] = {}
    for key in ("high", "medium", "low", "minimum_coverage", "minimum_weighted_coverage"):
        value = thresholds.get(key, DEFAULT_THRESHOLDS[key])
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"thresholds.{key} 必须是数字")
        checked_thresholds[key] = float(value)
    if not (0.0 <= checked_thresholds["low"] < checked_thresholds["medium"] < checked_thresholds["high"] <= 1.0):
        raise ValueError("阈值必须满足 0≤low<medium<high≤1")
    for key in ("minimum_coverage", "minimum_weighted_coverage"):
        if not 0.0 <= checked_thresholds[key] <= 1.0:
            raise ValueError(f"{key} 必须位于 0—1")

    raw_critical = data.get("critical_axes", DEFAULT_CRITICAL_AXES)
    critical = expect_str_list(raw_critical, "critical_axes")
    invalid_critical = [axis for axis in critical if axis not in AXIS_NAMES]
    if invalid_critical:
        raise ValueError(f"critical_axes 含非法维度：{invalid_critical}")
    if len(set(critical)) != len(critical):
        raise ValueError("critical_axes 存在重复值")

    return WeightSet(
        weights=checked,
        bias=float(bias_value),
        thresholds=checked_thresholds,
        critical_axes=tuple(critical),
        source=str(path),
        status=str(data.get("status", data.get("type", "unknown"))),
    )


def compute_linear_result(extraction: dict[str, Any], weight_set: WeightSet) -> dict[str, Any]:
    features: dict[str, float | None] = {}
    contributions: dict[str, float | None] = {}
    overload_factors: dict[str, float | None] = {}
    available = 0
    available_weight = 0.0
    total_weight = sum(abs(weight_set.weights[name]) for name in AXIS_NAMES)
    z = weight_set.bias
    high_overload_axes: list[str] = []
    missing_axes: list[str] = []

    risk_factor = {"低": 1.0, "中": 0.70, "高": 0.25}
    for axis in extraction["axes"]:
        name = axis["axis"]
        if not axis["evidence_sufficient"] or axis["score"] is None:
            features[name] = None
            contributions[name] = None
            overload_factors[name] = None
            missing_axes.append(name)
            continue
        normalized = (float(axis["score"]) - 2.0) / 2.0
        reliability = clamp(float(axis["confidence"]) / 100.0, 0.0, 1.0)
        factor = risk_factor[axis["overload_risk"]] if normalized > 0 else 1.0
        if axis["overload_risk"] == "高" and axis["score"] >= 3:
            high_overload_axes.append(name)
        feature = normalized * reliability * factor
        contribution = weight_set.weights[name] * feature
        features[name] = round(feature, 6)
        contributions[name] = round(contribution, 6)
        overload_factors[name] = factor
        z += contribution
        available += 1
        available_weight += abs(weight_set.weights[name])

    coverage = available / len(AXIS_NAMES)
    weighted_coverage = available_weight / total_weight if total_weight > 0 else 0.0
    missing_critical_axes = [name for name in weight_set.critical_axes if name in missing_axes]
    activation = sigmoid(z)
    thresholds = weight_set.thresholds
    if (
        coverage < thresholds["minimum_coverage"]
        or weighted_coverage < thresholds["minimum_weighted_coverage"]
        or missing_critical_axes
    ):
        raw_level = "证据不足"
    elif activation >= thresholds["high"]:
        raw_level = "高"
    elif activation >= thresholds["medium"]:
        raw_level = "中"
    elif activation >= thresholds["low"]:
        raw_level = "低"
    else:
        raw_level = "很低"

    input_type = extraction["input_type"]
    judgment_name = {
        "fragment": "局部爆款机制承载度",
        "single_chapter": "本章追读执行强度",
        "first_three": "开篇文本执行潜力",
        "online_full": "文本商业执行潜力",
        "unpublished_full": "文本商业执行潜力",
    }[input_type]

    final_level = raw_level
    cap_reasons: list[str] = []
    if raw_level == "证据不足":
        if coverage < thresholds["minimum_coverage"]:
            cap_reasons.append(f"有效维度覆盖率不足：{coverage:.1%}")
        if weighted_coverage < thresholds["minimum_weighted_coverage"]:
            cap_reasons.append(f"权重覆盖率不足：{weighted_coverage:.1%}")
        if missing_critical_axes:
            cap_reasons.append("关键轴证据不足：" + "、".join(missing_critical_axes))

    if len(high_overload_axes) >= 2 and final_level == "高":
        final_level = "中"
        cap_reasons.append("至少两个高分维度存在高过载风险，高等级被下调：" + "、".join(high_overload_axes))

    if input_type in {"online_full", "unpublished_full", "first_three"}:
        gates = {gate["gate"]: gate for gate in extraction["gates"]}
        hard_names = ["卖点识别门", "情绪承诺门", "主角发动机门", "最小兑现门"]
        missing = [name for name in hard_names if not gates[name]["evidence_sufficient"] or gates[name]["score"] is None]
        failed = [name for name in hard_names if gates[name]["evidence_sufficient"] and gates[name]["score"] is not None and gates[name]["score"] < 2]
        if missing:
            final_level = "证据不足"
            cap_reasons.append("关键商业门证据不足：" + "、".join(missing))
        elif failed and final_level in {"高", "中"}:
            final_level = "低"
            cap_reasons.append("关键商业门未过，八维高分不得补偿：" + "、".join(failed))

    readability = extraction["mainline"]["readability_risk"]
    if readability == "证据不足" and final_level in {"高", "中"}:
        final_level = "证据不足"
        cap_reasons.append("主线复述证据不足，禁止输出中高等级")
    elif readability == "高" and final_level == "高":
        final_level = "中"
        cap_reasons.append("主线可读性高风险，高等级被下调")

    positive = sorted(
        ({"axis": name, "contribution": value} for name, value in contributions.items() if value is not None and value > 0),
        key=lambda item: item["contribution"], reverse=True,
    )
    negative = sorted(
        ({"axis": name, "contribution": value} for name, value in contributions.items() if value is not None and value < 0),
        key=lambda item: item["contribution"],
    )
    return {
        "judgment_name": judgment_name,
        "judgment_boundary": fixed_judgment_boundary(input_type),
        "raw_z": round(z, 6),
        "activation": round(activation, 6),
        "activation_note": "内部线性激活值，不是市场成功概率",
        "coverage": round(coverage, 6),
        "weighted_coverage": round(weighted_coverage, 6),
        "missing_axes": missing_axes,
        "missing_critical_axes": missing_critical_axes,
        "raw_level": raw_level,
        "final_level": final_level,
        "cap_reasons": cap_reasons,
        "features": features,
        "overload_factors": overload_factors,
        "high_overload_axes": high_overload_axes,
        "weights": weight_set.weights,
        "critical_axes": list(weight_set.critical_axes),
        "bias": weight_set.bias,
        "thresholds": weight_set.thresholds,
        "weight_source": weight_set.source,
        "weight_status": weight_set.status,
        "contributions": contributions,
        "top_positive": positive[:3],
        "top_negative": negative[:3],
    }

def sanitize_md(value: Any) -> str:
    if value is None:
        return "—"
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def render_markdown_report(report: dict[str, Any]) -> str:
    extraction = report["extraction"]
    linear = report["linear_result"]
    run = report["run"]
    lines: list[str] = ["# 八维伪线性探针报告", ""]
    lines.extend(
        [
            f"- 脚本版本：`{run['version']}`",
            f"- 规则版本：`{run['rubric_version']}`",
            f"- 输入：`{run['source_name']}`",
            f"- 输入类型：{INPUT_TYPES[extraction['input_type']]}",
            f"- 特征提取端：`{extraction['extractor']['name']}`",
            f"- 权重状态：`{linear['weight_status']}`",
            "",
            "> 边界：Codex 负责文本特征提取；本地脚本不调用 API。activation 只是固定八维向量经过线性头后的内部值，不是爆款概率、签约率、留存率或收入预测。",
            "",
            "## 1. 判定边界",
            "",
            f"- 本次允许判断：{linear['judgment_boundary']['allowed_judgment']}",
            f"- 本次禁止外推：{linear['judgment_boundary']['forbidden_extrapolation']}",
            f"- {linear['judgment_name']}：**{linear['final_level']}**",
            f"- 线性激活值：`{linear['activation']:.4f}`",
            f"- 特征覆盖率：`{linear['coverage']:.1%}`",
            f"- 权重覆盖率：`{linear['weighted_coverage']:.1%}`",
            f"- 关键轴：`{'、'.join(linear['critical_axes'])}`",
        ]
    )
    if linear["cap_reasons"]:
        lines.append("- 门控/下调原因：" + "；".join(linear["cap_reasons"]))
    lines.extend(["", "## 2. 主线复述风险锁", "", "| 项目 | 结果 |", "|---|---|"])
    m = extraction["mainline"]
    mapping = [
        ("核心视角", "core_viewpoint"), ("当前目标", "current_goal"),
        ("当前阻力", "current_obstacle"), ("获得或失去", "gained_or_lost"),
        ("局势变化", "situation_change"), ("下一步承诺", "next_commitment"),
        ("一句话主线", "one_sentence_mainline"), ("可读性风险", "readability_risk"),
    ]
    for label, key in mapping:
        lines.append(f"| {label} | {sanitize_md(m[key])} |")

    axis_map = {axis["axis"]: axis for axis in extraction["axes"]}
    lines.extend(
        [
            "", "## 3. 八维向量与线性贡献", "",
            "| 维度 | 分数 | 置信度 | 有效特征 x | 权重 w | 贡献 w×x | 过载 | 证据 |",
            "|---|---:|---:|---:|---:|---:|---|---|",
        ]
    )
    for name in AXIS_NAMES:
        axis = axis_map[name]
        feature = linear["features"][name]
        contribution = linear["contributions"][name]
        evidence = "；".join(axis["evidence"][:2]) if axis["evidence"] else axis["evidence_gap"]
        lines.append(
            "| " + " | ".join(
                [
                    sanitize_md(name), sanitize_md(axis["score"]), f"{axis['confidence']}%",
                    "—" if feature is None else f"{feature:.4f}",
                    f"{linear['weights'][name]:.4f}",
                    "—" if contribution is None else f"{contribution:.4f}",
                    sanitize_md(axis["overload_risk"]), sanitize_md(evidence),
                ]
            ) + " |"
        )

    lines.extend(["", "## 4. 商业六门", "", "| 商业门 | 分数 | 置信度 | 判断 | 证据 |", "|---|---:|---:|---|---|"])
    for gate in extraction["gates"]:
        evidence = "；".join(gate["evidence"][:2]) if gate["evidence"] else gate["evidence_gap"]
        lines.append(
            f"| {sanitize_md(gate['gate'])} | {sanitize_md(gate['score'])} | {gate['confidence']}% | "
            f"{sanitize_md(gate['judgment'])} | {sanitize_md(evidence)} |"
        )

    lines.extend(["", "## 5. 主要正负贡献", ""])
    pos = "、".join(f"{item['axis']}({item['contribution']:+.3f})" for item in linear["top_positive"])
    neg = "、".join(f"{item['axis']}({item['contribution']:+.3f})" for item in linear["top_negative"])
    lines.append(f"- 主要正贡献：{pos or '无'}")
    lines.append(f"- 主要负贡献：{neg or '无'}")

    lines.extend(["", "## 6. 优先级问题", ""])
    if extraction["top_issues"]:
        lines.extend(["| 编号 | 主轴 | 位置 | 根因 | 商业损伤 | 最小改动 |", "|---|---|---|---|---|---|"])
        for issue in extraction["top_issues"]:
            lines.append(
                f"| {sanitize_md(issue['issue_id'])} | {sanitize_md(issue['primary_axis'])} | "
                f"{sanitize_md(issue['location'])} | {sanitize_md(issue['root_cause'])} | "
                f"{sanitize_md(issue['commercial_damage'])} | {sanitize_md(issue['minimum_change'])} |"
            )
    else:
        lines.append("未提取到可确认的优先级问题。")

    lines.extend(["", "## 7. 证据缺口", ""])
    for gap in extraction["evidence_gaps"] or ["未记录额外证据缺口"]:
        lines.append(f"- {gap}")
    lines.extend(["", f"特征提取置信度：`{extraction['extraction_confidence']}%`", ""])
    return "\n".join(lines)


def make_task(
    *, input_path: Path, text: str, input_type: str, metadata: dict[str, Any], truncated: bool
) -> dict[str, Any]:
    digest = sha256_text(text)
    identity_payload = json.dumps(
        {"sha256": digest, "input_type": input_type, "metadata": metadata, "rubric": RUBRIC_VERSION},
        ensure_ascii=False,
        sort_keys=True,
    )
    task_id = hashlib.sha256(identity_payload.encode("utf-8")).hexdigest()[:20]
    return {
        "schema_version": SCHEMA_VERSION,
        "rubric_version": RUBRIC_VERSION,
        "task_id": task_id,
        "created_at": utc_now(),
        "input_type": input_type,
        "source": {
            "name": input_path.name,
            "path": str(input_path),
            "sha256": digest,
            "character_count": len(text),
        },
        "metadata": metadata,
        "text": text,
        "truncated": truncated,
    }


def prepare_task(args: argparse.Namespace) -> None:
    input_path = Path(args.input).resolve()
    text = read_text_file(input_path)
    text, truncated = validate_text_length(text, args.max_chars, args.allow_truncate)
    metadata = load_json_object(Path(args.metadata).resolve() if args.metadata else None)
    task = make_task(
        input_path=input_path,
        text=text,
        input_type=args.input_type,
        metadata=metadata,
        truncated=truncated,
    )
    validate_task(task)
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    task_path = output_dir / "task.json"
    extraction_path = output_dir / "extraction.json"
    report_path = output_dir / "probe.report.json"
    write_json(task_path, task)
    write_json(output_dir / "extraction.template.json", extraction_template(task))
    write_json(output_dir / "extraction.schema.json", extraction_schema())
    cwd = Path.cwd().resolve()
    script_ref = os.path.relpath(Path(__file__).resolve(), cwd)
    task_ref = os.path.relpath(task_path, cwd)
    extraction_ref = os.path.relpath(extraction_path, cwd)
    report_ref = os.path.relpath(report_path, cwd)
    local_command = (
        "\n\n## 当前任务本地计算命令\n\n"
        "从执行 `prepare` 时的项目目录运行：\n\n"
        "```powershell\n"
        f'python "{script_ref}" score --task "{task_ref}" '
        f'--extraction "{extraction_ref}" --output "{report_ref}"\n'
        "```\n"
    )
    (output_dir / "CODEX_TASK.md").write_text(CODEX_INSTRUCTION + local_command, encoding="utf-8")
    print(f"任务目录：{output_dir}")
    print(f"任务文件：{output_dir / 'task.json'}")
    print(f"Codex 指令：{output_dir / 'CODEX_TASK.md'}")
    print("下一步：让 Codex 生成 extraction.json；本脚本不会调用 API。")


def score_files(args: argparse.Namespace) -> dict[str, Any]:
    task_path = Path(args.task).resolve()
    extraction_path = Path(args.extraction).resolve()
    task = validate_task(load_json_object(task_path))
    extraction = validate_extraction(load_json_object(extraction_path), task)
    weight_set = load_weights(Path(args.weights).resolve() if args.weights else None)
    linear = compute_linear_result(extraction, weight_set)
    report = {
        "run": {
            "version": VERSION,
            "schema_version": SCHEMA_VERSION,
            "rubric_version": RUBRIC_VERSION,
            "created_at": utc_now(),
            "task": str(task_path),
            "extraction": str(extraction_path),
            "source_name": task["source"]["name"],
            "source_sha256": task["source"]["sha256"],
            "input_type": task["input_type"],
            "truncated": task["truncated"],
            "metadata": task["metadata"],
            "api_called_by_script": False,
        },
        "extraction": extraction,
        "linear_result": linear,
    }
    output_json = Path(args.output).resolve()
    output_md = Path(args.markdown).resolve() if args.markdown else output_json.with_suffix(".md")
    write_json(output_json, report)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(render_markdown_report(report), encoding="utf-8")
    print(f"JSON 报告：{output_json}")
    print(f"Markdown 报告：{output_md}")
    print(
        f"{linear['judgment_name']}：{linear['final_level']}；"
        f"activation={linear['activation']:.4f}（非概率）"
    )
    return report


def batch_score(args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    extraction_name = args.extraction_name
    task_name = args.task_name
    extractions = sorted(root.rglob(extraction_name))
    if not extractions:
        raise ValueError(f"未找到 {extraction_name}：{root}")
    output_dir = Path(args.output_dir).resolve()
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for extraction_path in extractions:
        task_path = extraction_path.with_name(task_name)
        relative_dir = extraction_path.parent.relative_to(root)
        out_json = output_dir / relative_dir / "probe.report.json"
        try:
            local_args = argparse.Namespace(
                task=str(task_path), extraction=str(extraction_path), output=str(out_json),
                markdown=None, weights=args.weights,
            )
            report = score_files(local_args)
            linear = report["linear_result"]
            rows.append(
                {
                    "source": report["run"]["source_name"],
                    "task_dir": str(relative_dir),
                    "level": linear["final_level"],
                    "activation": linear["activation"],
                    "coverage": linear["coverage"],
                    "report": str(out_json),
                }
            )
        except Exception as exc:
            failures.append({"extraction": str(extraction_path), "error": str(exc)})
            print(f"[FAIL] {extraction_path}: {exc}", file=sys.stderr)
    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "probe_index.csv"
    with index_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source", "task_dir", "level", "activation", "coverage", "report"])
        writer.writeheader()
        writer.writerows(rows)
    write_json(output_dir / "probe_failures.json", failures)
    print(f"批处理索引：{index_path}")
    print(f"成功 {len(rows)}，失败 {len(failures)}")


def read_report(path: Path) -> dict[str, Any]:
    data = load_json_object(path)
    if "linear_result" not in data or "extraction" not in data or "run" not in data:
        raise ValueError(f"不是有效探针报告：{path}")
    return data


def compare_reports(args: argparse.Namespace) -> None:
    before_path = Path(args.before).resolve()
    after_path = Path(args.after).resolve()
    before = read_report(before_path)
    after = read_report(after_path)
    b = before["linear_result"]
    a = after["linear_result"]
    before_hash = before["run"].get("source_sha256")
    after_hash = after["run"].get("source_sha256")
    relation_warnings: list[str] = []
    relation: dict[str, Any] | None = None

    if args.relation:
        relation = load_json_object(Path(args.relation).resolve())
        exact_keys(
            relation,
            {"relation_type", "pair_id", "before_source_sha256", "after_source_sha256", "note"},
            "relation",
        )
        if relation["relation_type"] != "revision_pair":
            raise ValueError("relation.relation_type 必须为 revision_pair")
        expect_str(relation["pair_id"], "relation.pair_id", allow_empty=False)
        expect_str(relation["note"], "relation.note")
        if relation["before_source_sha256"] != before_hash:
            raise ValueError("relation.before_source_sha256 与修改前报告不一致")
        if relation["after_source_sha256"] != after_hash:
            raise ValueError("relation.after_source_sha256 与修改后报告不一致")
    elif not args.force_unrelated:
        raise ValueError("compare 必须提供 --relation 修订关系文件；仅排错时可用 --force-unrelated")
    else:
        relation_warnings.append("未提供修订关系文件，本次仅作诊断比较，不得解释为修改收益")

    if before_hash == after_hash:
        if not args.force_unrelated:
            raise ValueError("修改前后正文 SHA-256 相同，禁止作为修订效果比较")
        relation_warnings.append("两份报告正文 SHA-256 相同")

    checks = {
        "脚本版本": (before["run"].get("version"), after["run"].get("version")),
        "规则版本": (before["run"].get("rubric_version"), after["run"].get("rubric_version")),
        "输入类型": (before["run"].get("input_type"), after["run"].get("input_type")),
        "特征提取端": (
            before["extraction"].get("extractor", {}).get("name"),
            after["extraction"].get("extractor", {}).get("name"),
        ),
        "权重": (b.get("weights"), a.get("weights")),
        "偏置": (b.get("bias"), a.get("bias")),
        "阈值": (b.get("thresholds"), a.get("thresholds")),
    }
    incompatible = [f"{name}: {left!r} != {right!r}" for name, (left, right) in checks.items() if left != right]
    if incompatible and not args.force_incompatible:
        raise ValueError(
            "两份报告口径不兼容，禁止直接比较：" + "；".join(incompatible)
            + "。排查时可使用 --force-incompatible，但结果不得作为改写优劣证据。"
        )
    axis_rows = []
    for axis in AXIS_NAMES:
        bf = b["features"].get(axis)
        af = a["features"].get(axis)
        delta = None if bf is None or af is None else round(float(af) - float(bf), 6)
        axis_rows.append({"axis": axis, "before_feature": bf, "after_feature": af, "delta": delta})
    comparison = {
        "version": VERSION,
        "created_at": utc_now(),
        "before": str(before_path),
        "after": str(after_path),
        "relation": relation,
        "activation_before": b["activation"],
        "activation_after": a["activation"],
        "activation_delta": round(float(a["activation"]) - float(b["activation"]), 6),
        "axis_deltas": axis_rows,
        "forced_incompatible": bool(incompatible),
        "forced_unrelated": bool(args.force_unrelated and relation is None),
        "compatibility_warnings": incompatible + relation_warnings,
        "note": "差值仅表示已声明修订关系、同一伪探针口径下的变化，不表示真实读者指标变化",
    }
    out = Path(args.output).resolve()
    write_json(out, comparison)
    md = [
        "# 八维伪线性探针对比", "",
        f"- 修订关系：`{relation['pair_id'] if relation else '未验证，仅诊断'}`",
        f"- 修改前 activation：`{b['activation']:.4f}`",
        f"- 修改后 activation：`{a['activation']:.4f}`",
        f"- 差值：`{comparison['activation_delta']:+.4f}`（非真实留存变化）",
    ]
    warnings = incompatible + relation_warnings
    if warnings:
        md.append("- **警告：本次比较存在兼容性或关系风险。**")
        md.extend(f"  - {item}" for item in warnings)
    md.extend(["", "| 维度 | 修改前特征 | 修改后特征 | Δ |", "|---|---:|---:|---:|"])
    for row in axis_rows:
        bf = "—" if row["before_feature"] is None else f"{row['before_feature']:.4f}"
        af = "—" if row["after_feature"] is None else f"{row['after_feature']:.4f}"
        delta = "—" if row["delta"] is None else f"{row['delta']:+.4f}"
        md.append(f"| {row['axis']} | {bf} | {af} | {delta} |")
    md_path = out.with_suffix(".md")
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"对比 JSON：{out}")
    print(f"对比 Markdown：{md_path}")

def report_to_training_vector(report: dict[str, Any]) -> list[float]:
    features = report["linear_result"]["features"]
    return [0.0 if features.get(axis) is None else float(features[axis]) for axis in AXIS_NAMES]


def dot(weights: list[float], vector: list[float]) -> float:
    return sum(w * x for w, x in zip(weights, vector, strict=True))


def train_logistic(
    samples: list[list[float]], labels: list[int], *, epochs: int, learning_rate: float, l2: float
) -> tuple[list[float], float]:
    width = len(AXIS_NAMES)
    weights = [0.0] * width
    bias = 0.0
    n = len(samples)
    for _ in range(epochs):
        grad_w = [0.0] * width
        grad_b = 0.0
        for x, y in zip(samples, labels, strict=True):
            p = sigmoid(bias + dot(weights, x))
            error = p - y
            for i in range(width):
                grad_w[i] += error * x[i]
            grad_b += error
        for i in range(width):
            grad_w[i] = grad_w[i] / n + l2 * weights[i]
            weights[i] -= learning_rate * grad_w[i]
        bias -= learning_rate * (grad_b / n)
    return weights, bias


def classification_metrics(
    samples: list[list[float]], labels: list[int], weights: list[float], bias: float
) -> dict[str, float]:
    tp = tn = fp = fn = 0
    log_loss = 0.0
    for x, y in zip(samples, labels, strict=True):
        p = clamp(sigmoid(bias + dot(weights, x)), 1e-9, 1 - 1e-9)
        pred = 1 if p >= 0.5 else 0
        log_loss += -(y * math.log(p) + (1 - y) * math.log(1 - p))
        if y == 1 and pred == 1:
            tp += 1
        elif y == 0 and pred == 0:
            tn += 1
        elif y == 0 and pred == 1:
            fp += 1
        else:
            fn += 1
    accuracy = (tp + tn) / max(1, len(labels))
    tpr = tp / max(1, tp + fn)
    tnr = tn / max(1, tn + fp)
    return {
        "accuracy": accuracy,
        "balanced_accuracy": (tpr + tnr) / 2.0,
        "log_loss": log_loss / max(1, len(labels)),
    }


def stratified_folds(labels: list[int], k: int, seed: int) -> list[list[int]]:
    rng = random.Random(seed)
    by_class: dict[int, list[int]] = {0: [], 1: []}
    for index, label in enumerate(labels):
        by_class[label].append(index)
    for indexes in by_class.values():
        rng.shuffle(indexes)
    folds = [[] for _ in range(k)]
    for indexes in by_class.values():
        for pos, index in enumerate(indexes):
            folds[pos % k].append(index)
    return folds


def fit_weights(args: argparse.Namespace) -> None:
    dataset_path = Path(args.dataset).resolve()
    base_dir = dataset_path.parent
    samples: list[list[float]] = []
    labels: list[int] = []
    sources: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    with dataset_path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            label = int(row["label"])
            if label not in (0, 1):
                raise ValueError(f"第 {line_no} 行 label 必须为 0 或 1")
            report_path = Path(row["report"])
            if not report_path.is_absolute():
                report_path = (base_dir / report_path).resolve()
            report = read_report(report_path)
            coverage = float(report["linear_result"]["coverage"])
            if coverage < args.min_coverage:
                raise ValueError(f"第 {line_no} 行覆盖率 {coverage:.1%} 低于 {args.min_coverage:.1%}：{report_path}")
            source_hash = expect_str(report["run"].get("source_sha256"), f"第 {line_no} 行 source_sha256", allow_empty=False)
            if source_hash in seen_hashes:
                raise ValueError(f"第 {line_no} 行正文 SHA-256 重复，禁止同一文本重复进入训练：{source_hash}")
            seen_hashes.add(source_hash)
            samples.append(report_to_training_vector(report))
            labels.append(label)
            sources.append({"report": str(report_path), "label": label, "source_sha256": source_hash})
    if not samples:
        raise ValueError("训练集为空")
    counts = {0: labels.count(0), 1: labels.count(1)}
    if len(set(labels)) < 2:
        raise ValueError("训练集必须同时包含 label=0 和 label=1")
    if not args.force_small_sample and (len(samples) < 40 or min(counts.values()) < 10):
        raise ValueError(f"样本不足：总数={len(samples)}，类别分布={counts}。默认至少 40 条且每类至少 10 条。")

    k = min(5, min(counts.values()))
    fold_metrics: list[dict[str, float]] = []
    if k >= 2:
        folds = stratified_folds(labels, k, args.seed)
        all_indexes = set(range(len(samples)))
        for fold in folds:
            test_set = set(fold)
            train_indexes = sorted(all_indexes - test_set)
            test_indexes = sorted(test_set)
            if not train_indexes or not test_indexes:
                continue
            train_labels = [labels[i] for i in train_indexes]
            if len(set(train_labels)) < 2:
                continue
            weights, bias = train_logistic(
                [samples[i] for i in train_indexes], train_labels,
                epochs=args.epochs, learning_rate=args.learning_rate, l2=args.l2,
            )
            fold_metrics.append(
                classification_metrics([samples[i] for i in test_indexes], [labels[i] for i in test_indexes], weights, bias)
            )

    final_weights, final_bias = train_logistic(
        samples, labels, epochs=args.epochs, learning_rate=args.learning_rate, l2=args.l2
    )
    aggregate = None
    if fold_metrics:
        aggregate = {
            key: sum(metric[key] for metric in fold_metrics) / len(fold_metrics)
            for key in ("accuracy", "balanced_accuracy", "log_loss")
        }
    status = "experimental_fitted_with_cv" if aggregate is not None else "experimental_fitted_no_cv"
    output = {
        "version": VERSION,
        "created_at": utc_now(),
        "type": "fitted_pseudo_linear_head",
        "status": status,
        "weights": {axis: round(final_weights[i], 8) for i, axis in enumerate(AXIS_NAMES)},
        "bias": round(final_bias, 8),
        "thresholds": DEFAULT_THRESHOLDS,
        "critical_axes": DEFAULT_CRITICAL_AXES,
        "threshold_status": "engineering_defaults_not_calibrated",
        "training": {
            "dataset": str(dataset_path), "sample_count": len(samples), "class_counts": counts,
            "folds_requested": k, "folds_used": len(fold_metrics), "cross_validation_mean": aggregate,
            "epochs": args.epochs, "learning_rate": args.learning_rate, "l2": args.l2,
            "min_coverage": args.min_coverage, "forced_small_sample": args.force_small_sample,
            "label_semantics": "由项目人工定义；不等于平台爆款真值或市场概率",
            "warning": "本命令只拟合权重与偏置，不校准高/中/低阈值。",
            "sources": sources,
        },
    }
    out = Path(args.output).resolve()
    write_json(out, output)
    print(f"拟合权重文件：{out}")
    if aggregate is None:
        print("交叉验证：未执行或不可执行；结果只能用于代码路径实验")
    else:
        print(
            f"交叉验证均值：accuracy={aggregate['accuracy']:.3f}, "
            f"balanced_accuracy={aggregate['balanced_accuracy']:.3f}, log_loss={aggregate['log_loss']:.3f}"
        )

def write_default_weights(args: argparse.Namespace) -> None:
    out = Path(args.output).resolve()
    write_json(
        out,
        {
            "version": VERSION,
            "created_at": utc_now(),
            "type": "engineering_initial_weights",
            "status": "uncalibrated",
            "weights": DEFAULT_WEIGHTS,
            "bias": DEFAULT_BIAS,
            "thresholds": DEFAULT_THRESHOLDS,
            "critical_axes": DEFAULT_CRITICAL_AXES,
            "warning": "人工工程初始值，未经项目样本训练，不是平台事实。",
        },
    )
    print(out)


def write_schema(args: argparse.Namespace) -> None:
    out = Path(args.output).resolve()
    write_json(out, extraction_schema())
    print(out)


def synthetic_task(input_type: str = "first_three", suffix: str = "A") -> dict[str, Any]:
    lines = [
        f"测试正文版本{suffix}。主角采取行动，局势发生变化，下一步承诺已经启动。",
        *[f"{name}真实证据句。" for name in AXIS_NAMES],
        *[f"{name}真实证据句。" for name in GATE_NAMES],
        "优先问题真实证据句。",
    ]
    text = "\n".join(lines)
    return make_task(
        input_path=Path(f"synthetic_{suffix}.txt"), text=text, input_type=input_type,
        metadata={"test": True, "revision": suffix}, truncated=False,
    )

def synthetic_extraction(task: dict[str, Any], score: int = 2) -> dict[str, Any]:
    data = extraction_template(task)
    data["extractor"] = {"name": "Codex-self-test", "run_note": "synthetic"}
    data["mainline"] = {
        "core_viewpoint": "测试主角", "current_goal": "解决问题", "current_obstacle": "测试阻力",
        "gained_or_lost": "获得测试收益", "situation_change": "局势发生变化",
        "next_commitment": "下一步承诺已经启动", "one_sentence_mainline": "测试主角采取行动并改变局势。",
        "readability_risk": "低", "missing_items": [],
    }
    for axis in data["axes"]:
        axis.update(
            {
                "evidence_sufficient": True, "score": score, "confidence": 100,
                "overload_risk": "低", "evidence": [f"{axis['axis']}真实证据句。"],
                "judgment": "自检判断", "root_issue": "", "related_axes": [], "evidence_gap": "",
            }
        )
    for gate in data["gates"]:
        gate.update(
            {
                "evidence_sufficient": True, "score": 3, "confidence": 100,
                "evidence": [f"{gate['gate']}真实证据句。"], "judgment": "自检判断", "evidence_gap": "",
            }
        )
    data["extraction_confidence"] = 100
    return data

def self_test(_: argparse.Namespace) -> None:
    task = validate_task(synthetic_task())
    extraction = validate_extraction(synthetic_extraction(task, score=2), task)
    weights = WeightSet(
        DEFAULT_WEIGHTS.copy(), DEFAULT_BIAS, DEFAULT_THRESHOLDS.copy(),
        tuple(DEFAULT_CRITICAL_AXES), "self-test", "uncalibrated"
    )
    neutral = compute_linear_result(extraction, weights)
    assert neutral["activation"] == 0.5
    assert neutral["raw_level"] == "中", "八维全部合格（2分）必须映射为中"
    assert neutral["coverage"] == 1.0
    assert "allowed_judgment" not in extraction and "forbidden_extrapolation" not in extraction

    high_extraction = validate_extraction(synthetic_extraction(task, score=4), task)
    high = compute_linear_result(high_extraction, weights)
    assert high["activation"] > 0.68 and high["raw_level"] == "高"

    overloaded_raw = synthetic_extraction(task, score=4)
    for axis in overloaded_raw["axes"]:
        axis["overload_risk"] = "高"
    overloaded = compute_linear_result(validate_extraction(overloaded_raw, task), weights)
    assert overloaded["final_level"] != "高", "多维高过载不得继续输出高"

    missing_extraction = synthetic_extraction(task, score=2)
    for axis in missing_extraction["axes"][:4]:
        axis.update({
            "evidence_sufficient": False, "score": None, "confidence": 20,
            "evidence": [], "judgment": "证据不足", "evidence_gap": "测试证据不足",
        })
    missing = compute_linear_result(validate_extraction(missing_extraction, task), weights)
    assert missing["coverage"] == 0.5 and missing["raw_level"] == "证据不足"

    critical_missing_raw = synthetic_extraction(task, score=3)
    for axis in critical_missing_raw["axes"]:
        if axis["axis"] == "章尾钩子轴":
            axis.update({
                "evidence_sufficient": False, "score": None, "confidence": 20,
                "evidence": [], "judgment": "证据不足", "evidence_gap": "章尾证据不足",
            })
    critical_missing = compute_linear_result(validate_extraction(critical_missing_raw, task), weights)
    assert critical_missing["coverage"] == 0.875
    assert critical_missing["raw_level"] == "证据不足"
    assert critical_missing["missing_critical_axes"] == ["章尾钩子轴"]

    weighted_weights = WeightSet(
        {name: (10.0 if name in {"因果代价轴", "章尾钩子轴"} else 0.1) for name in AXIS_NAMES},
        0.0,
        DEFAULT_THRESHOLDS.copy(),
        tuple(),
        "weighted-self-test",
        "uncalibrated",
    )
    weighted_missing_raw = synthetic_extraction(task, score=3)
    for axis in weighted_missing_raw["axes"]:
        if axis["axis"] in {"因果代价轴", "章尾钩子轴"}:
            axis.update({
                "evidence_sufficient": False, "score": None, "confidence": 20,
                "evidence": [], "judgment": "证据不足", "evidence_gap": "高权重轴证据不足",
            })
    weighted_missing = compute_linear_result(validate_extraction(weighted_missing_raw, task), weighted_weights)
    assert weighted_missing["coverage"] == 0.75
    assert weighted_missing["weighted_coverage"] < DEFAULT_THRESHOLDS["minimum_weighted_coverage"]
    assert weighted_missing["raw_level"] == "证据不足"

    duplicate_raw = synthetic_extraction(task, score=4)
    shared = task["text"].splitlines()[0]
    for axis in duplicate_raw["axes"][:3]:
        axis["evidence"] = [shared]
    try:
        validate_extraction(duplicate_raw, task)
    except ValueError:
        pass
    else:
        raise AssertionError("同一句证据不得重复支撑三个及以上高分维度")

    gate_fail = synthetic_extraction(task, score=4)
    for gate in gate_fail["gates"]:
        if gate["gate"] == "卖点识别门":
            gate["score"] = 1
    gated = compute_linear_result(validate_extraction(gate_fail, task), weights)
    assert gated["raw_level"] == "高" and gated["final_level"] == "低"

    no_evidence = synthetic_extraction(task, score=4)
    no_evidence["axes"][0]["evidence"] = []
    try:
        validate_extraction(no_evidence, task)
    except ValueError:
        pass
    else:
        raise AssertionError("有分无证据必须阻断")

    invented = synthetic_extraction(task, score=4)
    invented["axes"][0]["evidence"] = ["这句正文中不存在"]
    try:
        validate_extraction(invented, task)
    except ValueError:
        pass
    else:
        raise AssertionError("无法回溯正文的证据必须阻断")

    bad_mainline = synthetic_extraction(task, score=2)
    for key in (
        "core_viewpoint", "current_goal", "current_obstacle", "gained_or_lost",
        "situation_change", "next_commitment", "one_sentence_mainline",
    ):
        bad_mainline["mainline"][key] = ""
    bad_mainline["mainline"]["readability_risk"] = "低"
    try:
        validate_extraction(bad_mainline, task)
    except ValueError:
        pass
    else:
        raise AssertionError("主线全空却标低风险必须阻断")

    bad_hash = json.loads(json.dumps(extraction, ensure_ascii=False))
    bad_hash["source_sha256"] = "0" * 64
    try:
        validate_extraction(bad_hash, task)
    except ValueError:
        pass
    else:
        raise AssertionError("source_sha256 不一致必须阻断")

    report = {
        "run": {"version": VERSION, "rubric_version": RUBRIC_VERSION, "source_name": task["source"]["name"], "input_type": task["input_type"]},
        "extraction": extraction,
        "linear_result": neutral,
    }
    assert "本地脚本不调用 API" in render_markdown_report(report)
    print("SELF-TEST PASS")
    print(json.dumps({
        "neutral": neutral,
        "high": high,
        "overloaded": overloaded,
        "missing": missing,
        "critical_missing": critical_missing,
        "weighted_missing": weighted_missing,
        "gated": gated,
    }, ensure_ascii=False, indent=2))

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="八维伪线性探针：Codex 提取特征 + 本地无 API 线性计算",
    )
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="封装待审文本，生成 Codex 任务与提取模板")
    prepare.add_argument("--input", required=True, help="小说文本或 Markdown")
    prepare.add_argument("--input-type", choices=list(INPUT_TYPES), default="single_chapter")
    prepare.add_argument("--metadata", help="可选 JSON 元数据")
    prepare.add_argument("--output-dir", required=True)
    prepare.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    prepare.add_argument("--allow-truncate", action="store_true")
    prepare.set_defaults(func=prepare_task)

    score = sub.add_parser("score", help="读取 Codex 生成的 extraction.json 并本地计算")
    score.add_argument("--task", required=True)
    score.add_argument("--extraction", required=True)
    score.add_argument("--output", required=True)
    score.add_argument("--markdown", help="默认与 JSON 报告同名")
    score.add_argument("--weights", help="可选权重文件")
    score.set_defaults(func=score_files)

    batch = sub.add_parser("batch-score", help="批量计算含 task.json/extraction.json 的任务目录")
    batch.add_argument("--root", required=True)
    batch.add_argument("--output-dir", required=True)
    batch.add_argument("--task-name", default="task.json")
    batch.add_argument("--extraction-name", default="extraction.json")
    batch.add_argument("--weights")
    batch.set_defaults(func=batch_score)

    compare = sub.add_parser("compare", help="比较两份探针报告")
    compare.add_argument("--before", required=True)
    compare.add_argument("--after", required=True)
    compare.add_argument("--output", required=True)
    compare.add_argument("--relation", help="修订关系 JSON；正常比较必须提供")
    compare.add_argument("--force-unrelated", action="store_true", help="仅诊断：允许无修订关系比较")
    compare.add_argument("--force-incompatible", action="store_true")
    compare.set_defaults(func=compare_reports)

    fit = sub.add_parser("fit", help="使用人工标签报告集拟合权重与偏置（不校准阈值）")
    fit.add_argument("--dataset", required=True, help='JSONL：每行 {"report":"x.json","label":0|1}')
    fit.add_argument("--output", required=True)
    fit.add_argument("--epochs", type=int, default=3000)
    fit.add_argument("--learning-rate", type=float, default=0.05)
    fit.add_argument("--l2", type=float, default=0.05)
    fit.add_argument("--min-coverage", type=float, default=0.75)
    fit.add_argument("--seed", type=int, default=42)
    fit.add_argument("--force-small-sample", action="store_true")
    fit.set_defaults(func=fit_weights)

    defaults = sub.add_parser("write-default-weights", help="导出工程初始权重")
    defaults.add_argument("--output", required=True)
    defaults.set_defaults(func=write_default_weights)

    schema = sub.add_parser("write-schema", help="导出 extraction JSON Schema")
    schema.add_argument("--output", required=True)
    schema.set_defaults(func=write_schema)

    test = sub.add_parser("self-test", help="纯本地自检；不调用 API")
    test.set_defaults(func=self_test)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = args.func(args)
        return 0 if result is not False else 1
    except KeyboardInterrupt:
        print("已取消", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
