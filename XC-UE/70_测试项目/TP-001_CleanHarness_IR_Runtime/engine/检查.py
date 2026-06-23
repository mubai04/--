from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable


def nonspace_len(text: str) -> int:
    return len(re.findall(r"\S", text))


def has_any(text: str, terms: Iterable[str]) -> bool:
    return any(term in text for term in terms)


def has_all(text: str, terms: Iterable[str]) -> bool:
    return all(term in text for term in terms)


def status_from_bool(value: bool) -> str:
    return "pass" if value else "fail"


def match_terms(text: str, terms: list[str], mode: str) -> bool:
    if mode == "all":
        return has_all(text, terms)
    if mode == "any":
        return has_any(text, terms)
    raise ValueError(f"Unsupported rule mode: {mode}")


def run_checks(sources: dict[str, str], candidate_path: Path, rules: dict[str, object], root: Path, check_type) -> list:
    checks: list = []
    candidate = sources["candidate"]
    all_ir = "\n".join(sources[name] for name in sources if name.startswith("ir"))

    checks.append(check_type(
        "ENGINE",
        "candidate_exists",
        status_from_bool(candidate_path.exists()),
        str(candidate_path.relative_to(root)),
    ))
    checks.append(check_type(
        "ENGINE",
        "formal_ch01_not_overwritten",
        status_from_bool("在这里写第一章正文。" in sources["formal_ch01"]),
        "formal chapters/ch01.md still contains placeholder text",
    ))
    checks.append(check_type(
        "ENGINE",
        "images_not_truth_source",
        status_from_bool("图片" in sources["manifest"] and "不是真源" in sources["manifest"]),
        "MANIFEST states image assets are expression layer, not truth source",
    ))

    for term in rules["ir_terms"]:
        checks.append(check_type("IR", f"contains_{term}", status_from_bool(term in all_ir), f"term={term}"))

    count = nonspace_len(candidate)
    length_rule = rules["candidate_length"]
    min_len = int(length_rule["min_nonspace_chars"])
    max_len = int(length_rule["max_nonspace_chars"])
    length_ok = min_len <= count <= max_len
    checks.append(check_type(
        str(length_rule["gate"]),
        str(length_rule["name"]),
        status_from_bool(length_ok),
        f"nonspace_chars={count}; expected={min_len}..{max_len}",
        "error" if not length_ok else "info",
    ))

    for rule in rules["text_gates"]:
        terms = list(rule["terms"])
        mode = str(rule.get("mode", "any"))
        ok = match_terms(candidate, terms, mode)
        evidence = f"mode={mode}; terms=" + " / ".join(terms)
        checks.append(check_type(str(rule["gate"]), str(rule["name"]), status_from_bool(ok), evidence, "error" if not ok else "info"))

    forbidden = {
        "legacy_as_input": "_legacy_root_inputs",
        "auto_merge_formal": "自动覆盖 `chapters/ch01.md`",
    }
    checks.append(check_type(
        "BOUNDARY",
        "candidate_declares_no_auto_overwrite",
        status_from_bool("不得自动覆盖 `chapters/ch01.md`" in candidate),
        "candidate header declares no formal overwrite",
    ))
    for name, term in forbidden.items():
        ok = term not in candidate or "不得自动覆盖" in candidate
        checks.append(check_type("BOUNDARY", name, status_from_bool(ok), f"term={term}"))

    return checks
