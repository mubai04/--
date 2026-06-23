from __future__ import annotations

from L2模型 import 失败输入, 修复单
from 能力标准解析 import 能力规则, 失败规则


FAILURE_HINTS = {
    "叙事失败": ["因果", "主线", "路径", "结构", "推进", "张力", "剪枝"],
    "字数不足": ["结构加压", "条件补全", "章节", "收益", "扩写"],
    "章末弱": ["未来压力", "下一步问题", "心理钩子", "章末"],
    "章末追读弱": ["未来压力", "下一步问题", "心理钩子", "章末"],
    "文风失败": ["信息增量", "语境", "重复", "解释", "句式", "现实锚点"],
    "AI味失败": ["AI", "模板", "解释", "语境锁定", "句式"],
    "认知成本过高": ["解释", "重复", "密度", "时间成本", "认知"],
    "角色失败": ["动机", "心理", "欲望", "恐惧", "隐藏目的", "关系"],
    "创意设定失败": ["中心价值", "约束", "边界", "压缩入口", "玩法"],
    "入口弱": ["P1", "P2", "即时信号", "收益承诺", "开头"],
    "E低：即时情绪反馈弱": ["P2", "P5", "情绪强度", "即时信号"],
    "V低：未来价值预期弱": ["P3", "P9", "预测", "期待升级", "未来"],
    "C高：认知成本过高": ["P8", "时间成本", "认知", "解释"],
    "弃读点明显": ["P7", "P8", "变化频率", "时间成本", "退出"],
    "投入意愿不足": ["P1", "P3", "P9", "收益承诺", "预测", "期待升级"],
    "技术护栏失败": ["真源", "阶段", "状态", "一致性", "回写"],
}


DEFAULT_ACTIONS = {
    "L2-01": ["主线锁定", "条件补全", "结构加压"],
    "L2-02": ["信息增量标注", "解释削减", "语境锁定"],
    "L2-03": ["动机补强", "心理迁移补全", "隐藏目的标注"],
    "L2-04": ["中心价值锁定", "约束边界建立", "压缩入口"],
    "L2-05": ["A1 时间窗口锁定", "A3 UEG 拆解表", "A13 反馈验证表"],
    "L2-06": ["真源清洗", "阶段锁定", "一致性复核"],
}


def _score_rule(item: 失败输入, rule: 失败规则) -> int:
    haystack = " ".join([rule.编号, rule.名称, rule.定义, " ".join(rule.表现), " ".join(rule.修复规则)])
    hints = FAILURE_HINTS.get(item.失败类型, [item.失败类型, item.名称])
    return sum(1 for hint in hints if hint and hint in haystack)


def 选择失败规则(item: 失败输入, ability: 能力规则) -> 失败规则 | None:
    if not ability.失败类型库:
        return None
    scored = sorted(((_score_rule(item, rule), rule) for rule in ability.失败类型库), key=lambda x: x[0], reverse=True)
    if scored and scored[0][0] > 0:
        return scored[0][1]
    return None


def _选择动作(item: 失败输入, ability: 能力规则, rule: 失败规则 | None) -> list[str]:
    actions = rule.修复规则[:] if rule and rule.修复规则 else []
    if not actions:
        hints = FAILURE_HINTS.get(item.失败类型, [])
        for action in ability.修复动作库:
            if any(hint and hint in action for hint in hints):
                actions.append(action)
    if not actions:
        actions = DEFAULT_ACTIONS.get(ability.模块, [])[:]
    if not actions:
        actions = ability.修复动作库[:3]
    return actions[:4]


def _选择验收(ability: 能力规则, rule: 失败规则 | None) -> list[str]:
    acceptance = rule.验收标准[:] if rule and rule.验收标准 else []
    if not acceptance:
        acceptance = ability.回流验收问题[:3]
    return acceptance[:4]


def 生成标准修复单(item: 失败输入, ability: 能力规则) -> 修复单:
    rule = 选择失败规则(item, ability)
    actions = _选择动作(item, ability, rule)
    acceptance = _选择验收(ability, rule)
    product = item.修复方向 or ability.输出产物 or f"{ability.模块} 修复单"
    needs_l2 = "是" if ability.模块 == "L2-05" and item.失败类型.startswith("C高") else "否"
    reroute = "是" if rule and "越界" in rule.名称 else "否"
    return 修复单(
        修复单类型="L2 能力修复单",
        来源闸门=item.来源闸门,
        接收模块=ability.模块,
        输入问题=item.说明,
        主失败类型=item.失败类型,
        次失败类型=rule.编号 if rule else "",
        修复动作=" / ".join(actions),
        修复产物=product,
        验收问题="；".join(acceptance) if acceptance else "修复后是否回到原闸门复验并消除该失败类型。",
        回流位置=item.回流验收位置 or item.来源闸门,
        是否需要其他L2辅助=needs_l2,
        是否需要回L15重路由=reroute,
        最终状态="回原闸门复验",
        标准来源=ability.标准来源,
        规则编号=rule.编号 if rule else "",
        规则依据=rule.名称 if rule else "按能力接口表生成",
        标准动作=actions,
        标准验收=acceptance,
    )
