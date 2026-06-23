from __future__ import annotations

from 切分 import 找证据
from 正文检测模型 import 检测项, 段落, 闸门结果
from 路由 import 补路由


def 检测(paragraphs: list[段落], word_count: int, l102_passed: bool) -> 闸门结果:
    items: list[检测项] = []

    if word_count < 2000:
        items.append(
            检测项(
                "L1-03",
                "字数体量",
                "失败",
                f"当前正文约 {word_count} 字，低于 2000，默认降级为功能稿。",
                [],
                "error",
                "字数不足",
            )
        )
    elif word_count > 3200:
        items.append(
            检测项(
                "L1-03",
                "字数体量",
                "风险",
                f"当前正文约 {word_count} 字，高于黄金三章默认 2200-3000 字区间，可能需要压缩或拆章人工判断。",
                [],
                "warning",
                "字数超出默认发布体量",
            )
        )
    else:
        items.append(检测项("L1-03", "字数体量", "成立", f"当前正文约 {word_count} 字，落在默认发布体量附近。"))

    payoff_ev = 找证据(paragraphs, [r"尸体消失", r"向内塌陷", r"门票", r"撞进", r"第一次灭门"], 5)
    if len(payoff_ev) < 3:
        items.append(
            检测项("L1-03", "当章收益", "失败", "当章没有足够明确的惊讶、压迫、信息推进或新问题。", payoff_ev, "error", "当章收益不足")
        )
    else:
        items.append(检测项("L1-03", "当章收益", "成立", "当章兑现死亡异常、成境、主角撞门与灭门钩子。", payoff_ev))

    hook_ev = 找证据(paragraphs[-12:], [r"第一次灭门", r"第三扇门后", r"遗境里的韩照骨", r"等了他很多年"], 4)
    if len(hook_ev) < 2:
        items.append(检测项("L1-03", "章末追读", "失败", "章末没有制造下一章新变量。", hook_ev, "error", "章末追读弱"))
    else:
        items.append(检测项("L1-03", "章末追读", "成立", "章末给出第一次灭门与遗境韩照骨，追读理由明确。", hook_ev))

    if not l102_passed:
        items.append(
            检测项(
                "L1-03",
                "投入意愿前置",
                "风险",
                "L1-02 存在需要派单修复项，发布锁不能直接判发布。",
                [],
                "warning",
                "投入意愿不足",
                候选模块="回L1-02",
                回流验收位置="L1-02",
                修复方向="先回 L1-02 处理读者投入风险",
            )
        )

    failures = [补路由(i) for i in items if i.严重级别 in {"error", "warning"}]
    hard = [i for i in failures if i.严重级别 == "error"]
    if hard:
        result = "退回重构"
    elif failures:
        result = "需要人工复核"
    else:
        result = "发布"
    return 闸门结果(
        闸门="L1-03",
        判断结果=result,
        失败类型=[i.失败类型 for i in failures if i.失败类型],
        失败位置=[e for i in failures for e in i.证据],
        是否进入L15="是" if failures else "否",
        调用方向=[i.候选模块 for i in failures if i.候选模块],
        回流验收位置="L1-03",
        最终状态=result,
        检测项=items,
    )
