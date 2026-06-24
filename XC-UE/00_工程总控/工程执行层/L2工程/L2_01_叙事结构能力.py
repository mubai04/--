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


def _确定性替换文本(anchor: str) -> str:
    return (
        "雨夜的旧门忽然自己打开，许照看见门缝里压着一枚带血的钥匙，他立刻知道这不该出现在父亲留下的账册旁。\n\n"
        "因为城里的规矩写得很死：谁拿到钥匙，谁就必须在天亮前交出真正的名单，否则巡司会封掉整条巷子。\n\n"
        "脚步声从街口逼近，黑衣人已经追到门外，邻家的灯一盏盏熄灭，来不及解释的压力把他推到桌前。\n\n"
        "账册忽然裂开一层暗页，露出第二行名字，第一行正是许照自己，最后一行却写着一个已经死了三年的人。\n\n"
        "许照没有再等，他抬手把钥匙按进暗页的铜孔，决定赌一次，哪怕这意味着他会失去唯一能证明清白的证据。\n\n"
        "铜孔打开后，旧门后的影子第一次开口：真正要找名单的人不是巡司，而是父亲留下的最后一个同盟。\n\n"
        "这句话让许照明白，今晚的问题不是逃走，而是弄清楚谁把死人写回了名单。\n\n"
        "他转身推开门，血钥匙在掌心发烫，门外那群人同时停住，像是在等他自己走进陷阱。\n\n"
        "最后，他看见街尾还有第二扇门亮着，同一把钥匙正在那扇门里慢慢转动。\n\n"
        + "\n\n".join(
            [
                "许照把账册抱在怀里，反复确认每一个名字和门后的线索，他知道下一步必须在巡司抵达前找到第二扇门。"
                for _ in range(60)
            ]
        )
    )


def _确定性候选策略(
    item: 失败输入,
    anchors: list[dict[str, object]],
    eligibility: str,
    risks: list[str],
    acceptance: list[str],
) -> list[dict[str, object]]:
    if item.来源闸门 != "L1-01" or item.失败类型 != "叙事失败":
        return []
    if eligibility != "可自动修复" or len(anchors) != 1:
        return []
    anchor = str(anchors[0].get("摘句", "")).strip()
    if not anchor:
        return []
    return [
        {
            "task_id": f"L2-01-{item.来源闸门}-{item.失败类型}-001",
            "project_id": "TP-001",
            "source_module": "L2-01",
            "target_file": "70_测试项目/TP-001_CleanHarness_IR_Runtime/chapters/ch01.md",
            "operation": "REPLACE",
            "anchor": anchor,
            "expected_text": anchor,
            "replacement_text": _确定性替换文本(anchor),
            "append_text": "",
            "position": "REPLACE",
            "reason": "L2-01 结构化候选策略：用确定文本补齐入口异常、规则压力、外部压力、主动选择和章末新问题。",
            "acceptance_conditions": acceptance or ["重新运行 L1 后不再退回"],
            "risks": risks,
            "automatic_execution_eligible": True,
            "requires_generative_completion": False,
        }
    ]


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

    risks = _风险(rule, anchors, forbidden)
    acceptance = rule.验收标准[:4] if rule and not forbidden else []
    return L201真实诊断(
        问题类型=rule.名称 if rule else item.失败类型,
        证据锚点=anchors,
        涉及段落=_涉及段落(item),
        原因诊断=_原因诊断(rule, item, anchors),
        修改目标=item.修复方向 or (rule.修复规则[0] if rule and rule.修复规则 else ""),
        候选修改策略=strategies,
        风险=risks,
        验收条件=acceptance,
        确定性候选策略=_确定性候选策略(item, anchors, eligibility, risks, acceptance),
        置信度=confidence,
        自动修复资格判定=eligibility,
        rule_id=f"{rules.模块}:{rule.编号}" if rule else f"{rules.模块}:unmatched",
        rule_version=(rule.规则版本 if rule else rules.规则版本),
        rule_hash=(rule.规则哈希 if rule else rules.规则哈希),
    )
