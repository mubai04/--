from __future__ import annotations

import re

from 切分 import 找证据
from 正文检测模型 import 检测项, 段落, 闸门结果
from 路由 import 补路由


def _ordered_hits(paragraphs: list[段落], stages: list[tuple[str, list[str]]]) -> tuple[int, list]:
    evidence = []
    last = 0
    for _name, patterns in stages:
        found = None
        for p in paragraphs:
            if p.编号 <= last:
                continue
            if any(re.search(pattern, p.文本) for pattern in patterns):
                found = p
                break
        if found:
            evidence.extend(找证据([found], [".*"], 1))
            last = found.编号
    return len(evidence), evidence


def 检测(paragraphs: list[段落], standards: dict[str, str]) -> 闸门结果:
    items: list[检测项] = []

    stages = [
        ("尸体与异常物", [r"尸簿|停尸院", r"钥匙"]),
        ("重复死亡异常", [r"十七年前|死两次|死亡时间"]),
        ("外部压力靠近", [r"掌境堂|韩照骨|封山"]),
        ("成境事件发生", [r"尸体消失|遗境|向内塌陷|空间本身"]),
        ("主角主动选择", [r"两个选择|没有再等|朝药园奔去|撞进"]),
        ("章末核心反转", [r"第一次灭门|尸山|第三扇门后"]),
    ]
    hit_count, ev = _ordered_hits(paragraphs, stages)
    if hit_count < len(stages):
        items.append(
            检测项(
                "L1-01",
                "叙事因果链",
                "失败",
                f"核心事件链只识别到 {hit_count}/{len(stages)} 个有序节点，章节推进可能断裂。",
                ev,
                "error",
                "叙事失败",
            )
        )
    else:
        items.append(
            检测项(
                "L1-01",
                "叙事因果链",
                "成立",
                "尸体异常、重复死亡、掌境堂压力、成境、主动进入、章末反转形成有序推进。",
                ev,
            )
        )

    agency = 找证据(paragraphs, [r"两个选择", r"没有再等", r"朝药园奔去", r"撞进"], 4)
    pressure = 找证据(paragraphs, [r"废籍逐出宗门|盗取遗境线索|拿下|封山|入口闭合"], 4)
    if len(agency) < 2 or len(pressure) < 2:
        items.append(
            检测项(
                "L1-01",
                "角色动机与选择代价",
                "风险",
                "主角选择或外部代价证据不足，可能导致关键行动像作者推动。",
                agency + pressure,
                "warning",
                "角色失败",
            )
        )
    else:
        items.append(
            检测项(
                "L1-01",
                "角色动机与选择代价",
                "成立",
                "正文给出追捕、定罪、入口闭合与钥匙门票，能解释主角主动撞门。",
                agency + pressure,
            )
        )

    setting_ev = 找证据(paragraphs, [r"没有修为的人，不会成境", r"死两次", r"初生遗境", r"普通人看不见入口", r"第三扇门"], 5)
    if len(setting_ev) < 3:
        items.append(
            检测项(
                "L1-01",
                "创意设定压力",
                "失败",
                "成境规则、钥匙/门、死亡异常没有形成足够规则压力。",
                setting_ev,
                "error",
                "创意设定失败",
            )
        )
    else:
        items.append(
            检测项(
                "L1-01",
                "创意设定压力",
                "成立",
                "无修为却成境、死两次、入口只被主角看见、第三扇门禁忌形成设定压力。",
                setting_ev,
            )
        )

    explanation_words = ["因为", "所以", "至少", "专管", "照规矩", "不是", "不该"]
    explanation_paras = [
        p for p in paragraphs if sum(p.文本.count(w) for w in explanation_words) >= 2
    ]
    if len(explanation_paras) >= 7:
        items.append(
            检测项(
                "L1-01",
                "解释腔与AI味风险",
                "风险",
                "解释性连接词密集段偏多，可能让中段从现场压力滑向规则说明。",
                找证据(explanation_paras, [r".*"], 5),
                "warning",
                "AI味失败",
            )
        )

    long_paras = [p for p in paragraphs if p.字数 >= 120]
    if len(long_paras) >= 8:
        items.append(
            检测项(
                "L1-01",
                "文风密度",
                "风险",
                "长段偏多，若连续出现会抬高阅读负担；需人工判断是否压住节奏。",
                找证据(long_paras, [r".*"], 5),
                "warning",
                "文风失败",
            )
        )

    failures = [补路由(i) for i in items if i.严重级别 in {"error", "warning"}]
    hard = [i for i in failures if i.严重级别 == "error"]
    result = "内部创作失败" if hard else ("需要派单修复" if failures else "内部创作成立")
    return 闸门结果(
        闸门="L1-01",
        判断结果=result,
        失败类型=[i.失败类型 for i in failures if i.失败类型],
        失败位置=[e for i in failures for e in i.证据],
        是否进入L15="是" if failures else "否",
        调用方向=[i.候选模块 for i in failures if i.候选模块],
        回流验收位置="L1-01",
        最终状态=result,
        检测项=items,
    )
