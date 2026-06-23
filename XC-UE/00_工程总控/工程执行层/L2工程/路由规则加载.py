from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class 路由规则:
    rule_id: str
    version: str
    hash: str
    keywords: list[str]
    target: str


@dataclass(frozen=True)
class 路由规则集:
    version: str
    hash: str
    rules: list[路由规则]


def 加载路由规则(path: Path) -> 路由规则集:
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    raw = json.loads(data.decode("utf-8-sig"))
    version = raw.get("version", "")
    rules = [
        路由规则(
            rule_id=item["rule_id"],
            version=version,
            hash=digest,
            keywords=list(item.get("keywords", [])),
            target=item["target"],
        )
        for item in raw.get("routes", [])
    ]
    _校验冲突(rules)
    return 路由规则集(version=version, hash=digest, rules=rules)


def _校验冲突(rules: list[路由规则]) -> None:
    seen: dict[str, str] = {}
    for rule in rules:
        for keyword in rule.keywords:
            existing = seen.get(keyword)
            if existing and existing != rule.target:
                raise ValueError(f"路由关键词冲突：{keyword} 同时指向 {existing} 与 {rule.target}")
            seen[keyword] = rule.target
