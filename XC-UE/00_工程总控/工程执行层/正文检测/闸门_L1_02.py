from __future__ import annotations

import re

from 切分 import 找证据
from 正文检测模型 import 检测项, 段落, 闸门结果
from 路由 import 补路由


TERMS = [
    "青岚宗",
    "停尸院",
    "尸簿",
    "周不问",
    "药园",
    "陆沉舟",
    "宁小满",
    "掌境堂",
    "韩照骨",
    "遗境",
    "成境",
    "灵雾",
    "白骨令",
    "锁灵索",
    "第三扇门",
]


def _score_c(paragraphs: list[段落]) -> tuple[int, list[段落], str]:
    first_half = paragraphs[: max(1, len(paragraphs) // 2)]
    hit_terms = [term for term in TERMS if any(term in p.文本 for p in first_half)]
    dense = []
    for p in first_half:
        term_hits = sum(1 for term in TERMS if term in p.文本)
        explain_hits = sum(p.文本.count(w) for w in ["因为", "所以", "至少", "专管", "规则", "不该", "不是"])
        if term_hits >= 2 or explain_hits >= 2:
            dense.append(p)
    if len(hit_terms) >= 11 or len(dense) >= 9:
        return 4, dense[:5], f"前半章术语/专名 {len(hit_terms)} 个，密集说明段 {len(dense)} 个。"
    if len(hit_terms) >= 8 or len(dense) >= 5:
        return 3, dense[:5], f"前半章术语/专名 {len(hit_terms)} 个，密集说明段 {len(dense)} 个。"
    return 2, dense[:5], f"前半章术语/专名 {len(hit_terms)} 个，密集说明段 {len(dense)} 个。"


def 检测(paragraphs: list[段落], l101_passed: bool) -> 闸门结果:
    items: list[检测项] = []

    entrance_ev = 找证据(paragraphs[:8], [r"停尸院", r"周不问", r"无修为", r"钥匙|死两次"], 4)
    if len(entrance_ev) < 3:
        items.append(
            检测项(
                "L1-02",
                "入口抓手",
                "风险",
                "前八段未同时给出场景、异常对象和核心疑问，入口可能慢。",
                entrance_ev,
                "warning",
                "入口弱",
            )
        )
    else:
        items.append(检测项("L1-02", "入口抓手", "成立", "前八段能给出停尸院、死者身份与异常物抓手。", entrance_ev))

    e_ev = 找证据(paragraphs, [r"尸体消失", r"向内塌陷", r"剧痛", r"拿下", r"全是血|尸山"], 5)
    e_score = 4 if len(e_ev) >= 4 else 2
    if e_score < 3:
        items.append(
            检测项("L1-02", "E 即时情绪反馈", "失败", "尸体异变、压迫、追捕、疼痛等即时刺激不足。", e_ev, "error", "E低：即时情绪反馈弱")
        )
    else:
        items.append(检测项("L1-02", "E 即时情绪反馈", "成立", "尸体消失、空间塌陷、追捕、剧痛和尸山反转提供即时刺激。", e_ev))

    v_ev = 找证据(paragraphs[-18:], [r"第三扇门", r"第一次灭门", r"外面的韩照骨|遗境里的韩照骨", r"等了他很多年"], 5)
    v_score = 5 if len(v_ev) >= 3 else 2
    if v_score < 3:
        items.append(
            检测项("L1-02", "V 未来价值预期", "失败", "章末没有形成下一章必须看的明确问题。", v_ev, "error", "V低：未来价值预期弱")
        )
    else:
        items.append(检测项("L1-02", "V 未来价值预期", "成立", "章末把第三扇门、第一次灭门、两个韩照骨压成下一章问题。", v_ev))

    c_score, dense_paras, c_desc = _score_c(paragraphs)
    if c_score >= 4:
        items.append(
            检测项(
                "L1-02",
                "C 认知成本",
                "风险",
                c_desc + " E/V 很强，但前半章概念、机构、规则集中，存在压过入口流畅度的风险。",
                找证据(dense_paras, [r".*"], 5),
                "warning",
                "C高：认知成本过高",
            )
        )
    else:
        items.append(检测项("L1-02", "C 认知成本", "成立", c_desc + " 未检测到压过 E × V 的密度。", 找证据(dense_paras, [r".*"], 5)))

    abandon = []
    for i in range(0, len(paragraphs) - 2):
        window = paragraphs[i : i + 3]
        if sum(p.字数 for p in window) >= 330 and sum(1 for p in window if "“" in p.文本) <= 1:
            abandon.extend(window)
            break
    if abandon:
        items.append(
            检测项(
                "L1-02",
                "弃读点窗口",
                "风险",
                "检测到连续长说明/低对话窗口，可能是阅读断流点，需人工复核。",
                找证据(abandon, [r".*"], 3),
                "warning",
                "弃读点明显",
            )
        )

    failures = [补路由(i) for i in items if i.严重级别 in {"error", "warning"}]
    if not l101_passed:
        failures.insert(
            0,
            补路由(
                检测项(
                    "L1-02",
                    "前置闸门",
                    "阻断",
                    "L1-01 未完全成立时，L1-02 不允许直接判通过。",
                    [],
                    "warning",
                    "L1-01未通过",
                    候选模块="回L1-01",
                    回流验收位置="L1-01",
                    修复方向="先处理内部创作成立问题",
                )
            ),
        )
    hard = [i for i in failures if i.严重级别 == "error"]
    result = "读者投入不足" if hard else ("需要派单修复" if failures else "读者投入成立")
    return 闸门结果(
        闸门="L1-02",
        判断结果=result,
        失败类型=[i.失败类型 for i in failures if i.失败类型],
        失败位置=[e for i in failures for e in i.证据],
        是否进入L15="是" if failures else "否",
        调用方向=[i.候选模块 for i in failures if i.候选模块],
        回流验收位置="L1-02",
        最终状态=result,
        检测项=items,
    )
