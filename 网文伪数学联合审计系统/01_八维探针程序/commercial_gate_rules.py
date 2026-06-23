#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""八维探针商业六门唯一门控真源。"""
from __future__ import annotations
from typing import Any

ALL_GATES = ["卖点识别门","情绪承诺门","开篇入口门","主角发动机门","最小兑现门","连载扩展门"]
RULES = {
    "fragment": ["卖点识别门","情绪承诺门","开篇入口门","最小兑现门"],
    "single_chapter": ALL_GATES,
    "first_three": ALL_GATES,
    "online_full": ALL_GATES,
    "unpublished_full": ALL_GATES,
}
MIN_SCORE = 2

def evaluate_commercial_gates(gates: list[dict[str,Any]], input_type: str) -> dict[str,Any]:
    gate_map={g.get("gate"):g for g in gates}
    required=RULES.get(input_type,ALL_GATES)
    missing=[]; failed=[]; passed=[]
    for name in required:
        g=gate_map.get(name)
        if not g or not g.get("evidence_sufficient") or g.get("score") is None:
            missing.append(name); continue
        if float(g["score"]) < MIN_SCORE: failed.append(name)
        else: passed.append(name)
    if missing: status="证据不足"
    elif failed: status="未通过"
    else: status="通过"
    return {"status":status,"required_gates":required,"minimum_score":MIN_SCORE,"missing_gates":missing,"failed_gates":failed,"passed_gates":passed}
