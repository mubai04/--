from __future__ import annotations

from L2模型 import 失败输入, 接口判断
from 能力标准解析 import L2规则


FALLBACK_FAILURE_TO_MODULE = {
    "叙事失败": "L2-01",
    "字数不足": "L2-01",
    "章末弱": "L2-01",
    "章末追读弱": "L2-01",
    "文风失败": "L2-02",
    "AI味失败": "L2-02",
    "认知成本过高": "L2-02",
    "角色失败": "L2-03",
    "创意设定失败": "L2-04",
    "入口弱": "L2-05",
    "E低：即时情绪反馈弱": "L2-05",
    "V低：未来价值预期弱": "L2-05",
    "C高：认知成本过高": "L2-05",
    "弃读点明显": "L2-05",
    "投入意愿不足": "L2-05",
    "技术护栏失败": "L2-06",
}

NON_L2 = {
    "L3": "L3",
    "外部运营层": "外部运营层",
}

DERIVED_RECHECK = {
    "回L1-01": "L1-01",
    "回 L1-01": "L1-01",
    "回L1-02": "L1-02",
    "回 L1-02": "L1-02",
    "回L1-03": "L1-03",
    "回 L1-03": "L1-03",
}


def _标准归属(item: 失败输入, rules: L2规则 | None) -> str:
    if not rules:
        return FALLBACK_FAILURE_TO_MODULE.get(item.失败类型, "")
    haystack = " ".join([item.失败类型, item.名称, item.说明, item.修复方向])
    for keywords, module in rules.路由表:
        if module.startswith("回"):
            continue
        if any(keyword and keyword in haystack for keyword in keywords):
            return module.replace("重路由", "")
    for module, ability in rules.能力接口表.items():
        if any(keyword and keyword in haystack for keyword in ability.输入关键词):
            return module
    return FALLBACK_FAILURE_TO_MODULE.get(item.失败类型, "")


def 判断(item: 失败输入, rules: L2规则 | None = None) -> 接口判断:
    candidate = item.候选模块
    if candidate in DERIVED_RECHECK:
        target = DERIVED_RECHECK[candidate]
        return 接口判断(
            来源闸门=item.来源闸门,
            输入来源模式="派生复验项",
            输入问题=item.说明,
            初步归属=target,
            主候选模块="",
            接口失败类型="IF-R1",
            判断依据="该项来自上游闸门的复验前置条件，只记录复验目标，不生成 L2 修复单。",
            是否越界="否",
            建议动作=[f"回 {target} 复验"],
            回流验收位置=item.回流验收位置 or target,
            最终状态="派生复验",
            备注="不转换为回 L1.5，不阻断同批其他 L2 修复单。",
        )
    if candidate in NON_L2:
        target = NON_L2[candidate]
        return 接口判断(
            来源闸门=item.来源闸门,
            输入来源模式="直接闸门输入",
            输入问题=item.说明,
            初步归属=target,
            主候选模块=target,
            接口失败类型="IF-P2" if target == "回L1.5" else "IF-P4",
            判断依据="L1 failure packet 给出的候选模块不是 L2 能力模块。",
            是否越界="是",
            建议动作=["回 L1.5 重路由"] if target == "回L1.5" else ["进入 L3"],
            回流验收位置=item.回流验收位置 or item.来源闸门,
            最终状态="回L1.5" if target == "回L1.5" else "进入L3",
        )

    standard_expected = _标准归属(item, rules)
    expected = FALLBACK_FAILURE_TO_MODULE.get(item.失败类型, "") or standard_expected
    if not candidate and not expected:
        return 接口判断(
            来源闸门=item.来源闸门,
            输入来源模式="直接闸门输入",
            输入问题=item.说明,
            初步归属="L1.5",
            主候选模块="",
            接口失败类型="IF-P2",
            判断依据="失败类型未映射到 L2 模块，且 failure packet 无候选模块。",
            是否混合问题="是",
            建议动作=["回 L1.5 重路由"],
            回流验收位置=item.来源闸门,
            最终状态="回L1.5",
        )

    module = candidate or expected
    if expected and candidate and expected != candidate:
        return 接口判断(
            来源闸门=item.来源闸门,
            输入来源模式="直接闸门输入",
            输入问题=item.说明,
            初步归属=expected,
            主候选模块=expected,
            次候选模块=candidate,
            接口失败类型="IF-P3",
            判断依据=f"失败类型映射为 {expected}，但输入候选模块为 {candidate}。",
            是否混合问题="是",
            建议动作=["回 L1.5 重路由"],
            回流验收位置=item.回流验收位置 or item.来源闸门,
            最终状态="回L1.5",
        )

    return 接口判断(
        来源闸门=item.来源闸门,
        输入来源模式="直接闸门输入",
        输入问题=item.说明,
        初步归属=module,
        主候选模块=module,
        判断依据=f"失败类型“{item.失败类型}”匹配 {module} 接口范围。",
        建议动作=["进入对应 L2"],
        回流验收位置=item.回流验收位置 or item.来源闸门,
        最终状态="接口明确",
    )
