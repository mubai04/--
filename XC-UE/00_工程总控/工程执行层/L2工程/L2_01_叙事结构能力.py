from __future__ import annotations

from L2模型 import L201真实诊断, 失败输入, 修复单
from 能力标准解析 import 能力规则, 失败规则
from 能力修复单 import 生成标准修复单, 选择失败规则


def 生成修复单(item: 失败输入, rules: 能力规则) -> 修复单:
    return 生成标准修复单(item, rules)


def _证据锚点(item: 失败输入) -> list[dict[str, object]]:
    anchors: list[dict[str, object]] = []
    for evidence in item.证据:
        if not evidence.摘句:
            continue
        anchors.append({"段落": evidence.段落, "摘句": evidence.摘句})
    return anchors


def _涉及段落(item: 失败输入) -> list[int]:
    return sorted({evidence.段落 for evidence in item.证据 if isinstance(evidence.段落, int)})


def _越界(rule: 失败规则 | None) -> bool:
    if not rule:
        return False
    text = " ".join([rule.编号, rule.名称, rule.定义, *rule.修复规则])
    return "越界" in text or "L1.5" in text


def _原因诊断(rule: 失败规则 | None, item: 失败输入, anchors: list[dict[str, object]]) -> str:
    if not rule:
        return "未命中 L2-01 结构化失败规则，当前输入不足以形成叙事结构诊断。"
    evidence_text = "；".join(str(anchor["摘句"]) for anchor in anchors)
    if evidence_text:
        return f"{rule.定义} 输入证据显示：{evidence_text}"
    return f"{rule.定义} 但输入未提供可复现文本锚点，不能继续推导具体正文定位。"


def _风险(rule: 失败规则 | None, anchors: list[dict[str, object]], forbidden: bool) -> list[str]:
    risks: list[str] = []
    if not anchors:
        risks.append("证据不足：无可复现文本锚点，禁止伪造定位。")
    if not rule:
        risks.append("未命中 L2-01 结构化失败规则，不得生成候选修复。")
    if forbidden:
        risks.append("疑似越界：应回 L1.5 重路由，不得生成 L2-01 候选修复。")
    if not risks:
        risks.append("候选策略只允许作用于证据锚点覆盖的结构问题。")
    return risks


def 生成真实诊断(item: 失败输入, rules: 能力规则) -> L201真实诊断:
    rule = 选择失败规则(item, rules)
    anchors = _证据锚点(item)
    forbidden = _越界(rule)
    if forbidden:
        eligibility = "禁止处理"
        confidence = "中" if anchors else "低"
        strategies: list[str] = []
    elif not rule:
        eligibility = "无需修复"
        confidence = "低"
        strategies = []
    elif not anchors:
        eligibility = "需人工判断"
        confidence = "低"
        strategies = []
    else:
        eligibility = "可自动修复"
        confidence = "高"
        strategies = rule.修复规则[:4]

    return L201真实诊断(
        问题类型=rule.名称 if rule else item.失败类型,
        证据锚点=anchors,
        涉及段落=_涉及段落(item),
        原因诊断=_原因诊断(rule, item, anchors),
        修改目标=item.修复方向 or (rule.修复规则[0] if rule and rule.修复规则 else ""),
        候选修改策略=strategies,
        风险=_风险(rule, anchors, forbidden),
        验收条件=(rule.验收标准[:4] if rule and not forbidden else []),
        置信度=confidence,
        自动修复资格判定=eligibility,
        rule_id=f"{rules.模块}:{rule.编号}" if rule else f"{rules.模块}:unmatched",
        rule_version=(rule.规则版本 if rule else rules.规则版本),
        rule_hash=(rule.规则哈希 if rule else rules.规则哈希),
    )
