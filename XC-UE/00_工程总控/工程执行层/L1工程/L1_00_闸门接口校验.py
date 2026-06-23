from __future__ import annotations

from L1模型 import 检测项, 闸门结果
from 闸门标准解析 import 标准完整性


REQUIRED_FIELDS = [
    "闸门",
    "判断结果",
    "输入材料",
    "失败类型",
    "失败位置",
    "是否进入L15",
    "调用方向",
    "回流验收位置",
    "最终状态",
]


def 检测(gates: list[闸门结果], standards: dict[str, str]) -> 闸门结果:
    items: list[检测项] = []

    missing_sections = 标准完整性(standards)
    if missing_sections:
        items.append(
            检测项(
                "L1-00",
                "闸门标准完整性",
                "风险",
                "部分 L1 Markdown 标准缺少工程需要的章节：" + str(missing_sections),
                [],
                "warning",
                "输入不足",
                候选模块="回L1-00",
                回流验收位置="L1-00",
                修复方向="补齐 L1 闸门接口标准",
            )
        )
    else:
        items.append(检测项("L1-00", "闸门标准完整性", "检测到接口信号", "L1-00 到 L1-03 的关键工程章节存在。"))

    bad_fields = []
    for gate in gates:
        for field in REQUIRED_FIELDS:
            if not hasattr(gate, field):
                bad_fields.append(f"{gate.闸门}.{field}")
    if bad_fields:
        items.append(
            检测项(
                "L1-00",
                "统一输出格式",
                "失败",
                "闸门输出缺少 L1-00 要求字段：" + "、".join(bad_fields),
                [],
                "error",
                "输入不足",
                候选模块="回L1-00",
                回流验收位置="L1-00",
                修复方向="修正 L1 工程输出模型",
            )
        )
    else:
        items.append(检测项("L1-00", "统一输出格式", "检测到接口信号", "L1-01/L1-02/L1-03 输出字段符合 L1-00 接口。"))

    route_errors = []
    for gate in gates:
        has_failure = bool(gate.失败类型)
        if has_failure and gate.是否进入L15 != "是":
            route_errors.append(f"{gate.闸门} 有失败类型但未进入 L1.5")
        if (not has_failure) and gate.是否进入L15 == "是":
            route_errors.append(f"{gate.闸门} 无失败类型但进入 L1.5")
    if route_errors:
        items.append(
            检测项(
                "L1-00",
                "L1.5交接条件",
                "失败",
                "；".join(route_errors),
                [],
                "error",
                "技术护栏失败",
                候选模块="L3",
                回流验收位置="L1-00",
                修复方向="修正 L1 到 L1.5 的交接条件",
            )
        )
    else:
        items.append(检测项("L1-00", "L1.5交接条件", "检测到接口信号", "失败闸门进入 L1.5，非失败闸门不强行派单。"))

    failures = [item for item in items if item.严重级别 in {"error", "warning"}]
    hard = [item for item in failures if item.严重级别 == "error"]
    result = "需要补输入" if hard else ("需要派单修复" if failures else "INTERFACE_SIGNAL_PRESENT")
    return 闸门结果(
        闸门="L1-00",
        判断结果=result,
        输入材料=["L1-00 Markdown标准", "L1-01/L1-02/L1-03闸门输出", "L1标准完整性检查结果"],
        失败类型=[item.失败类型 for item in failures if item.失败类型],
        失败位置=[],
        是否进入L15="是" if failures else "否",
        调用方向=[item.候选模块 for item in failures if item.候选模块],
        回流验收位置="L1-00",
        最终状态=result,
        检测项=items,
        规则摘要={"必填字段": REQUIRED_FIELDS},
    )
