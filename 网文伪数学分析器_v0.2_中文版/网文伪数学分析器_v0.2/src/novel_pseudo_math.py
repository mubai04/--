#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

VERSION = "0.2.0"
ROOT = Path(__file__).resolve().parents[1]
WORKS_ROOT = (ROOT / "正文" / "作品").resolve()
REGISTRY_PATH = ROOT / "配置" / "metric_registry.json"
THRESHOLDS_PATH = ROOT / "配置" / "thresholds.json"
EXTRACTION_SCHEMA_PATH = ROOT / "schemas" / "extraction.schema.json"
WORK_SCHEMA_PATH = ROOT / "schemas" / "work_info.schema.json"
CHAPTER_RE = re.compile(r"^(\d{4})_.+\.(md|txt)$", re.IGNORECASE)
WORK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
GATES = ("G_C", "G_A", "G_L", "G_P")
PROFILE = ("U_ch", "C_ch", "A_ch", "E_ch", "R_ch", "F_ch")
CRITICAL_PROFILE = ("U_ch", "C_ch")
DATA_STATUSES = {"OK", "NA", "LOW_SAMPLE", "NOT_APPLICABLE", "INSUFFICIENT_DATA"}
GATE_STATUSES = {"PASS", "FAIL", "UNKNOWN"}
SCORE_STATUSES = {"OK", "NA", "LOW_SAMPLE", "NOT_APPLICABLE", "INSUFFICIENT_DATA"}
ANTI_GAMING_CODES = (
    "AG_SENSORY_STUFFING",
    "AG_RANDOM_REVERSAL",
    "AG_MEANINGLESS_CHOICE",
    "AG_SYMBOL_SPAM",
    "AG_RANDOM_RHYTHM",
    "AG_HARMFUL_OMISSION",
)
GATE_MIN_CHARS = {"G_C": 300, "G_A": 300, "G_L": 500, "G_P": 300}


class AnalyzerError(Exception):
    pass


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise AnalyzerError(f"文件不存在：{path}") from exc
    except json.JSONDecodeError as exc:
        raise AnalyzerError(f"JSON 格式错误：{path}: {exc}") from exc


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def clip(x: float, lo: float = 0.0, hi: float = 4.0) -> float:
    return max(lo, min(hi, x))


def q_ratio(p: float) -> float:
    if not is_finite_number(p):
        raise AnalyzerError(f"比例必须是有限数值：{p!r}")
    if not 0.0 <= float(p) <= 1.0:
        raise AnalyzerError(f"比例必须位于 0—1：{p}")
    return 4.0 * float(p)


def n_map(x: float, a: float, b: float) -> float:
    if not all(is_finite_number(v) for v in (x, a, b)):
        raise AnalyzerError("N(x;a,b) 的 x、a、b 必须是有限数值")
    x, a, b = float(x), float(a), float(b)
    if b <= a:
        raise AnalyzerError(f"N(x;a,b) 要求 b>a，实际 a={a}, b={b}")
    return clip(4.0 * (x - a) / (b - a))


def validate_schema(instance: Any, schema_path: Path, label: str) -> None:
    schema = read_json(schema_path)
    try:
        validator = Draft202012Validator(schema)
        validator.check_schema(schema)
    except SchemaError as exc:
        raise AnalyzerError(f"{label} 的 JSON Schema 自身非法：{exc.message}") from exc
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))
    if errors:
        details = []
        for err in errors[:12]:
            location = ".".join(str(x) for x in err.absolute_path) or "<root>"
            details.append(f"{location}: {err.message}")
        suffix = "" if len(errors) <= 12 else f"；另有 {len(errors) - 12} 项"
        raise AnalyzerError(f"{label} 未通过 Schema 校验：" + " | ".join(details) + suffix)


def safe_work_id(work_id: str) -> str:
    if not WORK_ID_RE.fullmatch(work_id):
        raise AnalyzerError("work_id 仅允许英文字母、数字、下划线和连字符，长度 1—64，且不得包含路径符号")
    return work_id


def ensure_within(child: Path, parent: Path, label: str) -> Path:
    resolved_child = child.resolve()
    resolved_parent = parent.resolve()
    if not resolved_child.is_relative_to(resolved_parent):
        raise AnalyzerError(f"{label} 越过允许目录：{resolved_child}")
    return resolved_child


def normalize_work_dir(work_dir: Path) -> Path:
    return ensure_within(work_dir, WORKS_ROOT, "作品目录")


def as_interval(value: Any) -> tuple[float, float] | None:
    if value is None:
        return None
    if is_finite_number(value):
        v = float(value)
        if not 0 <= v <= 4:
            raise AnalyzerError(f"评分超出 0—4：{v}")
        return (v, v)
    if isinstance(value, dict):
        status = value.get("status", "OK")
        if status not in SCORE_STATUSES:
            raise AnalyzerError(f"非法评分状态：{status}")
        if status in {"NA", "LOW_SAMPLE", "NOT_APPLICABLE", "INSUFFICIENT_DATA"}:
            return None
        lo = value.get("min", value.get("value"))
        hi = value.get("max", value.get("value"))
        if lo is None or hi is None:
            raise AnalyzerError(f"OK 评分必须提供 value 或 min/max：{value}")
        if not is_finite_number(lo) or not is_finite_number(hi):
            raise AnalyzerError(f"评分区间必须是有限数值：{value}")
        lo, hi = float(lo), float(hi)
        if not (0 <= lo <= hi <= 4):
            raise AnalyzerError(f"非法区间：{value}")
        return (lo, hi)
    raise AnalyzerError(f"不支持的评分格式：{value!r}")


def wa_interval(
    values: list[tuple[float, float] | None],
    weights: list[float],
    min_fraction: float = 0.5,
) -> tuple[float, float] | None:
    if len(values) != len(weights):
        raise AnalyzerError("WA 输入与权重数量不一致")
    if any(not is_finite_number(w) or float(w) <= 0 for w in weights):
        raise AnalyzerError("WA 权重必须为有限正数")
    available = [(v, float(w)) for v, w in zip(values, weights) if v is not None]
    required = math.ceil(len(values) * min_fraction)
    if not available or len(available) < required:
        return None
    sw = sum(w for _, w in available)
    if sw <= 0:
        raise AnalyzerError("WA 可用权重和必须大于 0")
    return (
        sum(v[0] * w for v, w in available) / sw,
        sum(v[1] * w for v, w in available) / sw,
    )


def chapter_files(work_dir: Path) -> list[Path]:
    work_dir = normalize_work_dir(work_dir)
    chapter_dir = work_dir / "当前版本" / "章节"
    if not chapter_dir.exists():
        raise AnalyzerError(f"章节目录不存在：{chapter_dir}")
    files = [p for p in chapter_dir.iterdir() if p.is_file() and p.suffix.lower() in {".md", ".txt"}]
    bad = [p.name for p in files if not CHAPTER_RE.match(p.name)]
    if bad:
        raise AnalyzerError("章节命名不合规：" + ", ".join(sorted(bad)))
    nums = [int(CHAPTER_RE.match(p.name).group(1)) for p in files]
    if len(nums) != len(set(nums)):
        raise AnalyzerError("存在重复章节编号")
    return sorted(files, key=lambda p: int(CHAPTER_RE.match(p.name).group(1)))


def validate_work(work_dir: Path) -> dict[str, Any]:
    work_dir = normalize_work_dir(work_dir)
    info = read_json(work_dir / "作品信息.json")
    validate_schema(info, WORK_SCHEMA_PATH, "作品信息")
    safe_work_id(info["work_id"])
    if work_dir.name != info["work_id"]:
        raise AnalyzerError("作品目录名必须与 work_id 完全一致")
    if info["chapter_directory"] != "当前版本/章节":
        raise AnalyzerError("chapter_directory 必须为 当前版本/章节")
    if info["encoding"].lower() != "utf-8":
        raise AnalyzerError("正文编码必须声明为 utf-8")
    files = chapter_files(work_dir)
    for p in files:
        try:
            p.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as exc:
            raise AnalyzerError(f"正文不是 UTF-8：{p}") from exc
    return {
        "work_id": info["work_id"],
        "title": info["title"],
        "chapter_count": len(files),
        "files": [p.name for p in files],
    }


def select_chapters(files: list[Path], scope: str, chapters: list[str] | None) -> list[Path]:
    by_num = {CHAPTER_RE.match(p.name).group(1): p for p in files}
    if scope == "full":
        if not files:
            raise AnalyzerError("整书范围没有正文文件")
        return files
    if not chapters:
        raise AnalyzerError("single/range 必须提供 --chapters")
    normalized = [str(c).zfill(4) for c in chapters]
    missing = [c for c in normalized if c not in by_num]
    if missing:
        raise AnalyzerError("找不到章节：" + ", ".join(missing))
    if scope == "single" and len(normalized) != 1:
        raise AnalyzerError("single 只能选择一个章节")
    ordered = sorted([by_num[c] for c in normalized], key=lambda p: int(CHAPTER_RE.match(p.name).group(1)))
    if scope == "range":
        nums = [int(CHAPTER_RE.match(p.name).group(1)) for p in ordered]
        if nums != list(range(nums[0], nums[-1] + 1)):
            raise AnalyzerError("range 必须是连续章节")
    return ordered


def cmd_init_work(args: argparse.Namespace) -> None:
    work_id = safe_work_id(args.work_id)
    work_dir = ensure_within(WORKS_ROOT / work_id, WORKS_ROOT, "新作品目录")
    if work_dir.exists() and any(work_dir.iterdir()):
        raise AnalyzerError(f"作品目录已存在：{work_dir}")
    (work_dir / "当前版本" / "章节").mkdir(parents=True, exist_ok=True)
    (work_dir / "历史版本").mkdir(parents=True, exist_ok=True)
    (work_dir / "分析范围").mkdir(parents=True, exist_ok=True)
    info = {
        "work_id": work_id,
        "title": args.title,
        "genre": args.genre,
        "platform": args.platform,
        "current_version": "v001",
        "chapter_directory": "当前版本/章节",
        "encoding": "utf-8",
        "chapter_order_rule": "filename_numeric_prefix",
        "calibration_group": "未校准",
    }
    validate_schema(info, WORK_SCHEMA_PATH, "作品信息")
    write_json(work_dir / "作品信息.json", info)
    print(work_dir)


def cmd_validate_work(args: argparse.Namespace) -> None:
    print(json.dumps(validate_work(Path(args.work_dir)), ensure_ascii=False, indent=2))


def cmd_prepare(args: argparse.Namespace) -> None:
    work_dir = normalize_work_dir(Path(args.work_dir))
    meta = validate_work(work_dir)
    files = select_chapters(chapter_files(work_dir), args.scope, args.chapters)
    parts: list[str] = []
    documents: list[dict[str, Any]] = []
    for p in files:
        text = p.read_text(encoding="utf-8-sig")
        parts.append(f"\n\n===== {p.name} =====\n\n{text}")
        documents.append({"file": p.name, "sha256": sha256_text(text), "chars": len(text), "text": text})
    combined = "".join(parts).lstrip()
    if args.max_chars and len(combined) > args.max_chars:
        raise AnalyzerError(
            f"所选正文 {len(combined)} 字符，超过上限 {args.max_chars}；禁止静默截断，请缩小范围"
        )
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    task_id = f"{meta['work_id']}-{args.scope}-{sha256_text(combined)[:12]}"
    task = {
        "task_id": task_id,
        "method_version": VERSION,
        "calibration_level": "C0",
        "work_id": meta["work_id"],
        "title": meta["title"],
        "scope_type": args.scope,
        "chapters": [CHAPTER_RE.match(p.name).group(1) for p in files],
        "source_files": [{k: d[k] for k in ("file", "sha256", "chars")} for d in documents],
        "documents": documents,
        "source_sha256": sha256_text(combined),
        "text_char_count": len(combined),
        "truncated": False,
        "text": combined,
    }
    write_json(out / "task.json", task)
    instructions = f"""# Codex 分析任务（方法版本 {VERSION}）

读取：

- `task.json`
- 项目根目录 `schemas/extraction.schema.json`
- 项目根目录 `文档/编码手册_v0.2.md`
- 项目根目录 `配置/metric_registry.json`
- 项目根目录 `文档/反刷分协议.md`

生成当前目录下的 `extraction.json`。

硬规则：

1. 不修改 `task_id` 与 `source_sha256`；
2. 每条证据必须填写 `file`、`quote`、`start`、`end`，并与对应章节原文逐字一致；
3. 无证据时输出 `UNKNOWN`、`NA` 或其他缺失状态，不得猜测；
4. 事实指标保留合法的分子、分母、样本量；分子不得为负，不得大于分母；
5. 人工评分使用 0—4 区间并说明判断；
6. 同一根病灶使用同一 `finding_id`，禁止重复处罚；
7. 同一引文默认最多支持两个主判断；确需复用必须写 `reuse_justification`，且最多四项；
8. 完成六项反刷分检查；
9. 不输出作者身份概率、商业成功率、平台留存率或版权结论；
10. 写完后先运行本地 `score`，Schema 或证据校验失败必须修正。
"""
    (out / "CODEX_TASK.md").write_text(instructions, encoding="utf-8")
    print(out)


def document_map(task: dict[str, Any]) -> dict[str, str]:
    docs = task.get("documents")
    if not isinstance(docs, list) or not docs:
        raise AnalyzerError("task.json 缺少 documents，不能验证证据文件与位置")
    mapping: dict[str, str] = {}
    for doc in docs:
        file = doc.get("file")
        text = doc.get("text")
        if not isinstance(file, str) or not file or file in mapping:
            raise AnalyzerError(f"task.documents 文件名非法或重复：{file!r}")
        if not isinstance(text, str):
            raise AnalyzerError(f"task.documents[{file}] 缺少正文")
        if sha256_text(text) != doc.get("sha256"):
            raise AnalyzerError(f"task.documents[{file}] SHA-256 不一致")
        mapping[file] = text
    return mapping


def evidence_fingerprint(item: dict[str, Any]) -> tuple[str, int, int, str]:
    return (str(item["file"]), int(item["start"]), int(item["end"]), str(item["quote"]))


def validate_evidence_item(item: dict[str, Any], docs: dict[str, str], field: str, index: int) -> None:
    file = item.get("file")
    quote = item.get("quote")
    start = item.get("start")
    end = item.get("end")
    if file not in docs:
        raise AnalyzerError(f"{field}[{index}] 证据文件不存在于任务范围：{file}")
    if not isinstance(quote, str) or len(quote.strip()) < 8:
        raise AnalyzerError(f"{field}[{index}] 引文过短，至少 8 个非空字符")
    if not isinstance(start, int) or not isinstance(end, int):
        raise AnalyzerError(f"{field}[{index}] start/end 必须为整数")
    text = docs[file]
    if start < 0 or end <= start or end > len(text):
        raise AnalyzerError(f"{field}[{index}] 证据位置越界：{start}:{end}")
    if text[start:end] != quote:
        raise AnalyzerError(f"{field}[{index}] 引文与指定位置不一致")


def validate_evidence_list(
    evidence: list[dict[str, Any]],
    docs: dict[str, str],
    field: str,
    require: bool = False,
) -> None:
    if require and not evidence:
        raise AnalyzerError(f"{field} 缺少证据")
    for i, item in enumerate(evidence):
        validate_evidence_item(item, docs, field, i)


def iter_evidence(ext: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    for code, item in ext.get("gates", {}).items():
        for ev in item.get("evidence", []):
            yield f"gates.{code}", ev
    for group in ("chapter_profile", "manual_scores", "facts"):
        for code, item in ext.get(group, {}).items():
            if isinstance(item, dict):
                for ev in item.get("evidence", []):
                    yield f"{group}.{code}", ev
    for i, finding in enumerate(ext.get("findings", [])):
        for ev in finding.get("evidence", []):
            yield f"findings[{i}]", ev
    for code, item in ext.get("anti_gaming", {}).items():
        for ev in item.get("evidence", []):
            yield f"anti_gaming.{code}", ev


def validate_evidence_reuse(ext: dict[str, Any]) -> None:
    uses: dict[tuple[str, int, int, str], list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    for owner, ev in iter_evidence(ext):
        uses[evidence_fingerprint(ev)].append((owner, ev))
    for fingerprint, rows in uses.items():
        if len(rows) <= 2:
            continue
        justifications = [str(ev.get("reuse_justification", "")).strip() for _, ev in rows]
        if len(rows) > 4:
            raise AnalyzerError(f"同一证据被复用 {len(rows)} 次，超过绝对上限 4：{fingerprint[0]}:{fingerprint[1]}-{fingerprint[2]}")
        if any(not j for j in justifications):
            owners = ", ".join(owner for owner, _ in rows)
            raise AnalyzerError(f"同一证据被三个以上主判断复用但未全部说明理由：{owners}")


def validate_gate_applicability(task: dict[str, Any], code: str, item: dict[str, Any]) -> None:
    status = item["status"]
    chars = int(task.get("text_char_count", 0))
    if status == "PASS" and chars < GATE_MIN_CHARS[code]:
        raise AnalyzerError(
            f"{code} 在仅 {chars} 字符的材料上不得判 PASS；少于 {GATE_MIN_CHARS[code]} 字符时应为 UNKNOWN"
        )
    if code == "G_L" and status == "PASS" and task.get("scope_type") == "single" and chars < 800:
        raise AnalyzerError("单章少于 800 字时，连续性闸门 G_L 不得判 PASS")


def gate_summary(
    task: dict[str, Any],
    gates: dict[str, Any],
    docs: dict[str, str],
) -> tuple[str, dict[str, Any]]:
    normalized: dict[str, Any] = {}
    statuses: list[str] = []
    for code in GATES:
        item = gates.get(code)
        if not isinstance(item, dict):
            raise AnalyzerError(f"缺少闸门 {code}")
        status = item.get("status")
        if status not in GATE_STATUSES:
            raise AnalyzerError(f"{code} 状态非法：{status}")
        validate_gate_applicability(task, code, item)
        validate_evidence_list(item.get("evidence", []), docs, f"gates.{code}", require=(status in {"PASS", "FAIL"}))
        if not str(item.get("judgment", "")).strip():
            raise AnalyzerError(f"{code} 缺少 judgment")
        normalized[code] = item
        statuses.append(status)
    if "FAIL" in statuses:
        return "BLOCKED", normalized
    if "UNKNOWN" in statuses:
        return "NEEDS_REVIEW", normalized
    return "PASSED", normalized


def validate_fact(code: str, fact: dict[str, Any], spec: dict[str, Any], docs: dict[str, str]) -> None:
    status = fact.get("status", "OK")
    if status not in DATA_STATUSES:
        raise AnalyzerError(f"facts.{code} 状态非法：{status}")
    for key in ("numerator", "denominator", "sample_size", "value"):
        if key in fact and fact[key] is not None:
            if not is_finite_number(fact[key]):
                raise AnalyzerError(f"facts.{code}.{key} 必须为有限数值")
            if float(fact[key]) < 0:
                raise AnalyzerError(f"facts.{code}.{key} 不得为负数")
    if "sample_size" in fact and fact["sample_size"] is not None and int(fact["sample_size"]) != float(fact["sample_size"]):
        raise AnalyzerError(f"facts.{code}.sample_size 必须为整数")
    mapping = spec["mapping"]
    if status == "OK":
        if mapping in {"Q", "ONE_MINUS_Q"}:
            num, den = fact.get("numerator"), fact.get("denominator")
            if num is None or den is None:
                raise AnalyzerError(f"facts.{code} 的 {mapping} 映射必须提供 numerator/denominator")
            if float(den) <= 0:
                raise AnalyzerError(f"facts.{code}.denominator 必须大于 0")
            if float(num) > float(den):
                raise AnalyzerError(f"facts.{code}.numerator 不得大于 denominator")
        elif mapping == "N":
            if fact.get("value") is None:
                raise AnalyzerError(f"facts.{code} 的 N 映射必须提供 value")
        elif mapping == "DIRECT":
            as_interval(fact)
        else:
            raise AnalyzerError(f"facts.{code} 使用未知 mapping：{mapping}")
        validate_evidence_list(fact.get("evidence", []), docs, f"facts.{code}", require=True)
    else:
        if status in {"NA", "NOT_APPLICABLE", "INSUFFICIENT_DATA", "LOW_SAMPLE"} and not str(fact.get("judgment", "")).strip():
            raise AnalyzerError(f"facts.{code} 为 {status} 时必须说明 judgment")


def fact_to_interval(fact: dict[str, Any], spec: dict[str, Any]) -> tuple[float, float] | None:
    status = fact.get("status", "OK")
    if status in {"NA", "NOT_APPLICABLE", "INSUFFICIENT_DATA", "LOW_SAMPLE"}:
        return None
    sample = fact.get("sample_size")
    if sample is None:
        sample = fact.get("denominator", 0)
    min_sample = int(spec.get("min_sample", 1))
    if float(sample or 0) < min_sample:
        return None
    mapping = spec["mapping"]
    if mapping in {"Q", "ONE_MINUS_Q"}:
        den = float(fact["denominator"])
        num = float(fact["numerator"])
        p = num / den
        v = q_ratio(1 - p if mapping == "ONE_MINUS_Q" else p)
        return (v, v)
    if mapping == "DIRECT":
        return as_interval(fact)
    if mapping == "N":
        a, b = spec.get("a"), spec.get("b")
        if a is None or b is None:
            return None
        v = n_map(float(fact["value"]), float(a), float(b))
        return (v, v)
    raise AnalyzerError(f"未知 mapping：{mapping}")


def risk_action(value: float | None, thresholds: dict[str, Any]) -> dict[str, str]:
    if value is None:
        return {"status": "INSUFFICIENT_DATA", "action": "补充样本或人工复核"}
    if not 0 <= value <= 4:
        raise AnalyzerError(f"风险中心值超出 0—4：{value}")
    for row in thresholds["risk_actions"]:
        lower = float(row["min_inclusive"])
        upper = float(row["max_exclusive"])
        if lower <= value < upper or (value == 4.0 and upper == 4.0000001):
            return {"status": row["status"], "action": row["action"]}
    raise AnalyzerError(f"风险阈值未覆盖数值：{value}")


def validate_scored_group(
    group_name: str,
    group: dict[str, Any],
    docs: dict[str, str],
    required_keys: Iterable[str] | None = None,
) -> dict[str, tuple[float, float] | None]:
    if required_keys is not None:
        missing = sorted(set(required_keys) - set(group))
        if missing:
            raise AnalyzerError(f"{group_name} 缺少字段：{', '.join(missing)}")
    result: dict[str, tuple[float, float] | None] = {}
    for key, item in group.items():
        if not isinstance(item, dict):
            raise AnalyzerError(f"{group_name}.{key} 必须是对象")
        interval = as_interval(item)
        require = interval is not None
        validate_evidence_list(item.get("evidence", []), docs, f"{group_name}.{key}", require=require)
        if require and not str(item.get("judgment", "")).strip():
            raise AnalyzerError(f"{group_name}.{key} 有评分时必须填写 judgment")
        result[key] = interval
    return result


def validate_findings(findings: list[dict[str, Any]], docs: dict[str, str]) -> None:
    seen: set[str] = set()
    for i, finding in enumerate(findings):
        fid = finding.get("finding_id")
        if not isinstance(fid, str) or not fid.strip() or fid in seen:
            raise AnalyzerError(f"finding_id 缺失或重复：{fid}")
        seen.add(fid)
        validate_evidence_list(finding.get("evidence", []), docs, f"findings[{i}]", require=True)
        if not str(finding.get("judgment", "")).strip():
            raise AnalyzerError(f"findings[{i}] 缺少 judgment")
        if not str(finding.get("repair_action", "")).strip():
            raise AnalyzerError(f"findings[{i}] 缺少 repair_action")


def validate_anti_gaming(
    anti: dict[str, Any],
    docs: dict[str, str],
) -> dict[str, Any]:
    if set(anti) != set(ANTI_GAMING_CODES):
        missing = sorted(set(ANTI_GAMING_CODES) - set(anti))
        extra = sorted(set(anti) - set(ANTI_GAMING_CODES))
        raise AnalyzerError(f"反刷分检查不完整；缺少={missing}，多余={extra}")
    for code, item in anti.items():
        status = item.get("status")
        if status not in {"PASS", "FAIL", "UNKNOWN"}:
            raise AnalyzerError(f"anti_gaming.{code} 状态非法：{status}")
        validate_evidence_list(item.get("evidence", []), docs, f"anti_gaming.{code}", require=(status == "FAIL"))
        if not str(item.get("judgment", "")).strip():
            raise AnalyzerError(f"anti_gaming.{code} 缺少 judgment")
    return anti


def interval_center(iv: tuple[float, float] | None) -> float | None:
    return None if iv is None else (iv[0] + iv[1]) / 2


def weighted_center(values: list[tuple[float, float] | None], weights: list[float]) -> float | None:
    iv = wa_interval(values, weights)
    return interval_center(iv)


def module_stability(
    values: list[tuple[float, float] | None],
    base_weights: list[float],
    thresholds: dict[str, Any],
    trials: int,
    perturbation: float,
    seed: int,
) -> dict[str, Any] | None:
    available = [(v, float(w)) for v, w in zip(values, base_weights) if v is not None]
    if len(available) < math.ceil(len(values) * 0.5):
        return None
    centers = [interval_center(v) for v, _ in available]
    weights = [w for _, w in available]
    base_value = sum(c * w for c, w in zip(centers, weights)) / sum(weights)
    base_status = risk_action(base_value, thresholds)["status"]
    rng = random.Random(seed)
    same = 0
    statuses: Counter[str] = Counter()
    for _ in range(trials):
        perturbed = [w * rng.uniform(1 - perturbation, 1 + perturbation) for w in weights]
        value = sum(c * w for c, w in zip(centers, perturbed)) / sum(perturbed)
        status = risk_action(value, thresholds)["status"]
        statuses[status] += 1
        if status == base_status:
            same += 1
    return {
        "baseline_status": base_status,
        "stability": round(same / trials, 4),
        "trials": trials,
        "perturbation": perturbation,
        "status_distribution": dict(sorted(statuses.items())),
    }


def derive_decision_state(
    gate_state: str,
    profile: dict[str, tuple[float, float] | None],
    s_ch: tuple[float, float] | None,
    risks: dict[str, dict[str, Any]],
    anti_gaming: dict[str, Any],
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if gate_state == "BLOCKED":
        return "BLOCKED", ["至少一个硬闸门失败"]
    if gate_state == "NEEDS_REVIEW":
        return "NEEDS_REVIEW", ["至少一个硬闸门为 UNKNOWN"]
    if s_ch is None or any(profile.get(k) is None for k in PROFILE):
        return "NEEDS_REVIEW", ["六维章级能力数据不足"]
    for code in CRITICAL_PROFILE:
        iv = profile[code]
        if iv is not None and iv[1] <= 1.0:
            reasons.append(f"{code} 上限不超过 1")
    if reasons:
        return "BLOCKED", reasons
    if any(item.get("status") == "UNKNOWN" for item in anti_gaming.values()):
        reasons.append("反刷分检查存在 UNKNOWN")
    anti_fail = [code for code, item in anti_gaming.items() if item.get("status") == "FAIL"]
    if anti_fail:
        reasons.append("反刷分检查失败：" + ", ".join(anti_fail))
    risk_centers = [row["center"] for row in risks.values() if row["center"] is not None]
    if s_ch[1] < 2.5 or any(v >= 3.0 for v in risk_centers):
        if s_ch[1] < 2.5:
            reasons.append("S_ch 上限低于 2.5")
        if any(v >= 3.0 for v in risk_centers):
            reasons.append("至少一个风险维度达到 3.0")
        return "REWRITE", reasons
    if anti_fail:
        return "TARGETED_REPAIR", reasons
    profile_floor_ok = all(profile[k][0] >= 2.0 for k in PROFILE if profile[k] is not None)
    all_risk_low = all(v < 2.0 for v in risk_centers) if risk_centers else False
    if s_ch[0] >= 2.8 and profile_floor_ok and all_risk_low and not reasons:
        return "ROBUST_PASS", ["硬闸门全过、六维下限达标、九维风险均低于 2.0"]
    if s_ch[0] < 2.8:
        reasons.append("S_ch 下限低于 2.8")
    if not profile_floor_ok:
        reasons.append("至少一个章级能力维度下限低于 2")
    if any(v >= 2.0 for v in risk_centers):
        reasons.append("至少一个风险维度达到 2.0")
    return "TARGETED_REPAIR", reasons or ["未满足稳健通过条件"]


def score_task(task_path: Path, extraction_path: Path, output_dir: Path) -> dict[str, Any]:
    task = read_json(task_path)
    ext = read_json(extraction_path)
    validate_schema(ext, EXTRACTION_SCHEMA_PATH, "extraction.json")
    reg = read_json(REGISTRY_PATH)
    th = read_json(THRESHOLDS_PATH)
    if ext.get("task_id") != task.get("task_id"):
        raise AnalyzerError("task_id 不一致")
    if ext.get("source_sha256") != task.get("source_sha256"):
        raise AnalyzerError("source_sha256 不一致")
    if task.get("method_version") != VERSION:
        raise AnalyzerError(f"任务方法版本为 {task.get('method_version')}，当前脚本为 {VERSION}")
    if task.get("truncated"):
        raise AnalyzerError("任务标记为截断，禁止正式评分")
    docs = document_map(task)
    gate_state, gates = gate_summary(task, ext["gates"], docs)
    profile = validate_scored_group("chapter_profile", ext["chapter_profile"], docs, PROFILE)
    manual = validate_scored_group("manual_scores", ext["manual_scores"], docs, reg["manual_scores"])
    facts = ext["facts"]
    unknown_fact_codes = sorted(set(facts) - {spec["source"] for spec in reg["metrics"].values()})
    if unknown_fact_codes:
        raise AnalyzerError("facts 包含未登记指标：" + ", ".join(unknown_fact_codes))
    for metric_name, spec in reg["metrics"].items():
        source_code = spec["source"]
        if source_code in facts:
            validate_fact(source_code, facts[source_code], spec, docs)
    validate_findings(ext["findings"], docs)
    anti_gaming = validate_anti_gaming(ext["anti_gaming"], docs)
    validate_evidence_reuse(ext)

    vals: dict[str, tuple[float, float] | None] = {}
    for name, spec in reg["metrics"].items():
        vals[name] = fact_to_interval(facts[spec["source"]], spec) if spec["source"] in facts else None

    c_o = wa_interval([manual.get("Ca_causal"), manual.get("Cg_goal"), manual.get("Cs_state")], [1, 1, 1])
    v_a = wa_interval(
        [manual.get("Ve_salience"), manual.get("Vu_reframe"), manual.get("Vb_branch"), manual.get("Vr_rhythm")],
        [1, 1, 1, 1],
    )
    vals["P_s"] = (
        (c_o[0] * (4 - v_a[1]) / 4, c_o[1] * (4 - v_a[0]) / 4) if c_o and v_a else None
    )
    vals["E_flat"] = wa_interval(
        [manual.get("ES_same"), manual.get("EI_lowvar"), manual.get("ER_repeat"), manual.get("EA_mismatch")],
        [0.30, 0.25, 0.25, 0.20],
    )
    ai_r = wa_interval([vals.get("Tr4"), manual.get("Sh_syntax"), vals.get("Ct4")], [1, 1, 1])
    ai_s = wa_interval([vals.get("Ex4"), vals.get("Ga4"), vals.get("Sr4")], [1, 1, 1])
    literature = [manual.get(k) for k in ("Lv_voice", "Li_sensory", "Lm_layers", "Lr_rhythm", "Lp_pov", "Lo_original")]
    l_floor = (
        (min(v[0] for v in literature), min(v[1] for v in literature)) if all(v is not None for v in literature) else None
    )
    vals["R_language"] = (
        (
            0.35 * ai_r[0] + 0.35 * ai_s[0] + 0.30 * (4 - l_floor[1]),
            0.35 * ai_r[1] + 0.35 * ai_s[1] + 0.30 * (4 - l_floor[0]),
        )
        if ai_r and ai_s and l_floor
        else None
    )

    modules: dict[str, tuple[float, float] | None] = {}
    stability: dict[str, Any] = {}
    st_cfg = th["stability"]
    for name, spec in reg["modules"].items():
        inputs = [vals.get(k) for k in spec["inputs"]]
        modules[name] = wa_interval(inputs, spec["weights"])
        stability[name] = module_stability(
            inputs,
            spec["weights"],
            th,
            int(st_cfg["trials"]),
            float(st_cfg["weight_perturbation"]),
            int(st_cfg["seed"]) + sum(ord(c) for c in name),
        )
    modules["R_language"] = vals["R_language"]
    stability["R_language"] = None

    s_ch = wa_interval([profile[k] for k in PROFILE], [0.15, 0.20, 0.15, 0.15, 0.20, 0.15], min_fraction=1.0)

    a_pos = wa_interval(
        [ai_r, ai_s, modules.get("R_convergence"), vals.get("P_s"), modules.get("R_ambiguity"), modules.get("R_embodiment")],
        [0.28, 0.28, 0.16, 0.10, 0.10, 0.08],
        min_fraction=1.0,
    )
    h_neg = wa_interval(
        [manual.get("H_long"), manual.get("H_voice"), manual.get("H_asym")],
        [0.40, 0.30, 0.30],
        min_fraction=1.0,
    )
    ai_style = None
    if a_pos and h_neg:
        center = 100 / (
            1
            + math.exp(
                -float(th["ai_style"]["slope"])
                * (interval_center(a_pos) - interval_center(h_neg) - float(th["ai_style"]["center"]))
            )
        )
        n = int(task.get("text_char_count", len(task.get("text", ""))))
        short = max(0, 1 - n / 3000)
        ctx = ext.get("context", {})
        width = max(
            12,
            min(
                35,
                12
                + 12 * float(ctx.get("rater_disagreement", 0))
                + 10 * short
                + 8 * int(ctx.get("baseline_missing", 1))
                + 8 * int(ctx.get("mixed_edit", 0)),
            ),
        )
        ai_style = {
            "index": round(center, 3),
            "interval": [round(max(0, center - width), 3), round(min(100, center + width), 3)],
            "status": "OBSERVE_ONLY" if n < int(th["ai_style"]["min_chars_observe"]) else "INTERNAL_TREND",
            "interpretation": "AI式文本迹象指数，不是作者身份概率",
        }

    risks: dict[str, dict[str, Any]] = {}
    for name, iv in modules.items():
        center = interval_center(iv)
        risks[name] = {
            "interval": None if iv is None else [round(iv[0], 4), round(iv[1], 4)],
            "center": None if center is None else round(center, 4),
            **risk_action(center, th),
            "stability": stability.get(name),
        }

    decision_state, decision_reasons = derive_decision_state(gate_state, profile, s_ch, risks, anti_gaming)
    result = {
        "project": "网文伪数学分析器",
        "version": VERSION,
        "calibration_level": "C0",
        "task": {
            "task_id": task["task_id"],
            "work_id": task["work_id"],
            "scope_type": task["scope_type"],
            "chapters": task["chapters"],
            "source_sha256": task["source_sha256"],
            "text_char_count": task["text_char_count"],
        },
        "decision": {"state": decision_state, "reasons": decision_reasons},
        "gate_state": gate_state,
        "gates": gates,
        "chapter_profile": {
            "S_ch_interval": None if s_ch is None else [round(s_ch[0], 4), round(s_ch[1], 4)],
            "dimensions": {
                k: None if profile[k] is None else [round(profile[k][0], 4), round(profile[k][1], 4)]
                for k in PROFILE
            },
        },
        "risk_vector": risks,
        "ai_style_index": ai_style,
        "anti_gaming": anti_gaming,
        "findings": ext["findings"],
        "boundaries": [
            "风险值不是客观文学质量",
            "AI_STYLE_INDEX不是作者身份概率",
            "C0结果不得用于跨作者排名或商业成功预测",
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "analysis.json", result)
    lines = [
        "# 网文伪数学分析报告",
        "",
        f"- 任务：`{task['task_id']}`",
        f"- 范围：{task['scope_type']} / {', '.join(task['chapters'])}",
        f"- 最终状态：**{decision_state}**",
        f"- 硬闸门：**{gate_state}**",
        f"- 校准等级：C0",
        "",
        "## 决策理由",
    ]
    lines.extend(f"- {reason}" for reason in decision_reasons)
    lines += ["", "## 九维风险"]
    for name, row in risks.items():
        lines.append(
            f"- {name}: {row['center'] if row['center'] is not None else 'NA'} / {row['status']} / {row['action']}"
        )
    if ai_style:
        lines += [
            "",
            "## AI 式文本迹象",
            f"- 指数：{ai_style['index']}，区间 {ai_style['interval']}",
            "- 仅用于内部版本趋势，不是作者身份概率。",
        ]
    (output_dir / "analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def cmd_score(args: argparse.Namespace) -> None:
    result = score_task(Path(args.task), Path(args.extraction), Path(args.output))
    print(json.dumps({"output": str(Path(args.output)), "decision": result["decision"]["state"]}, ensure_ascii=False))


def cmd_batch_score(args: argparse.Namespace) -> None:
    root = Path(args.tasks_dir)
    if not root.exists():
        raise AnalyzerError(f"任务目录不存在：{root}")
    success = 0
    failures: list[dict[str, str]] = []
    for task_path in sorted(root.rglob("task.json")):
        task_dir = task_path.parent
        extraction = task_dir / "extraction.json"
        rel = task_dir.relative_to(root)
        out = Path(args.output_dir) / rel
        if not extraction.exists():
            failures.append({"task": str(task_path), "error": "缺少 extraction.json"})
            continue
        try:
            score_task(task_path, extraction, out)
            success += 1
        except AnalyzerError as exc:
            failures.append({"task": str(task_path), "error": str(exc)})
    summary = {"success": success, "failed": len(failures), "failures": failures}
    write_json(Path(args.output_dir) / "batch_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if failures:
        raise AnalyzerError(f"批处理存在 {len(failures)} 个失败任务")


def cmd_compare(args: argparse.Namespace) -> None:
    before = read_json(Path(args.before))
    after = read_json(Path(args.after))
    for report, label in ((before, "before"), (after, "after")):
        if report.get("project") != "网文伪数学分析器":
            raise AnalyzerError(f"{label} 不是本网文伪数学分析器报告")
    bt, at = before["task"], after["task"]
    if bt["work_id"] != at["work_id"]:
        raise AnalyzerError("比较报告必须属于同一 work_id")
    if bt["scope_type"] != at["scope_type"] or bt["chapters"] != at["chapters"]:
        raise AnalyzerError("比较报告必须使用相同 scope_type 和章节范围")
    if bt["source_sha256"] == at["source_sha256"]:
        raise AnalyzerError("修改前后正文 SHA-256 相同，不能解释为版本变化")
    if before.get("version") != after.get("version"):
        raise AnalyzerError("比较报告必须由同一方法版本生成")
    risk_delta: dict[str, Any] = {}
    for key in sorted(set(before["risk_vector"]) | set(after["risk_vector"])):
        b = before["risk_vector"].get(key, {}).get("center")
        a = after["risk_vector"].get(key, {}).get("center")
        risk_delta[key] = None if b is None or a is None else round(a - b, 4)
    profile_delta: dict[str, Any] = {}
    for key in PROFILE:
        b = before["chapter_profile"]["dimensions"].get(key)
        a = after["chapter_profile"]["dimensions"].get(key)
        profile_delta[key] = None if b is None or a is None else round(((a[0] + a[1]) - (b[0] + b[1])) / 2, 4)
    result = {
        "project": "网文伪数学分析器",
        "version": VERSION,
        "work_id": bt["work_id"],
        "scope_type": bt["scope_type"],
        "chapters": bt["chapters"],
        "before_sha256": bt["source_sha256"],
        "after_sha256": at["source_sha256"],
        "before_decision": before["decision"]["state"],
        "after_decision": after["decision"]["state"],
        "risk_delta": risk_delta,
        "chapter_profile_delta": profile_delta,
        "interpretation": "风险负值表示风险下降；章级能力正值表示能力提高。C0 仅供同范围版本比较。",
    }
    out = Path(args.output)
    write_json(out, result)
    print(out)


def self_test() -> None:
    assert q_ratio(0.0) == 0.0 and q_ratio(0.5) == 2.0 and q_ratio(1.0) == 4.0
    try:
        q_ratio(-0.1)
        raise AssertionError("negative ratio should fail")
    except AnalyzerError:
        pass
    assert n_map(5, 0, 10) == 2
    assert wa_interval([(0, 0), None, (4, 4)], [1, 1, 1]) == (2, 2)
    c, v = (2, 3), (1, 2)
    p = (c[0] * (4 - v[1]) / 4, c[1] * (4 - v[0]) / 4)
    assert p == (1.0, 2.25)
    assert risk_action(0.95, read_json(THRESHOLDS_PATH))["status"] == "PASS"
    assert risk_action(1.95, read_json(THRESHOLDS_PATH))["status"] == "OBSERVE"
    assert risk_action(2.95, read_json(THRESHOLDS_PATH))["status"] == "TARGETED_REPAIR"
    tmp = ROOT / "tests" / "_bom.json"
    tmp.write_text('\ufeff{"x":1}', encoding="utf-8")
    assert read_json(tmp)["x"] == 1
    tmp.unlink()
    print("SELF-TEST PASS")


def main() -> int:
    parser = argparse.ArgumentParser(description="网文伪数学分析器（本地无 API）")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("self-test")
    p.set_defaults(func=lambda _: self_test())
    p = sub.add_parser("init-work")
    p.add_argument("--work-id", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--genre", default="未设置")
    p.add_argument("--platform", default="未设置")
    p.set_defaults(func=cmd_init_work)
    p = sub.add_parser("validate-work")
    p.add_argument("--work-dir", required=True)
    p.set_defaults(func=cmd_validate_work)
    p = sub.add_parser("prepare")
    p.add_argument("--work-dir", required=True)
    p.add_argument("--scope", choices=["single", "range", "full"], required=True)
    p.add_argument("--chapters", nargs="*")
    p.add_argument("--output", required=True)
    p.add_argument("--max-chars", type=int, default=0)
    p.set_defaults(func=cmd_prepare)
    p = sub.add_parser("score")
    p.add_argument("--task", required=True)
    p.add_argument("--extraction", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_score)
    p = sub.add_parser("batch-score")
    p.add_argument("--tasks-dir", required=True)
    p.add_argument("--output-dir", required=True)
    p.set_defaults(func=cmd_batch_score)
    p = sub.add_parser("compare")
    p.add_argument("--before", required=True)
    p.add_argument("--after", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_compare)
    args = parser.parse_args()
    try:
        args.func(args)
    except AnalyzerError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
